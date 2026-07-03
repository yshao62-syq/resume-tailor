"""工位 3b · scope-bound（边界受控）改写。技术心脏之一。

铁律：改写一条经历时，只能引用这条经历自己锁定的原子事实。
可以重新组织语言、往命中 JD 关键词的角度靠，但每个 claim 必须能被给定事实支持。
允许细节级润色（量化、强动词），但不许凭空新增事实，更不许把别条经历的事实挪过来。
每条 bullet 必须标注它基于哪些原子事实（source_facts），供追溯和审核。
"""
from llm import LLMClient
from models import Experience, JDAnalysis, RewriteResult

SYS = (
    "你是简历改写器，做 scope-bound（边界受控）改写。\n"
    "规则：\n"
    "1. 只能用下面给你的'这条经历锁定的原子事实'来改写，绝对不能引入任何不在列表里的事实。\n"
    "2. 可以重新组织语言、往命中 JD 关键词的角度改写，但每个 claim 必须能被给定事实支持。\n"
    "3. 允许细节级润色（补充合理措辞、强动词），但不许凭空新增经历里没有的事实。\n"
    "4. 严禁把别条经历的事实挪到这条来（跨项目腾挪）。\n"
    "5. 每条 bullet 必须在 source_facts 里列出它依据的原子事实（引用事实原文片段）。\n"
    "6. 输出 2-4 条精炼的简历 bullet。\n"
    "7. 每条 bullet 用'引导词：展开'格式——前面几个字的主题词 + 冒号 + 具体内容，如'异步工具协议：设计外呼的两阶段协议……'。"
)


def tailor_experience(
    client: LLMClient, exp: Experience, jd: JDAnalysis, max_bullets: int | None = None
) -> RewriteResult:
    facts_block = "\n".join(f"- {f.fact}" for f in exp.facts) or "(无)"
    keywords = jd.required_skills + jd.required_keywords
    extra = f"\n本次只输出 {max_bullets} 条精炼 bullet（一句带过）。" if max_bullets else ""
    user = (
        f"经历: {exp.role} @ {exp.org} ({exp.dates})\n\n"
        "【这条经历锁定的原子事实，你只能用这些，不许用别的】:\n"
        f"{facts_block}\n\n"
        f"JD 命中关键词（往这些角度靠）: {keywords}\n\n"
        f"把它改写成简历 bullet。experience_id={exp.id}{extra}"
    )
    return client.structured(SYS, user, RewriteResult, temperature=0.3)


def tailor_experience_fix(
    client: LLMClient, exp: Experience, jd: JDAnalysis, prev: RewriteResult, violations: list[str]
) -> RewriteResult:
    """审核发现违规后，把违规反馈给改写器重写一版（自动修复闭环用）。"""
    facts_block = "\n".join(f"- {f.fact}" for f in exp.facts) or "(无)"
    prev_block = "\n".join(f"- {b.text}" for b in prev.bullets) or "(无)"
    viol_block = "\n".join(f"- {x}" for x in violations) or "(无)"
    user = (
        f"经历: {exp.role} @ {exp.org} ({exp.dates})\n\n"
        "【这条经历锁定的原子事实，你只能用这些】:\n"
        f"{facts_block}\n\n"
        "【上一版改写的 bullet，审核发现以下违规，必须全部修正】:\n"
        f"{viol_block}\n\n"
        "上一版 bullet（供参考，不要原样保留问题部分）:\n"
        f"{prev_block}\n\n"
        "请严格基于锁定事实重新改写，杜绝上述违规。experience_id="
        f"{exp.id}"
    )
    return client.structured(SYS, user, RewriteResult, temperature=0.1)
