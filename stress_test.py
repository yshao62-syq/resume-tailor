"""工位 3d · 面试官视角 stress-test（debate 求逻辑严密）。

和 verifier 分工：
  - verifier 管"事实真不真"（跨项目腾挪 / 凭空编造）；
  - stress-test 管"逻辑严不严"——扮面试官对每条 bullet 抛最难追问，
    判断在现有锁定事实下能否 defend，指出逻辑薄弱点
    （自相矛盾 / 证据不足 / 过度拔高 / 因果跳跃）。
目标是把每条 claim 辩到自洽，把"面试会问倒的点"提前暴露，而不是找茬。
"""
from llm import LLMClient
from models import Experience, RewriteResult, JDAnalysis, StressTestVerdict

SYS = (
    "你是压力面试官，对简历做 stress-test，目标是逻辑严密自洽（不是找茬）。\n"
    "对每条 bullet：\n"
    "1. 抛出面试官会问的最难追问（针对该 claim 的逻辑 / 数据 / 因果 / 边界）。\n"
    "2. 严格判断：结合这条经历锁定的真实事实，这个 claim 能否扛住追问（holds=true 表示能 defend）。\n"
    "3. 若扛不住，指出 weakness（自相矛盾 / 证据不足 / 过度拔高 / 因果跳跃），给 suggestion 怎么改更严密。\n"
    "判 holds 要严：claim 里有任何在给定事实下解释不清、或过度引申的地方，就 holds=false。"
)


def stress_test(
    client: LLMClient, exp: Experience, rewrite: RewriteResult, jd: JDAnalysis
) -> StressTestVerdict:
    facts_block = "\n".join(f"- {f.fact}" for f in exp.facts) or "(无)"
    bullets_block = "\n".join(f"- {b.text}" for b in rewrite.bullets) or "(无)"
    user = (
        f"经历: {exp.role} @ {exp.org} ({exp.dates})\n\n"
        "【这条经历锁定的真实事实（defend 时只能引用这些）】:\n"
        f"{facts_block}\n\n"
        "【JD 必须 skill / 关键词（面试官关心的）】:\n"
        f"{jd.required_skills + jd.required_keywords}\n\n"
        "【要 stress-test 的 bullet】:\n"
        f"{bullets_block}\n\n"
        f"逐条 debate，返回 verdict。experience_id={exp.id}"
    )
    return client.structured(SYS, user, StressTestVerdict, temperature=0.2)
