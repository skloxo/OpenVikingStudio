# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""VLM Token usage monitoring data structures"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from openviking.utils.time_utils import format_iso8601
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_USAGE_FILE = Path(os.path.expanduser("~/.openviking/models_token_usage.json"))


@dataclass
class TokenUsage:
    """Token usage statistics"""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    call_count: int = 0
    last_updated: datetime = field(default_factory=datetime.now)

    def update(self, prompt_tokens: int, completion_tokens: int) -> None:
        """Update token usage

        Args:
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
        """
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.total_tokens = self.prompt_tokens + self.completion_tokens
        self.call_count += 1
        self.last_updated = datetime.now()

    def reset(self) -> None:
        """Reset token usage statistics"""
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.call_count = 0
        self.last_updated = datetime.now()

    def to_dict(self) -> Dict:
        """Convert to dictionary format

        Returns:
            Token usage dictionary
        """
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "call_count": self.call_count,
            "last_updated": format_iso8601(self.last_updated),
        }

    def __str__(self) -> str:
        return (
            f"TokenUsage(prompt={self.prompt_tokens}, "
            f"completion={self.completion_tokens}, "
            f"total={self.total_tokens}, "
            f"calls={self.call_count})"
        )


@dataclass
class ModelTokenUsage:
    """Token usage statistics by model"""

    model_name: str
    total_usage: TokenUsage = field(default_factory=TokenUsage)
    usage_by_provider: Dict[str, TokenUsage] = field(default_factory=dict)

    def update(self, provider: str, prompt_tokens: int, completion_tokens: int) -> None:
        """Update token usage for specified provider

        Args:
            provider: Provider name (openai, volcengine)
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
        """
        # Update total usage
        self.total_usage.update(prompt_tokens, completion_tokens)

        # Update provider usage
        if provider not in self.usage_by_provider:
            self.usage_by_provider[provider] = TokenUsage()

        self.usage_by_provider[provider].update(prompt_tokens, completion_tokens)

    def get_provider_usage(self, provider: str) -> Optional[TokenUsage]:
        """Get token usage for specified provider

        Args:
            provider: Provider name

        Returns:
            TokenUsage object, or None if provider doesn't exist
        """
        return self.usage_by_provider.get(provider)

    def to_dict(self) -> Dict:
        """Convert to dictionary format

        Returns:
            Token usage statistics in dictionary format
        """
        result = {
            "model_name": self.model_name,
            "total_usage": self.total_usage.to_dict(),
            "usage_by_provider": {},
        }

        for provider, usage in self.usage_by_provider.items():
            result["usage_by_provider"][provider] = usage.to_dict()

        return result

    def __str__(self) -> str:
        providers = ", ".join(
            [
                f"{provider}: {usage.total_tokens}"
                for provider, usage in self.usage_by_provider.items()
            ]
        )
        return f"ModelTokenUsage(model={self.model_name}, total={self.total_usage.total_tokens}, providers=[{providers}])"


class TokenUsageTracker:
    """Token usage tracker with JSON persistence"""

    def __init__(self, persistence_file: Optional[Path] = None, auto_load: bool = True):
        self._usage_by_model: Dict[str, ModelTokenUsage] = {}
        self._persistence_file = persistence_file or _DEFAULT_USAGE_FILE
        if auto_load:
            self.load_from_disk()

    def load_from_disk(self, file_path: Optional[Path] = None) -> None:
        """Load persistent token usage data from JSON file."""
        target_path = file_path or self._persistence_file
        if not target_path or not target_path.is_file():
            return
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            usage_by_model = data.get("usage_by_model", {})
            for model_name, m_data in usage_by_model.items():
                if model_name not in self._usage_by_model:
                    self._usage_by_model[model_name] = ModelTokenUsage(model_name)
                for provider_name, p_data in m_data.get("usage_by_provider", {}).items():
                    prompt = p_data.get("prompt_tokens", 0)
                    completion = p_data.get("completion_tokens", 0)
                    calls = p_data.get("call_count", 0)
                    last_updated_str = p_data.get("last_updated")

                    if provider_name not in self._usage_by_model[model_name].usage_by_provider:
                        self._usage_by_model[model_name].usage_by_provider[provider_name] = TokenUsage()

                    p_usage = self._usage_by_model[model_name].usage_by_provider[provider_name]
                    p_usage.prompt_tokens = prompt
                    p_usage.completion_tokens = completion
                    p_usage.total_tokens = prompt + completion
                    p_usage.call_count = calls
                    if last_updated_str:
                        try:
                            clean_str = last_updated_str.replace("Z", "+00:00")
                            p_usage.last_updated = datetime.fromisoformat(clean_str)
                        except Exception:
                            pass

                # Recompute total usage for model
                total = TokenUsage()
                for p_usage in self._usage_by_model[model_name].usage_by_provider.values():
                    total.prompt_tokens += p_usage.prompt_tokens
                    total.completion_tokens += p_usage.completion_tokens
                    total.total_tokens += p_usage.total_tokens
                    total.call_count += p_usage.call_count
                self._usage_by_model[model_name].total_usage = total
        except Exception as e:
            logger.debug(f"Error loading models_token_usage.json: {e}")

    def save_to_disk(self, file_path: Optional[Path] = None) -> None:
        """Persist current token usage data to JSON file."""
        target_path = file_path or self._persistence_file
        if not target_path:
            return
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = target_path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            tmp_path.replace(target_path)
        except Exception as e:
            logger.debug(f"Error saving models_token_usage.json: {e}")

    def update(
        self, model_name: str, provider: str, prompt_tokens: int, completion_tokens: int
    ) -> None:
        """Update token usage

        Args:
            model_name: Model name
            provider: Provider name
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
        """
        if model_name not in self._usage_by_model:
            self._usage_by_model[model_name] = ModelTokenUsage(model_name)

        self._usage_by_model[model_name].update(provider, prompt_tokens, completion_tokens)
        self.save_to_disk()

    def get_model_usage(self, model_name: str) -> Optional[ModelTokenUsage]:
        """Get token usage for specified model

        Args:
            model_name: Model name

        Returns:
            ModelTokenUsage object, or None if model doesn't exist
        """
        return self._usage_by_model.get(model_name)

    def get_all_usage(self) -> Dict[str, ModelTokenUsage]:
        """Get token usage for all models

        Returns:
            Token usage dictionary by model
        """
        return self._usage_by_model.copy()

    def get_total_usage(self) -> TokenUsage:
        """Get total token usage

        Returns:
            Total token usage statistics
        """
        total = TokenUsage()
        for model_usage in self._usage_by_model.values():
            total.prompt_tokens += model_usage.total_usage.prompt_tokens
            total.completion_tokens += model_usage.total_usage.completion_tokens

            total.total_tokens += model_usage.total_usage.total_tokens

        return total

    def reset(self) -> None:
        """Reset all token usage statistics"""
        self._usage_by_model.clear()

    def to_dict(self) -> Dict:
        """Convert to dictionary format

        Returns:
            Token usage statistics in dictionary format
        """
        result = {
            "total_usage": self.get_total_usage().to_dict(),
            "usage_by_model": {},
        }

        for model_name, model_usage in self._usage_by_model.items():
            result["usage_by_model"][model_name] = model_usage.to_dict()

        return result

    def __str__(self) -> str:
        models = ", ".join(
            [
                f"{model}: {usage.total_usage.total_tokens}"
                for model, usage in self._usage_by_model.items()
            ]
        )
        total = self.get_total_usage()
        return f"TokenUsageTracker(total={total.total_tokens}, models=[{models}])"

    @staticmethod
    def merge(*trackers: "TokenUsageTracker") -> "TokenUsageTracker":
        """Merge multiple TokenUsageTracker instances into one.

        Args:
            *trackers: One or more TokenUsageTracker instances to merge

        Returns:
            New TokenUsageTracker with merged data
        """
        merged = TokenUsageTracker()

        for tracker in trackers:
            for model_name, model_usage in tracker._usage_by_model.items():
                for provider_name, provider_usage in model_usage.usage_by_provider.items():
                    merged.update(
                        model_name=model_name,
                        provider=provider_name,
                        prompt_tokens=provider_usage.prompt_tokens,
                        completion_tokens=provider_usage.completion_tokens,
                    )
                    # Update call count (update() only increments by 1)
                    if provider_usage.call_count > 1:
                        merged_model = merged._usage_by_model[model_name]
                        merged_provider = merged_model.usage_by_provider[provider_name]
                        merged_provider.call_count = provider_usage.call_count
                        # Update last_updated
                        merged_provider.last_updated = provider_usage.last_updated

        return merged
