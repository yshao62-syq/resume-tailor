"""LLM 配置：从环境变量读取，provider 无关。

设计原则：工具用"运行者自己的 LLM API"，不绑死任何厂商。
支持两种兼容协议（绝大多数厂商走其一）：
  - anthropic-compatible：ANTHROPIC_AUTH_TOKEN / ANTHROPIC_API_KEY + ANTHROPIC_BASE_URL + ANTHROPIC_MODEL
    （智谱 BigModel 的 /api/anthropic 端点、各类 Claude 代理都走这条）
  - openai-compatible：OPENAI_API_KEY + OPENAI_BASE_URL + OPENAI_MODEL
"""
import os
from dataclasses import dataclass


def sanitize_model(name: str) -> str:
    """剥掉 router/客户端自用的标记后缀，比如 glm-5.2[1m] -> glm-5.2。

    [1m] 这类是 Claude Code 等客户端用来选上下文窗口的内部标记，
    直接发给底层 API 会被拒（"模型不存在"）。"""
    if not name:
        return name
    return name.split("[")[0].strip()


@dataclass
class LLMConfig:
    provider: str        # "anthropic" | "openai"
    base_url: str | None
    api_key: str | None       # openai-compatible / x-api-key
    auth_token: str | None    # anthropic-compatible Bearer
    model: str


def load_llm_config() -> LLMConfig:
    # 1) anthropic-compatible
    if os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY"):
        return LLMConfig(
            provider="anthropic",
            base_url=os.environ.get("ANTHROPIC_BASE_URL") or None,
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
            auth_token=os.environ.get("ANTHROPIC_AUTH_TOKEN"),
            model=sanitize_model(os.environ.get("ANTHROPIC_MODEL") or "glm-5.2"),
        )
    # 2) openai-compatible
    if os.environ.get("OPENAI_API_KEY"):
        return LLMConfig(
            provider="openai",
            base_url=os.environ.get("OPENAI_BASE_URL") or None,
            api_key=os.environ.get("OPENAI_API_KEY"),
            auth_token=None,
            model=sanitize_model(os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"),
        )
    raise RuntimeError(
        "没找到 LLM 凭证。请设置 ANTHROPIC_AUTH_TOKEN/ANTHROPIC_BASE_URL/ANTHROPIC_MODEL "
        "或 OPENAI_API_KEY/OPENAI_BASE_URL/OPENAI_MODEL。"
    )
