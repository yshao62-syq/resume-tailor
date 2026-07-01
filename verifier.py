"""工位 3c · scope 审核员（verifier）。技术心脏之二。

逐条经历复查改写结果，专门抓两种违规：
  - 跨项目腾挪：bullet 里的某个 claim 其实来自"另一条经历"的事实；
  - 凭空编造：bullet 里有 claim 在本条经历的事实里完全找不到依据。

做法：给审核员看本条经历的事实 + 改写出的 bullet + 其他经历的事实清单，
让它判断每条 bullet 是否越界。这是对"杜绝幻觉/腾挪"的硬约束，
不靠 prompt 祈求，而是独立的一道校验。
"""
from llm import LLMClient
from models import Experience, RewriteResult, VerifierVerdict

SYS = (
    "你是 scope 审核员，专抓简历改写里的越界问题。\n"
    "给你：本条经历锁定的原子事实、改写出的 bullet、以及'其他经历'的事实清单。\n"
    "逐条检查每个 bullet 的每一个 claim：\n"
    "1. 如果某 claim 能在'其他经历'的事实里找到对应、却不在本条事实里 -> 跨项目腾挪，记违规。\n"
    "2. 如果某 claim 在本条事实里找不到任何依据、也不在其他经历里 -> 凭空编造，记违规。\n"
    "3. 细节润色、合理措辞、用强动词改写 -> 不算违规。\n"
    "返回 clean（true=全部干净）和 violations（每条违规说清楚是哪个 bullet、哪个 claim、错在哪）。"
)


def verify(
    client: LLMClient, exp: Experience, all_exps: list[Experience], rewrite: RewriteResult
) -> VerifierVerdict:
    own = "\n".join(f"- {f.fact}" for f in exp.facts) or "(无)"
    others = []
    for o in all_exps:
        if o.id == exp.id:
            continue
        for f in o.facts:
            others.append(f"[{o.id}] {f.fact}")
    others_block = "\n".join(others) or "(无其他经历)"

    bullets_block = "\n".join(f"- {b.text}" for b in rewrite.bullets) or "(无)"

    user = (
        f"经历ID: {exp.id}\n\n"
        "【本条经历锁定的原子事实】:\n"
        f"{own}\n\n"
        "【改写出的 bullet】:\n"
        f"{bullets_block}\n\n"
        "【其他经历的事实清单（用于识别腾挪）】:\n"
        f"{others_block}\n\n"
        f"逐条检查，返回 verdict。experience_id={exp.id}"
    )
    return client.structured(SYS, user, VerifierVerdict, temperature=0.0)
