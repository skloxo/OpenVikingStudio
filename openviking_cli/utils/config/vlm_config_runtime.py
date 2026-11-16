# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
from __future__ import annotations

import asyncio
import threading
import weakref
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from .vlm_config_models import VLMCredential, _bind_token_usage_tracker, _has_codex_auth_available


class _VLMInstanceMixin:
    """Runtime VLM instance, failover, and completion methods."""

    def _has_legacy_provider_config(self) -> bool:
        """Check if there's legacy provider config (not credentials-based)."""
        return (
            self.provider is not None
            or self.api_key is not None
            or self.api_base is not None
            or self.providers
        )

    def _get_credential_api_key(self, cred: VLMCredential) -> str | None:
        """Get effective API key for a credential, checking providers dict."""
        if cred.api_key:
            return cred.api_key
        if cred.provider and cred.provider in self.providers:
            return self.providers[cred.provider].get("api_key")
        return None

    def _has_any_config(self) -> bool:
        """Check if any config is provided."""
        if self.credentials:
            return True
        if self.api_key or self.model or self.api_base or self.provider or self.default_provider:
            return True
        if self.providers:
            return True
        return False

    def _get_effective_api_key(self) -> str | None:
        """Get effective API key."""
        if self.credentials:
            return self.credentials[0].api_key or self._get_credential_api_key(self.credentials[0])
        if self.api_key:
            return self.api_key
        config, _ = self._match_provider()
        if config and config.get("api_key"):
            return config["api_key"]
        return None

    def _get_provider_config_by_name(self, provider_name: str) -> Dict[str, Any]:
        config = dict(self.providers.get(provider_name) or {})
        if self.api_key and "api_key" not in config:
            config["api_key"] = self.api_key
        if self.forward_api_key is not None and "forward_api_key" not in config:
            config["forward_api_key"] = self.forward_api_key
        if self.api_base and "api_base" not in config:
            config["api_base"] = self.api_base
        if self.extra_headers and "extra_headers" not in config:
            config["extra_headers"] = self.extra_headers
        if self.extra_request_body and "extra_request_body" not in config:
            config["extra_request_body"] = self.extra_request_body
        if self.reasoning_effort and "reasoning_effort" not in config:
            config["reasoning_effort"] = self.reasoning_effort
        if self.keepalive_expiry is not None and "keepalive_expiry" not in config:
            config["keepalive_expiry"] = self.keepalive_expiry
        return config

    def _provider_has_usable_credentials(self, provider_name: str, config: Dict[str, Any]) -> bool:
        if config.get("api_key"):
            return True
        if provider_name == "litellm":
            return True
        if provider_name == "openai-codex":
            has_codex_auth_available = _load_codex_auth_module().has_codex_auth_available

            return has_codex_auth_available()
        return False

    def _get_provider_config_from_credential(self, cred: VLMCredential) -> Dict[str, Any]:
        config: Dict[str, Any] = {}
        if cred.api_key:
            config["api_key"] = cred.api_key
        if cred.api_base:
            config["api_base"] = cred.api_base
        if cred.api_version:
            config["api_version"] = cred.api_version
        if cred.forward_api_key is not None:
            config["forward_api_key"] = cred.forward_api_key
        if cred.extra_headers:
            config["extra_headers"] = cred.extra_headers
        if cred.extra_request_body:
            config["extra_request_body"] = cred.extra_request_body
        if cred.reasoning_effort:
            config["reasoning_effort"] = cred.reasoning_effort
        if cred.stream is not None:
            config["stream"] = cred.stream
        elif self.stream:
            config["stream"] = self.stream
        if cred.keepalive_expiry is not None:
            config["keepalive_expiry"] = cred.keepalive_expiry
        return config

    def _match_provider(self, model: str | None = None) -> tuple[Dict[str, Any] | None, str | None]:
        """Match provider config.

        Returns:
            (provider_config_dict, provider_name)
        """
        del model
        # If credentials are configured, use the first one
        if self.credentials:
            cred = self.credentials[0]
            return self._get_provider_config_from_credential(cred), cred.provider

        if self.provider:
            return self._get_provider_config_by_name(self.provider) or {}, self.provider

        if self.default_provider:
            return (
                self._get_provider_config_by_name(self.default_provider) or {},
                self.default_provider,
            )

        if len(self.providers) == 1:
            provider_name = next(iter(self.providers))
            return self._get_provider_config_by_name(provider_name), provider_name

        for provider_name in self.providers:
            config = self._get_provider_config_by_name(provider_name)
            if self._provider_has_usable_credentials(provider_name, config):
                return config, provider_name

        return None, None

    def _resolve_provider_name(self) -> str | None:
        """Resolve provider name from credentials or legacy config."""
        if self.credentials:
            return self.credentials[0].provider
        _, name = self._match_provider()
        return name

    def get_provider_config(
        self, model: str | None = None
    ) -> tuple[Dict[str, Any] | None, str | None]:
        """Get provider config.

        Returns:
            (provider_config_dict, provider_name)
        """
        return self._match_provider(model)

    def get_vlm_instance(self) -> Any:
        """Get VLM instance with multi-credential failover support."""
        if self._vlm_instance is None:
            from openviking.models.vlm import FailoverVLM, MultiCredentialVLM, VLMFactory

            if self.credentials:
                # Build VLM instances for each credential
                vlm_instances = []
                for cred in self.credentials:
                    config_dict = self._build_vlm_config_dict_for_credential(cred)
                    vlm_instances.append(VLMFactory.create(config_dict))

                if len(vlm_instances) == 1:
                    self._vlm_instance = vlm_instances[0]
                else:
                    self._vlm_instance = MultiCredentialVLM(
                        vlm_instances,
                        credential_ids=[c.id for c in self.credentials],
                        failback_timeout_seconds=self.failback_timeout_seconds,
                        failback_request_count=self.failback_request_count,
                    )
            else:
                # Legacy mode: single VLM with optional backup
                config_dict = self._build_vlm_config_dict()
                primary = VLMFactory.create(config_dict)

                if self.backup is not None and self.backup._has_any_config():
                    backup_config_dict = self.backup._build_vlm_config_dict()
                    backup = VLMFactory.create(backup_config_dict)
                    self._vlm_instance = FailoverVLM(primary, backup)
                else:
                    self._vlm_instance = primary

            if self._token_usage_tracker is not None:
                _bind_token_usage_tracker(self._vlm_instance, self._token_usage_tracker)

        return self._vlm_instance

    def set_token_usage_tracker(self, tracker: Any) -> None:
        """Bind an externally owned tracker without eagerly creating a client."""
        if self._token_usage_tracker is tracker:
            return
        self._token_usage_tracker = tracker
        if self._vlm_instance is not None:
            _bind_token_usage_tracker(self._vlm_instance, tracker)

    def close(self) -> None:
        """Close and clear the cached VLM instance."""
        instance = self._vlm_instance
        self._vlm_instance = None
        if instance is not None:
            instance.close()

    def __del__(self) -> None:
        """Release a lazily-created client when the config is no longer referenced."""
        try:
            self.close()
        except Exception:
            pass

    def build_vlm_config_dict_for_credential(self, credential: VLMCredential) -> Dict[str, Any]:
        """Return the effective backend settings for one normalized credential."""
        return self._build_vlm_config_dict_for_credential(credential)

    def _build_vlm_config_dict_for_credential(self, credential: VLMCredential) -> Dict[str, Any]:
        """Build VLM instance config dict for a specific credential."""
        result = {
            "model": credential.model or self.model,
            "cost_bearer": credential.cost_bearer,
            "temperature": self.temperature,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "keepalive_expiry": credential.keepalive_expiry,
            "provider": credential.provider,
            "thinking": self.thinking,
            "max_tokens": (
                credential.max_tokens if credential.max_tokens is not None else self.max_tokens
            ),
            "stream": credential.stream if credential.stream is not None else self.stream,
            "api_version": credential.api_version,
            "media": self.media.model_dump(),
        }

        if credential.api_key:
            result["api_key"] = credential.api_key
        if credential.forward_api_key is not None:
            result["forward_api_key"] = credential.forward_api_key
        if credential.api_base:
            result["api_base"] = credential.api_base
        if credential.extra_headers:
            result["extra_headers"] = credential.extra_headers
        if credential.extra_request_body:
            result["extra_request_body"] = credential.extra_request_body
        if credential.reasoning_effort:
            result["reasoning_effort"] = credential.reasoning_effort

        return result

    def _build_vlm_config_dict(self) -> Dict[str, Any]:
        """Build VLM instance config dict."""
        config, name = self.get_provider_config()

        result = {
            "model": self.model,
            "temperature": self.temperature,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "keepalive_expiry": (
                config.get("keepalive_expiry")
                if config and config.get("keepalive_expiry") is not None
                else self.keepalive_expiry
            ),
            "provider": name,
            "thinking": self.thinking,
            "max_tokens": self.max_tokens,
            "stream": config.get("stream") if config and config.get("stream") is not None else self.stream,
            "api_version": self.api_version,
            "media": self.media.model_dump(),
        }

        if config:
            if config.get("api_key"):
                result["api_key"] = config.get("api_key")
            if config.get("forward_api_key") is not None:
                result["forward_api_key"] = config.get("forward_api_key")
            if config.get("api_base"):
                result["api_base"] = config.get("api_base")
            if config.get("extra_headers"):
                result["extra_headers"] = config.get("extra_headers")
            if config.get("extra_request_body"):
                result["extra_request_body"] = config.get("extra_request_body")
            if config.get("reasoning_effort"):
                result["reasoning_effort"] = config.get("reasoning_effort")

        return result

    def get_completion(
        self,
        prompt: str = "",
        thinking: Optional[bool] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[str, Any]:
        """Get LLM completion."""
        effective_thinking = self.thinking if thinking is None else thinking
        return self.get_vlm_instance().get_completion(
            prompt=prompt,
            thinking=effective_thinking,
            tools=tools,
            tool_choice=tool_choice,
            messages=messages,
        )

    async def get_completion_async(
        self,
        prompt: str = "",
        thinking: Optional[bool] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
    ) -> Union[str, Any]:
        """Get LLM completion asynchronously."""
        effective_thinking = self.thinking if thinking is None else thinking
        return await self.get_vlm_instance().get_completion_async(
            prompt=prompt,
            thinking=effective_thinking,
            tools=tools,
            tool_choice=tool_choice,
            messages=messages,
            max_tokens=max_tokens,
        )

    def is_available(self) -> bool:
        """Check if LLM is configured."""
        if self._resolve_provider_name() == "openai-codex":
            has_codex_auth_available = _load_codex_auth_module().has_codex_auth_available

            return bool(self._get_effective_api_key() or has_codex_auth_available())
        if self._resolve_provider_name() == "litellm":
            return bool(self.model)
        return self._get_effective_api_key() is not None

    def get_vision_completion(
        self,
        prompt: str = "",
        images: Optional[list] = None,
        thinking: Optional[bool] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[str, Any]:
        """Get LLM completion with images."""
        effective_thinking = self.thinking if thinking is None else thinking
        return self.get_vlm_instance().get_vision_completion(
            prompt=prompt,
            images=images,
            thinking=effective_thinking,
            tools=tools,
            tool_choice=tool_choice,
            messages=messages,
        )

    def _get_media_semaphore(self) -> asyncio.Semaphore:
        loop = asyncio.get_running_loop()
        with self._media_semaphore_lock:
            semaphore_ref = self._media_semaphores.get(loop)
            semaphore = semaphore_ref() if semaphore_ref is not None else None
            if semaphore is None:
                semaphore = asyncio.Semaphore(self.media.max_concurrent)
                self._media_semaphores[loop] = weakref.ref(semaphore)
            return semaphore

    def supports_media(
        self,
        *,
        media_type: str,
        filename: str,
        size_bytes: int,
    ) -> bool:
        """Return whether enabled VLM media processing supports this input."""
        if not self.media.enabled or not self.is_available():
            return False
        return bool(
            self.get_vlm_instance().supports_media(
                media_type=media_type,
                filename=filename,
                size_bytes=size_bytes,
            )
        )

    async def get_media_completion_async(
        self,
        *,
        prompt: str,
        media_path: Path,
        filename: str,
        media_type: str,
        prepare_media: Optional[Callable[[], Awaitable[None]]] = None,
    ) -> str:
        """Stage and understand audio/video under the configured media limit."""
        from openviking.models.vlm.base import UnsupportedMediaInputError

        if not self.media.enabled:
            raise UnsupportedMediaInputError("VLM media understanding is disabled")

        async with self._get_media_semaphore():
            if prepare_media is not None:
                await prepare_media()
            return await self.get_vlm_instance().get_media_completion_async(
                prompt=prompt,
                media_path=media_path,
                filename=filename,
                media_type=media_type,
            )

    async def get_vision_completion_async(
        self,
        prompt: str = "",
        images: Optional[list] = None,
        thinking: Optional[bool] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[str, Any]:
        """Get LLM completion with images asynchronously."""
        effective_thinking = self.thinking if thinking is None else thinking
        return await self.get_vlm_instance().get_vision_completion_async(
            prompt=prompt,
            images=images,
            thinking=effective_thinking,
            tools=tools,
            tool_choice=tool_choice,
            messages=messages,
        )
