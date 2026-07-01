"""工位 1 · JD 分析 + 岗位原型判断。"""
from llm import LLMClient
from models import JDAnalysis

SYS = (
    "你是 JD（招聘要求）分析器。从 JD 里抽出：\n"
    "- required_skills：必须的技能/工具/方法论\n"
    "- required_keywords：简历里该出现的关键词\n"
    "- responsibilities：核心职责\n"
    "- archetype_hint：岗位原型，从 {ai_builder_product, ai_builder_tech, general} 里选一个。"
    "ai_builder_product=偏产品/AI PM 向的 builder；ai_builder_tech=偏研发/工程向的 builder；都不是就 general。"
)


def analyze_jd(client: LLMClient, jd_text: str) -> JDAnalysis:
    return client.structured(SYS, f"JD:\n{jd_text}", JDAnalysis, temperature=0.0)
