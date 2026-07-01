"""工位 2 · 事实保险箱（采集即隔离）。

每段经历一进来，就把它的原文抽成原子事实，锁进自己的容器。
从这一刻起，这段经历的事实就和别段隔离了——这是杜绝跨项目腾挪的第一道闸。
"""
from llm import LLMClient
from models import Experience, FactList

SYS = (
    "你是简历事实抽取器。从一段经历原文里抽出原子事实。\n"
    "要求：\n"
    "1. 每条事实是 claim 级别的一句话，必须能被原文直接支持，绝不推断或补全。\n"
    "2. 把指标/数字类的事实标记 is_metric=true（比如提升了 X%、带 N 人、月均 Y 次）。\n"
    "3. 宁可多抽几条具体的，不要抽成笼统总结。"
)


def extract_facts(client: LLMClient, exp: Experience) -> Experience:
    user = (
        f"经历ID: {exp.id}\n"
        f"类型: {exp.type} | 角色: {exp.role} @ {exp.org} ({exp.dates})\n"
        f"原文:\n{exp.original_text}\n\n"
        "抽出原子事实列表。"
    )
    out = client.structured(SYS, user, FactList, temperature=0.0)
    exp.facts = out.facts
    return exp
