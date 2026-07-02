"""工位 1b · narrative synthesis（职业主线推断 + 取舍）。

候选人不会主动总结自己的职业主线。跨所有经历的真实事实，推断一条贯穿故事线
（例如：数据型 PM → 大模型对话 workflow → SOTA+skill+ReAct 做 agent harness）。
再结合目标 JD 决定每条经历的取舍：heavy 重点写 / light 一句带过 / drop 不写。

推断结果给候选人确认后再用于改写（确认环节在 agent.py）。
铁律：主线和定位只能基于真实事实，严禁编造经历里没有的能力或项目。
"""
from llm import LLMClient
from models import Experience, JDAnalysis, Narrative

SYS = (
    "你是职业主线推断器。候选人不会主动总结自己的职业主线，你要从 ta 所有经历的真实事实里，"
    "推断出一条贯穿的故事线（例如：数据型 PM → 大模型对话 workflow → SOTA+skill+ReAct 做 agent harness）。\n"
    "再结合目标 JD，决定每条经历的取舍：\n"
    "  - heavy：与 JD 主线强相关、重点写\n"
    "  - light：相关但非核心、一句带过\n"
    "  - drop：与 JD 无关或会稀释主线、不写\n"
    "铁律：主线和定位必须基于真实事实，严禁编造经历里没有的能力或项目。"
    "decisions 必须覆盖每一条经历 id。"
)


def synthesize(
    client: LLMClient, exps: list[Experience], jd: JDAnalysis, bg_type: str
) -> Narrative:
    facts_block = "\n".join(
        f"[{e.id}] {e.role} @ {e.org} ({e.dates}):\n"
        + "\n".join(f"  - {f.fact}" for f in e.facts)
        for e in exps
    ) or "(无)"
    user = (
        f"候选人背景类型: {bg_type}\n"
        f"目标 JD 必须 skill: {jd.required_skills}\n"
        f"目标 JD 关键词: {jd.required_keywords}\n\n"
        "【所有经历的真实事实】:\n"
        f"{facts_block}\n\n"
        "推断职业主线 mainline + 适配 JD 的 positioning + 每条经历的 emphasis（heavy/light/drop）。"
    )
    return client.structured(SYS, user, Narrative, temperature=0.3)
