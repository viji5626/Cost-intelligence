"""
Production-Grade AI Model Lifecycle Manager & Sequential Swapper
Coordinates state transitions, hardware-aware admission, request priority queuing,
atomic model swapping, graceful unload, and failure recovery across native AI engines.
"""

import asyncio
import gc
import logging
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import psutil

from ai.core.contracts import (
    AIExecutionEnvelope,
    InferenceEngineContract,
    ModelProvenance,
    TaskType,
)
from ai.hardware.fit_engine import (
    FitStatusEnum,
    HardwareFitEngine,
    HardwareFitResult,
)
from ai.hardware.profiles import RuntimeProfileName, get_runtime_profile
from ai.hardware.profiler import HardwareProfiler
from ai.providers.native_gguf import NativeGGUFEngine, native_gguf_engine
from ai.registry.models import ModelManifest, ModelStatusEnum, ModelTaskTypeEnum
from ai.registry.registry_service import model_registry_service
from ai.runtime.models import (
    LifecycleStateEnum,
    QueuedInferenceRequest,
    QueuedRequestStatusEnum,
    RequestPriorityEnum,
    RuntimeInstance,
)

logger = logging.getLogger(__name__)


class ModelLifecycleManager:
    """
    Core AI Model Lifecycle & Execution Coordinator.
    Manages runtime instances, sequential swapping, hardware budget gates, and request queueing.
    """

    def __init__(
        self,
        default_engine: Optional[InferenceEngineContract] = None,
        runtime_profile_name: RuntimeProfileName = RuntimeProfileName.PROFILE_BALANCED,
        max_vram_mb: int = 8192,
        default_device: str = "auto",
    ):
        self._engine: InferenceEngineContract = default_engine or native_gguf_engine
        self._profile_name = runtime_profile_name
        self.max_vram_mb = max_vram_mb
        self.default_device = default_device
        self._active_instances: Dict[str, RuntimeInstance] = {}  # instance_id -> RuntimeInstance
        self._model_to_instance: Dict[str, str] = {}  # model_id -> instance_id
        self._request_queue: List[QueuedInferenceRequest] = []
        self._lock = asyncio.Lock()

        # Synchronous compatibility cache
        self._legacy_active_model_name: Optional[str] = None
        self._legacy_active_model_instance: Optional[Any] = None
        self._legacy_active_model_type: Optional[str] = None

    @property
    def active_model(self) -> Optional[str]:
        """Returns the currently active primary model ID (for backward compatibility)."""
        if self._legacy_active_model_name:
            return self._legacy_active_model_name
        if self._active_instances:
            # Return model_id of first ready/executing instance
            for inst in self._active_instances.values():
                if inst.state in (LifecycleStateEnum.READY, LifecycleStateEnum.EXECUTING, LifecycleStateEnum.LOADING):
                    return inst.model_id
        return None

    def get_active_instances(self) -> List[RuntimeInstance]:
        """Returns a snapshot list of all tracked runtime instances."""
        return list(self._active_instances.values())

    def get_instance_by_model(self, model_id: str) -> Optional[RuntimeInstance]:
        """Looks up the active runtime instance for a given model ID."""
        inst_id = self._model_to_instance.get(model_id)
        if inst_id:
            return self._active_instances.get(inst_id)
        return None

    # =========================================================================
    # 1. ASYNC LIFECYCLE MANAGEMENT & ADMISSION
    # =========================================================================

    async def load_model(
        self,
        model_id: str,
        task_type: ModelTaskTypeEnum = ModelTaskTypeEnum.GENERATION,
        context_length: Optional[int] = None,
        force_cpu: bool = False,
        timeout_seconds: float = 60.0,
    ) -> RuntimeInstance:
        """
        Full lifecycle load pipeline:
        REGISTERED -> PREFLIGHT -> (SWAP/EVICT if needed) -> LOADING -> HEALTH_PROBE -> READY
        """
        async with self._lock:
            # Check if model already loaded & ready
            existing_inst = self.get_instance_by_model(model_id)
            if existing_inst and existing_inst.state == LifecycleStateEnum.READY:
                return existing_inst

            # 1. Initial State: REGISTERED
            instance = RuntimeInstance(
                model_id=model_id,
                task_type=task_type,
                state=LifecycleStateEnum.REGISTERED,
            )
            self._active_instances[instance.instance_id] = instance
            self._model_to_instance[model_id] = instance.instance_id

            try:
                # 2. PREFLIGHT: Registry & Manifest Verification
                instance.update_state(LifecycleStateEnum.PREFLIGHT)
                manifest = model_registry_service.get_model(model_id)
                if not manifest:
                    raise FileNotFoundError(f"Model '{model_id}' is not registered in Model Registry.")

                if manifest.status != ModelStatusEnum.ACTIVE_REGISTERED:
                    raise PermissionError(
                        f"Model '{model_id}' cannot be loaded: Status is '{manifest.status.value}' (Must be ACTIVE_REGISTERED)."
                    )

                # Hardware Fit Preflight
                target_ctx = context_length or manifest.recommended_context_length or 4096
                profile = get_runtime_profile(self._profile_name)

                fit_result = HardwareFitEngine.evaluate_fit(
                    manifest=manifest,
                    target_task=task_type,
                    gpu_info=HardwareProfiler.get_compatibility_report().gpu,
                    ram_info=HardwareProfiler.get_compatibility_report().ram,
                    cpu_info=HardwareProfiler.get_compatibility_report().cpu,
                    context_length=target_ctx,
                )

                if not fit_result.compatible or fit_result.status == FitStatusEnum.UNSAFE:
                    raise MemoryError(
                        f"Hardware Fit Admission Denied: Status={fit_result.status.value}. "
                        f"Reasons: {'; '.join(fit_result.reasons)}"
                    )

                instance.fit_result = fit_result
                instance.context_length = target_ctx
                instance.estimated_vram_mb = float(fit_result.estimated_peak_memory_mb)
                instance.estimated_ram_mb = float(fit_result.estimated_runtime_overhead_mb)

                # 3. CONCURRENCY & SEQUENTIAL SWAP ENFORCEMENT
                # Check active models and evict if max_concurrent_models exceeded
                other_active_ids = [
                    inst_id for inst_id, inst in self._active_instances.items()
                    if inst_id != instance.instance_id and inst.state in (LifecycleStateEnum.READY, LifecycleStateEnum.EXECUTING)
                ]

                if other_active_ids:
                    # Enforce profile max concurrent models or sequential policy
                    if len(other_active_ids) >= profile.max_concurrent_models or profile.max_concurrent_models == 1:
                        logger.info(f"Evicting {len(other_active_ids)} active model(s) to enforce sequential lifecycle.")
                        for other_id in other_active_ids:
                            await self._unload_instance_internal(other_id, force=True)

                # 4. LOADING STATE
                instance.update_state(LifecycleStateEnum.LOADING)
                instance.loaded_at = datetime.now(timezone.utc).isoformat()
                t0 = time.perf_counter()

                # Call underlying inference engine
                await asyncio.wait_for(
                    self._engine.load_model(
                        model_id=model_id,
                        context_length=target_ctx,
                        gpu_layers_override=0 if force_cpu else fit_result.recommended_gpu_layers,
                        force_cpu=force_cpu,
                    ),
                    timeout=timeout_seconds,
                )

                t1 = time.perf_counter()
                instance.gpu_layers = 0 if force_cpu else fit_result.recommended_gpu_layers
                engine_metrics = getattr(self._engine, "metrics", None)
                instance.observed_vram_mb = getattr(engine_metrics, "vram_after_load_mb", 0.0) if engine_metrics else 0.0
                instance.observed_ram_mb = getattr(engine_metrics, "ram_after_load_mb", 0.0) if engine_metrics else 0.0

                # 5. HEALTH PROBE
                is_healthy = await self.health_probe(instance.instance_id)
                if not is_healthy:
                    instance.update_state(LifecycleStateEnum.HEALTH_DEGRADED, "Health probe check failed after model load.")
                    await self._unload_instance_internal(instance.instance_id, force=True)
                    raise RuntimeError(f"Model '{model_id}' failed post-load health probe check.")

                # 6. READY STATE
                instance.health_check_passed = True
                instance.provenance = ModelProvenance(
                    model_id=manifest.model_id,
                    model_version=manifest.version,
                    model_file_hash=manifest.sha256_checksum,
                    quantization=manifest.quantization,
                    runtime_engine=getattr(getattr(self._engine, "metrics", None), "provider_type", "NATIVE_GGUF"),
                    runtime_profile=profile.name.value,
                    context_length=target_ctx,
                    temperature=0.0,
                    seed=42,
                )
                instance.update_state(LifecycleStateEnum.READY)
                return instance

            except MemoryError as e:
                # OOM or Admission rejection
                instance.update_state(LifecycleStateEnum.OOM_RECOVERED, str(e))
                await self._unload_instance_internal(instance.instance_id, force=True)
                raise
            except Exception as e:
                instance.update_state(LifecycleStateEnum.LOAD_FAILED, str(e))
                await self._unload_instance_internal(instance.instance_id, force=True)
                raise

    async def _unload_instance_internal(self, instance_id: str, force: bool = False) -> bool:
        """Internal helper to unload and clean up a runtime instance."""
        instance = self._active_instances.get(instance_id)
        if not instance:
            return True

        instance.update_state(LifecycleStateEnum.UNLOADING)

        # 1. Stop active generation / cancel
        if instance.state == LifecycleStateEnum.EXECUTING:
            self._engine.cancel_current_generation()

        # 2. Unload from engine
        try:
            await self._engine.unload_model()
        except Exception as e:
            logger.warning(f"Error during engine unload for {instance.model_id}: {e}")

        # 3. Trigger Garbage Collection & Memory release
        gc.collect()

        # 4. Final State: RELEASED
        instance.update_state(LifecycleStateEnum.RELEASED)

        # Remove from active map
        self._active_instances.pop(instance_id, None)
        if self._model_to_instance.get(instance.model_id) == instance_id:
            self._model_to_instance.pop(instance.model_id, None)

        return True

    async def unload_model(self, model_id_or_instance_id: str) -> bool:
        """Explicitly unloads a model instance and frees resources."""
        async with self._lock:
            # Check if passed ID is instance_id or model_id
            if model_id_or_instance_id in self._active_instances:
                return await self._unload_instance_internal(model_id_or_instance_id)
            elif model_id_or_instance_id in self._model_to_instance:
                inst_id = self._model_to_instance[model_id_or_instance_id]
                return await self._unload_instance_internal(inst_id)
            return True

    async def switch_model(
        self,
        current_model_id: str,
        new_model_id: str,
        target_task: ModelTaskTypeEnum = ModelTaskTypeEnum.GENERATION,
        context_length: Optional[int] = None,
    ) -> RuntimeInstance:
        """
        Atomic sequential model swapper:
        Current Model -> Stop/Cancel -> Unload -> Preflight New Model -> Load New Model -> READY
        """
        logger.info(f"Initiating sequential model switch: '{current_model_id}' -> '{new_model_id}'")

        # 1. Unload current model
        await self.unload_model(current_model_id)

        # 2. Load new model
        new_instance = await self.load_model(
            model_id=new_model_id,
            task_type=target_task,
            context_length=context_length,
        )

        return new_instance

    async def health_probe(self, instance_id: str) -> bool:
        """Executes a lightweight readiness probe on an active instance."""
        instance = self._active_instances.get(instance_id)
        if not instance:
            return False

        try:
            return await self._engine.is_ready()
        except Exception:
            return False

    # =========================================================================
    # 2. EXECUTION & REQUEST PRIORITY QUEUE
    # =========================================================================

    async def execute_inference(
        self,
        model_id: str,
        prompt: str,
        max_tokens: int = 512,
        priority: RequestPriorityEnum = RequestPriorityEnum.NORMAL,
        timeout_seconds: float = 60.0,
    ) -> str:
        """Submits prompt for execution, queuing if model is busy or needs loading."""
        # 1. Ensure Model is Loaded
        instance = await self.load_model(model_id=model_id, timeout_seconds=timeout_seconds)

        # 2. Execute with state transition
        instance.update_state(LifecycleStateEnum.EXECUTING)
        try:
            result = await self._engine.generate_text(
                prompt=prompt,
                max_tokens=max_tokens,
                timeout_seconds=timeout_seconds,
            )
            instance.update_state(LifecycleStateEnum.READY)
            return result
        except Exception as e:
            instance.update_state(LifecycleStateEnum.EXECUTION_FAILED, str(e))
            raise

    async def stream_inference(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        priority: RequestPriorityEnum = RequestPriorityEnum.NORMAL,
        timeout_seconds: float = 60.0,
    ) -> AsyncIterator[str]:
        """Streams tokens from model with lifecycle transition tracking."""
        instance = await self.load_model(model_id=model_id, timeout_seconds=timeout_seconds)
        instance.update_state(LifecycleStateEnum.EXECUTING)

        try:
            async for token in self._engine.stream_chat(
                messages=messages,
                max_tokens=max_tokens,
                timeout_seconds=timeout_seconds,
            ):
                yield token
            instance.update_state(LifecycleStateEnum.READY)
        except Exception as e:
            instance.update_state(LifecycleStateEnum.EXECUTION_FAILED, str(e))
            raise

    def cancel_active_instance(self, instance_id: str) -> bool:
        """Cancels generation on an active instance."""
        instance = self._active_instances.get(instance_id)
        if instance and instance.state == LifecycleStateEnum.EXECUTING:
            instance.update_state(LifecycleStateEnum.CANCELLING)
            self._engine.cancel_current_generation()
            return True
        return False

    def enqueue_request(self, request: QueuedInferenceRequest) -> str:
        """Adds a request to the prioritized sequential queue."""
        self._request_queue.append(request)
        # Sort queue by priority descending (HIGH=3, NORMAL=2, LOW=1)
        self._request_queue.sort(key=lambda r: r.priority.value, reverse=True)
        return request.request_id

    def cancel_queued_request(self, request_id: str) -> bool:
        """Cancels a pending request in the queue."""
        for req in self._request_queue:
            if req.request_id == request_id and req.status == QueuedRequestStatusEnum.QUEUED:
                req.status = QueuedRequestStatusEnum.CANCELLED
                self._request_queue.remove(req)
                return True
        return False

    def get_queue_status(self) -> List[Dict[str, Any]]:
        """Returns the current queue backlog."""
        return [req.model_dump() for req in self._request_queue]

    # =========================================================================
    # 3. BACKWARD-COMPATIBLE SYNCHRONOUS METHODS
    # =========================================================================

    def release_current_model(self) -> None:
        """Synchronous legacy model release helper."""
        if self._legacy_active_model_name is not None:
            logger.info(f"Releasing model: {self._legacy_active_model_name} ({self._legacy_active_model_type})")
            self._legacy_active_model_instance = None
            self._legacy_active_model_name = None
            self._legacy_active_model_type = None
            gc.collect()

    def acquire_model(self, model_type: str, model_name: str, loader_fn) -> Any:
        """Synchronous legacy model acquisition helper."""
        if self._legacy_active_model_name == model_name and self._legacy_active_model_instance is not None:
            return self._legacy_active_model_instance

        if self._legacy_active_model_name is not None:
            self.release_current_model()

        logger.info(f"Loading model: {model_name} [Type: {model_type}]")
        instance = loader_fn()
        self._legacy_active_model_name = model_name
        self._legacy_active_model_instance = instance
        self._legacy_active_model_type = model_type
        return instance

    @contextmanager
    def model_scope(self, model_type: str, model_name: str, loader_fn):
        """Synchronous legacy context manager for temporary model usage."""
        model = self.acquire_model(model_type, model_name, loader_fn)
        try:
            yield model
        finally:
            self.release_current_model()

    def get_status(self) -> Dict[str, Any]:
        """Returns model residency and memory status."""
        active_name = self.active_model
        return {
            "active_model": active_name,
            "active_type": self._legacy_active_model_type or "GENERATION",
            "active_instances_count": len(self._active_instances),
            "is_memory_clean": len(self._active_instances) == 0 and active_name is None,
            "instances": [inst.model_dump() for inst in self._active_instances.values()],
            "queue_length": len(self._request_queue),
        }


# Global singleton lifecycle manager instance
model_lifecycle_manager = ModelLifecycleManager()
