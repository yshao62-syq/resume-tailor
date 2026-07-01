"""LLM 客户端封装：provider 无关，结构化输出（strict-JSON 提示 + pydantic 校验 + 一次重试）。

结构化输出用"提示返回纯 JSON + pydantic 校验"而非原生 tool/schema，
因为这是跨 provider 最稳的方式（智谱/Anthropic/OpenAI 兼容端点都能跑）。
"""
import json
import re
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from config import LLMConfig

T = TypeVar("T", bound=BaseModel)


def _extract_json(text: str) -> dict:
    """从模型回复里抠出 JSON：去掉 markdown 代码围栏，用容错解析器修常见瑕疵
   （尾逗号、未转义引号、截断等），修不好再让上层走 LLM 修复兜底。"""
    from json_repair import repair_json

    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1).strip()
    obj = repair_json(text, return_objects=True)
    if isinstance(obj, dict):
        return obj
    # 兜底：手动切最外层 { } 再硬解析
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        return json.loads(text[start : end + 1])
    return json.loads(text)


class LLMClient:
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        if cfg.provider == "anthropic":
            import anthropic

            kw = {"base_url": cfg.base_url} if cfg.base_url else {}
            if cfg.auth_token:
                kw["auth_token"] = cfg.auth_token
            elif cfg.api_key:
                kw["api_key"] = cfg.api_key
            self._client = anthropic.Anthropic(**kw)
        elif cfg.provider == "openai":
            import openai

            kw = {"api_key": cfg.api_key}
            if cfg.base_url:
                kw["base_url"] = cfg.base_url
            self._client = openai.OpenAI(**kw)
        else:
            raise ValueError(f"未知 provider: {cfg.provider}")

    def chat(self, system: str, user: str, *, max_tokens: int = 2048, temperature: float = 0.2) -> str:
        last_err = None
        for attempt in range(3):
            try:
                if self.cfg.provider == "anthropic":
                    r = self._client.messages.create(
                        model=self.cfg.model,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        system=system,
                        messages=[{"role": "user", "content": user}],
                    )
                    return "".join(b.text for b in r.content if getattr(b, "type", None) == "text")
                r = self._client.chat.completions.create(
                    model=self.cfg.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )
                return r.choices[0].message.content or ""
            except Exception as e:
                last_err = e
                msg = str(e)
                # GLM 内容安全拦截（1301/敏感内容）常是随机误判，重试通常能过
                is_filter = any(k in msg for k in ("1301", "敏感", "safety", "content filter", "content_policy"))
                if is_filter and attempt < 2:
                    continue
                raise
        raise last_err

    def structured(
        self, system: str, user: str, model_cls: Type[T], *, max_tokens: int = 4096, temperature: float = 0.2
    ) -> T:
        schema = json.dumps(model_cls.model_json_schema(), ensure_ascii=False)
        sys2 = (
            system
            + "\n\n你必须返回严格 JSON，且符合下面这个 schema。只返回 JSON 本身，"
            "不要任何解释文字、不要 markdown 代码围栏。\nSchema:\n"
            + schema
        )
        raw = self.chat(sys2, user, max_tokens=max_tokens, temperature=temperature)
        last_raw = raw
        try:
            return model_cls.model_validate(_extract_json(raw))
        except (ValidationError, json.JSONDecodeError):
            # 第二次：把"必须严格按 schema 返回纯 JSON"再强调一遍
            last_raw = self.chat(
                sys2,
                user + "\n\n上次返回的内容无法按 schema 解析，请严格只返回符合 schema 的纯 JSON。",
                max_tokens=max_tokens,
                temperature=0.0,
            )
            try:
                return model_cls.model_validate(_extract_json(last_raw))
            except (ValidationError, json.JSONDecodeError):
                pass
        # 最后兜底：让模型按 schema 修自己吐的 JSON（schema 感知，避免丢字段）
        repair = self.chat(
            "你是 JSON 修复器。下面是一段可能损坏或被截断的 JSON。请按下面 schema 输出"
            "严格合法、完整的 JSON（只输出 JSON 本身），必须包含 schema 的所有字段，"
            "数组字段尽量还原原内容、不要丢成空。\nSchema:\n" + schema,
            "损坏的 JSON:\n" + last_raw,
            max_tokens=max_tokens,
            temperature=0.0,
        )
        try:
            return model_cls.model_validate(_extract_json(repair))
        except (ValidationError, json.JSONDecodeError) as e:
            raise ValueError(
                f"结构化输出解析失败 schema={model_cls.__name__}: {e}\n原始返回片段: {last_raw[:300]!r}"
            ) from e
