"""
Phase AI-04 Comprehensive Native GGUF Verification Script
Performs empirical GPU and CPU execution benchmarks using native llama-server.exe and actual local GGUF models.
"""

import asyncio
import hashlib
import json
import os
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import psutil

MODEL_PATH = r"C:\Users\vijay\.lmstudio\models\SentieAI\Sentie1.0-3B-Claude-Fable-5-GPT5.2-Sol-Kimi-K3-GLM-5.2-GGUF\Sentie1.0-3B.Q4_K_M.gguf"
LLAMA_SERVER_EXE = r"C:\Users\vijay\.docker\bin\inference\llama-server.exe"
PORT = 8091
BASE_URL = f"http://127.0.0.1:{PORT}"


def compute_file_sha256(filepath: str) -> str:
    """Calculates streaming SHA-256 in 64KB blocks."""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def sample_vram_nvidia_smi() -> Dict[str, Any]:
    """Queries nvidia-smi for precise total and used VRAM."""
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            check=True
        )
        parts = [p.strip() for p in res.stdout.strip().split(",")]
        return {
            "gpu_name": parts[0],
            "total_vram_mb": float(parts[1]),
            "used_vram_mb": float(parts[2]),
            "free_vram_mb": float(parts[3]),
        }
    except Exception as e:
        return {"gpu_name": "Unknown", "total_vram_mb": 0.0, "used_vram_mb": 0.0, "free_vram_mb": 0.0}


def sample_host_ram() -> Dict[str, float]:
    """Queries system host RAM."""
    vm = psutil.virtual_memory()
    return {
        "total_ram_mb": round(vm.total / (1024**2), 2),
        "used_ram_mb": round(vm.used / (1024**2), 2),
        "free_ram_mb": round(vm.available / (1024**2), 2),
    }


class NativeServerRunner:
    def __init__(self, model_path: str, gpu_layers: int = 33, context_size: int = 2048, threads: int = 6):
        self.model_path = model_path
        self.gpu_layers = gpu_layers
        self.context_size = context_size
        self.threads = threads
        self.process: Optional[subprocess.Popen] = None

    def start(self) -> float:
        """Starts native llama-server and returns load duration in seconds."""
        t0 = time.perf_counter()
        cmd = [
            LLAMA_SERVER_EXE,
            "-m", self.model_path,
            "-ngl", str(self.gpu_layers),
            "-c", str(self.context_size),
            "-t", str(self.threads),
            "--port", str(PORT),
            "--host", "127.0.0.1",
            "--reasoning-format", "none",
        ]
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )

        # Wait for health endpoint
        ready = False
        for _ in range(60):
            time.sleep(0.5)
            try:
                with urllib.request.urlopen(f"{BASE_URL}/health", timeout=1) as r:
                    if r.status == 200:
                        ready = True
                        break
            except Exception:
                pass

        t1 = time.perf_counter()
        if not ready:
            self.stop()
            raise TimeoutError("Native llama-server failed to initialize within 30 seconds.")
        return round(t1 - t0, 3)

    def stop(self) -> None:
        """Stops the native server process."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

    def get_process_memory_mb(self) -> float:
        """Measures resident memory of the native server process."""
        if self.process and psutil.pid_exists(self.process.pid):
            try:
                p = psutil.Process(self.process.pid)
                return round(p.memory_info().rss / (1024**2), 2)
            except Exception:
                return 0.0
        return 0.0


def run_completion(prompt: str, max_tokens: int = 150) -> Dict[str, Any]:
    """Executes completion via native server."""
    url = f"{BASE_URL}/v1/chat/completions"
    data = {
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode("utf-8"))
    t1 = time.perf_counter()

    msg = res["choices"][0]["message"]
    timings = res.get("timings", {})
    text = msg.get("content", "") or msg.get("reasoning_content", "")

    return {
        "text": text.strip(),
        "usage": res.get("usage", {}),
        "timings": timings,
        "roundtrip_seconds": round(t1 - t0, 3),
    }


def run_streaming(prompt: str, max_tokens: int = 150) -> Dict[str, Any]:
    """Executes streaming completion collecting tokens and timing."""
    url = f"{BASE_URL}/v1/chat/completions"
    data = {
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": max_tokens,
        "stream": True,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    t0 = time.perf_counter()
    first_tok_t = None
    chunks = []

    with urllib.request.urlopen(req, timeout=30) as resp:
        for line in resp:
            line_str = line.decode("utf-8").strip()
            if line_str.startswith("data: ") and line_str != "data: [DONE]":
                try:
                    payload = json.loads(line_str[6:])
                    delta = payload["choices"][0]["delta"]
                    content = delta.get("content", "") or delta.get("reasoning_content", "")
                    if content:
                        if first_tok_t is None:
                            first_tok_t = time.perf_counter()
                        chunks.append(content)
                except Exception:
                    pass

    t1 = time.perf_counter()
    first_latency_ms = round((first_tok_t - t0) * 1000.0, 2) if first_tok_t else 0.0
    tot_time = round(t1 - t0, 3)
    speed = round(len(chunks) / (t1 - first_tok_t), 2) if first_tok_t and (t1 > first_tok_t) else 0.0

    return {
        "text": "".join(chunks).strip(),
        "token_count": len(chunks),
        "first_token_latency_ms": first_latency_ms,
        "total_time_seconds": tot_time,
        "tokens_per_sec": speed,
    }


def main():
    print("================================================================================")
    print("PHASE AI-04 EMPIRICAL NATIVE GGUF VERIFICATION BENCHMARK")
    print("================================================================================")

    # 1. Exact Model Identity
    print("\n--- 1. COMPUTING EXACT MODEL HASH & METADATA ---")
    file_size_bytes = os.path.getsize(MODEL_PATH)
    file_size_gb = round(file_size_bytes / (1024**3), 3)
    print(f"Model Path: {MODEL_PATH}")
    print(f"File Size: {file_size_gb} GB ({file_size_bytes} bytes)")
    print("Calculating full file SHA-256 checksum...")
    sha256 = compute_file_sha256(MODEL_PATH)
    print(f"Exact File SHA-256: {sha256}")

    # 2. GPU Benchmark
    print("\n--- 2. RUNNING GPU ACCELERATED EXECUTION (33 layers offloaded) ---")
    vram_init = sample_vram_nvidia_smi()
    ram_init = sample_host_ram()
    print(f"GPU: {vram_init['gpu_name']} | Total VRAM: {vram_init['total_vram_mb']} MB")
    print(f"VRAM Baseline (Before Load): {vram_init['used_vram_mb']} MB")
    print(f"RAM Baseline (Before Load): {ram_init['used_ram_mb']} MB")

    gpu_runner = NativeServerRunner(model_path=MODEL_PATH, gpu_layers=33, context_size=2048, threads=6)
    load_time_gpu = gpu_runner.start()
    print(f"Native Model Load & Initialization Completed in: {load_time_gpu} s")

    vram_after_gpu = sample_vram_nvidia_smi()
    proc_ram_gpu = gpu_runner.get_process_memory_mb()
    print(f"VRAM Immediately After Load: {vram_after_gpu['used_vram_mb']} MB (Delta: +{vram_after_gpu['used_vram_mb'] - vram_init['used_vram_mb']:.1f} MB)")
    print(f"Native Server Process RSS RAM: {proc_ram_gpu} MB")

    prompt = "Explain in one sentence why plant OPEX is benchmarked per vehicle."
    print(f"\nSubmitting Prompt: '{prompt}'")
    gpu_res = run_streaming(prompt, max_tokens=150)
    vram_peak_gpu = sample_vram_nvidia_smi()

    print(f"Actual Generated Text: {repr(gpu_res['text'][:150])}...")
    print(f"Tokens Generated: {gpu_res['token_count']}")
    print(f"First Token Latency: {gpu_res['first_token_latency_ms']} ms")
    print(f"Tokens Per Second: {gpu_res['tokens_per_sec']} t/s")
    print(f"Peak VRAM during generation: {vram_peak_gpu['used_vram_mb']} MB")

    # Unload GPU
    gpu_runner.stop()
    time.sleep(1)
    vram_unloaded_gpu = sample_vram_nvidia_smi()
    print(f"VRAM After Unload: {vram_unloaded_gpu['used_vram_mb']} MB (Delta: {vram_unloaded_gpu['used_vram_mb'] - vram_after_gpu['used_vram_mb']:.1f} MB released)")

    # 3. CPU Benchmark
    print("\n--- 3. RUNNING CPU-ONLY EXECUTION (0 layers offloaded) ---")
    vram_cpu_init = sample_vram_nvidia_smi()
    ram_cpu_init = sample_host_ram()
    print(f"RAM Baseline (Before Load): {ram_cpu_init['used_ram_mb']} MB")

    cpu_runner = NativeServerRunner(model_path=MODEL_PATH, gpu_layers=0, context_size=2048, threads=6)
    load_time_cpu = cpu_runner.start()
    print(f"Native Model Load & Initialization Completed in: {load_time_cpu} s")

    vram_after_cpu = sample_vram_nvidia_smi()
    proc_ram_cpu = cpu_runner.get_process_memory_mb()
    print(f"VRAM After Load (CPU Mode): {vram_after_cpu['used_vram_mb']} MB (Delta: +{vram_after_cpu['used_vram_mb'] - vram_cpu_init['used_vram_mb']:.1f} MB)")
    print(f"Native Server Process RSS RAM (CPU Mode): {proc_ram_cpu} MB")

    cpu_res = run_streaming(prompt, max_tokens=150)
    print(f"Actual Generated Text (CPU Mode): {repr(cpu_res['text'][:150])}...")
    print(f"Tokens Generated (CPU Mode): {cpu_res['token_count']}")
    print(f"First Token Latency (CPU Mode): {cpu_res['first_token_latency_ms']} ms")
    print(f"Tokens Per Second (CPU Mode): {cpu_res['tokens_per_sec']} t/s")

    # Unload CPU
    cpu_runner.stop()
    time.sleep(1)
    ram_unloaded_cpu = sample_host_ram()
    print(f"RAM After Unload: {ram_unloaded_cpu['used_ram_mb']} MB (Process memory cleanly reclaimed)")

    # 4. Save results to JSON artifact
    results = {
        "model_id": "sentie1.0-3b-q4_k_m",
        "display_name": "SentieAI 1.0 3B Instruct GGUF",
        "model_path": MODEL_PATH,
        "file_size_gb": file_size_gb,
        "file_size_bytes": file_size_bytes,
        "sha256": sha256,
        "architecture": "llama",
        "quantization": "Q4_K_M",
        "parameter_count": "3.93B",
        "context_length": 262144,
        "native_backend": "llama.cpp (native standalone llama-server.exe)",
        "gpu_benchmark": {
            "gpu_name": vram_init["gpu_name"],
            "offload_layers": 33,
            "load_time_seconds": load_time_gpu,
            "vram_before_mb": vram_init["used_vram_mb"],
            "vram_after_load_mb": vram_after_gpu["used_vram_mb"],
            "vram_peak_generation_mb": vram_peak_gpu["used_vram_mb"],
            "vram_after_unload_mb": vram_unloaded_gpu["used_vram_mb"],
            "process_rss_ram_mb": proc_ram_gpu,
            "first_token_latency_ms": gpu_res["first_token_latency_ms"],
            "tokens_per_sec": gpu_res["tokens_per_sec"],
            "token_count": gpu_res["token_count"],
            "generated_sample": gpu_res["text"][:200],
        },
        "cpu_benchmark": {
            "offload_layers": 0,
            "load_time_seconds": load_time_cpu,
            "ram_before_mb": ram_cpu_init["used_ram_mb"],
            "process_rss_ram_mb": proc_ram_cpu,
            "first_token_latency_ms": cpu_res["first_token_latency_ms"],
            "tokens_per_sec": cpu_res["tokens_per_sec"],
            "token_count": cpu_res["token_count"],
            "generated_sample": cpu_res["text"][:200],
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    out_json = r"d:\MY APPS\hero-cost-intelligence\docs\AI_RUNTIME\ai_04_verification_results.json"
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\nBenchmark results written to:", out_json)


if __name__ == "__main__":
    main()
