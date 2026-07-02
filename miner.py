"""工位 0b · 提问式挖掘（从 JD 视角补材料）。

候选人不会主动讲全信息。从 JD 必须 skill / 关键词 视角看现有材料，
找出"写强 bullet 需要但材料里没讲"的点，生成针对性追问，挖出真实做过的事 + 数字。
挖到的回答在 agent.py 里作为新事实喂回 fact-locker（采集即隔离）。

这是"理解全局"的第一步：材料不足时主动追问，而不是凭空编。
"""
from llm import LLMClient
from models import Experience, JDAnalysis, MiningResult

SYS = (
    "你是简历信息挖掘器，从面试官 / JD 视角看候选人现有材料。\n"
    "任务：找出'写强简历 bullet 需要但材料里没讲'的信息，生成针对性追问帮候选人补全。\n"
    "规则：\n"
    "1. 每道题针对一个 JD 必须 skill / 关键词，且这个点在现有材料里确实缺失或太弱。\n"
    "2. 问题要具体、可答（不要'你有什么优势'这种空问题），引导候选人讲出真实做过的事 + 量化结果。\n"
    "3. 不要问材料里已经讲清楚的。\n"
    "4. 控制 3-6 道，按'对命中 JD 最关键'排序。\n"
    "每道题写清 target_skill（JD 要什么）、question（问什么）、why（为什么问）。"
)


def generate_questions(
    client: LLMClient, jd: JDAnalysis, exps: list[Experience]
) -> MiningResult:
    facts_block = "\n".join(
        f"[{e.id}] {e.role} @ {e.org}: " + "；".join(f.fact for f in e.facts)
        for e in exps
    ) or "(还没有任何材料)"
    skills = jd.required_skills + jd.required_keywords
    user = (
        "【JD 必须 skill / 关键词】:\n"
        f"{skills}\n\n"
        "【候选人现有材料（已抽出的原子事实）】:\n"
        f"{facts_block}\n\n"
        "找出 JD 要、但材料缺或弱的点，生成追问。"
    )
    return client.structured(SYS, user, MiningResult, temperature=0.2)
