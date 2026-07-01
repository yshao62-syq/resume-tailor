"""工位 0 · 采集与入口（Phase 0 简化版）。

读取用户的简历档案 YAML（experiences + jd + bg_type）。
Phase 0 先支持"粘贴/手填"入口；对话挖掘和逐字稿解析留到后面阶段。
"""
import yaml

from models import Experience


def load_profile(path: str):
    """返回 (experiences, jd_text, bg_type)。"""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    raw_exps = data.get("experiences", [])
    exps: list[Experience] = []
    for i, e in enumerate(raw_exps):
        e = dict(e)
        e.setdefault("id", f"exp{i}")
        # YAML 会把 2024 这种猜成 int，强制标量字段转 str，避免类型校验失败
        for k in ("id", "type", "role", "org", "dates"):
            if e.get(k) is not None:
                e[k] = str(e[k])
        exps.append(Experience(**e))

    jd = data.get("jd", "") or ""
    bg_type = data.get("bg_type", "product")
    return exps, jd, bg_type


def load_jd_file(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read().strip()
