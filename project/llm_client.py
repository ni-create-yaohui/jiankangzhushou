# -*- coding: utf-8 -*-
"""
[DEPRECATED] 此客户端已被 LangChain with_fallbacks 机制替代（见 model/factory.py）。
保留此文件供参考，新代码请勿使用。
---
LLM 容错客户端 - 支持主备 API 自动切换、网络错误重试、内容过滤回退
参考 data_analysis_agent 的 fallback_openai_client.py 设计
"""
import asyncio
from typing import Optional, Any, Dict
from openai import AsyncOpenAI, APIStatusError, APIConnectionError, APITimeoutError, APIError
from openai.types.chat import ChatCompletion

from project.logger_handler import logger


class FallbackLLMClient:
    """
    支持主备 API 自动切换的容错客户端。

    当主 API（DashScope）因网络错误、超时或内容过滤失败时，
    自动切换到备用 API（OpenAI 兼容接口）。
    """

    def __init__(
        self,
        primary_api_key: str,
        primary_base_url: str,
        primary_model_name: str,
        fallback_api_key: Optional[str] = None,
        fallback_base_url: Optional[str] = None,
        fallback_model_name: Optional[str] = None,
        max_retries_primary: int = 2,
        max_retries_fallback: int = 2,
        retry_delay_seconds: float = 1.0,
    ):
        if not primary_api_key or not primary_base_url:
            raise ValueError("主 API 密钥和基础 URL 不能为空。")

        self.primary_client = AsyncOpenAI(
            api_key=primary_api_key,
            base_url=primary_base_url,
        )
        self.primary_model_name = primary_model_name

        self.fallback_client: Optional[AsyncOpenAI] = None
        self.fallback_model_name: Optional[str] = None
        if fallback_api_key and fallback_base_url and fallback_model_name:
            self.fallback_client = AsyncOpenAI(
                api_key=fallback_api_key,
                base_url=fallback_base_url,
            )
            self.fallback_model_name = fallback_model_name
        else:
            logger.warning("未配置备用 API 客户端，主 API 失败时将无法回退。")

        self.max_retries_primary = max_retries_primary
        self.max_retries_fallback = max_retries_fallback
        self.retry_delay_seconds = retry_delay_seconds
        self._closed = False

    async def _attempt_api_call(
        self,
        client: AsyncOpenAI,
        model_name: str,
        messages: list,
        max_retries: int,
        api_label: str,
        **kwargs: Any,
    ) -> ChatCompletion:
        """尝试调用指定 API，支持指数退避重试。"""
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                completion = await client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    **kwargs,
                )
                return completion
            except (APIConnectionError, APITimeoutError) as e:
                last_exception = e
                logger.warning(
                    f"{api_label} API 网络错误 ({type(e).__name__}): {e}，"
                    f"尝试 {attempt + 1}/{max_retries + 1}"
                )
                if attempt < max_retries:
                    await asyncio.sleep(self.retry_delay_seconds * (attempt + 1))
            except APIStatusError as e:
                last_exception = e
                logger.warning(
                    f"{api_label} API 状态错误 ({e.status_code}): {e}，"
                    f"尝试 {attempt + 1}/{max_retries + 1}"
                )
                if attempt < max_retries:
                    await asyncio.sleep(self.retry_delay_seconds * (attempt + 1))
            except APIError as e:
                last_exception = e
                logger.error(f"{api_label} API 不可重试错误 ({type(e).__name__}): {e}")
                break

        if last_exception:
            raise last_exception
        raise RuntimeError(f"{api_label} API 调用意外失败。")

    async def chat(
        self,
        messages: list,
        **kwargs: Any,
    ) -> ChatCompletion:
        """
        使用主 API 调用，失败时自动回退到备用 API。
        """
        if self._closed:
            raise RuntimeError("客户端已关闭。")

        try:
            return await self._attempt_api_call(
                client=self.primary_client,
                model_name=self.primary_model_name,
                messages=messages,
                max_retries=self.max_retries_primary,
                api_label="主",
                **kwargs,
            )
        except APIError as e_primary:
            if self.fallback_client and self.fallback_model_name:
                logger.info(
                    f"主 API 失败 ({type(e_primary).__name__})，切换到备用 API..."
                )
                try:
                    result = await self._attempt_api_call(
                        client=self.fallback_client,
                        model_name=self.fallback_model_name,
                        messages=messages,
                        max_retries=self.max_retries_fallback,
                        api_label="备用",
                        **kwargs,
                    )
                    logger.info("备用 API 调用成功。")
                    return result
                except APIError as e_fallback:
                    logger.error(
                        f"备用 API 也失败: {type(e_fallback).__name__} - {e_fallback}"
                    )
                    raise e_fallback
            else:
                raise e_primary

    async def close(self):
        """关闭客户端连接。"""
        if not self._closed:
            await self.primary_client.close()
            if self.fallback_client:
                await self.fallback_client.close()
            self._closed = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
