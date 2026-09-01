"""
Token Budgeter Module
Calculates explicit token budget allocations, counts exact/estimated tokens,
and enforces model context limits dynamically.
"""

import math
from typing import Callable, Optional
from ai.context.models import CountingModeEnum, TokenBudgetSpec
from ai.registry.models import ModelManifest


class TokenBudgeter:
    """
    Deterministic Token Budgeting Engine.
    Partitions model context window into system, user, evidence, reserved output, and safety buffers.
    """

    def __init__(
        self,
        default_context_limit: int = 4096,
        default_reserved_output: int = 512,
        default_safety_reserve: int = 64,
        tokenizer_fn: Optional[Callable[[str], int]] = None,
    ):
        self._default_context_limit = default_context_limit
        self._default_reserved_output = default_reserved_output
        self._default_safety_reserve = default_safety_reserve
        self._tokenizer_fn = tokenizer_fn

    def count_tokens(self, text: str) -> tuple[int, CountingModeEnum]:
        """
        Counts tokens in text using exact tokenizer if available, or conservative estimator.
        Returns: (token_count, counting_mode)
        """
        if not text or not text.strip():
            return 0, CountingModeEnum.EXACT_TOKEN_COUNT if self._tokenizer_fn else CountingModeEnum.ESTIMATED_TOKEN_COUNT

        if self._tokenizer_fn:
            try:
                count = self._tokenizer_fn(text)
                return max(1, count), CountingModeEnum.EXACT_TOKEN_COUNT
            except Exception:
                pass

        # Conservative offline token estimation (avg 3.8 chars per token + 15% safety buffer)
        clean_text = text.strip()
        estimated = math.ceil((len(clean_text) / 3.8) * 1.15)
        return max(1, estimated), CountingModeEnum.ESTIMATED_TOKEN_COUNT

    def calculate_budget(
        self,
        model_manifest: Optional[ModelManifest] = None,
        system_prompt: str = "",
        user_prompt: str = "",
        override_context_limit: Optional[int] = None,
        reserved_output_tokens: Optional[int] = None,
        safety_reserve_tokens: Optional[int] = None,
    ) -> TokenBudgetSpec:
        """
        Calculates dynamic token budget allocation based on active model and inputs.
        """
        # Determine model context limit from manifest or override
        if override_context_limit is not None:
            context_limit = override_context_limit
        elif model_manifest:
            context_limit = model_manifest.recommended_context_length or model_manifest.context_length
        else:
            context_limit = self._default_context_limit

        reserved_output = (
            reserved_output_tokens
            if reserved_output_tokens is not None
            else self._default_reserved_output
        )
        safety_reserve = (
            safety_reserve_tokens
            if safety_reserve_tokens is not None
            else self._default_safety_reserve
        )

        sys_tokens, sys_mode = self.count_tokens(system_prompt)
        usr_tokens, usr_mode = self.count_tokens(user_prompt)

        # Budget equation: Max Evidence = Context Limit - (System + User + Output + Safety)
        fixed_overhead = sys_tokens + usr_tokens + reserved_output + safety_reserve
        max_evidence = max(0, context_limit - fixed_overhead)

        overall_mode = (
            CountingModeEnum.EXACT_TOKEN_COUNT
            if (sys_mode == CountingModeEnum.EXACT_TOKEN_COUNT and usr_mode == CountingModeEnum.EXACT_TOKEN_COUNT)
            else CountingModeEnum.ESTIMATED_TOKEN_COUNT
        )

        model_id = model_manifest.model_id if model_manifest else "default-model"

        return TokenBudgetSpec(
            model_id=model_id,
            model_context_limit=context_limit,
            system_tokens=sys_tokens,
            user_tokens=usr_tokens,
            reserved_output_tokens=reserved_output,
            safety_reserve_tokens=safety_reserve,
            max_evidence_tokens=max_evidence,
            counting_mode=overall_mode,
        )


# Global singleton
token_budgeter = TokenBudgeter()
