"""编排：工位 0→3 串起来，组装定制简历文本 + 追溯/审核/压力测试报告。

一次性生成器（非对话）。对话式流程（提问式挖掘 + 主线确认）见 agent.py。
"""
from config import load_llm_config
from llm import LLMClient
from intake import load_profile, load_jd_file
from fact_locker import extract_facts
from jd_analyzer import analyze_jd
from module_selector import ArchetypePreset, select_modules
from tailor import tailor_experience, tailor_experience_fix
from verifier import verify
from stress_test import stress_test


def run(profile_path: str, archetype: str = "ai_builder", jd_file: str | None = None,
        do_stress_test: bool = True):
    cfg = load_llm_config()
    client = LLMClient(cfg)

    exps, jd, bg_type = load_profile(profile_path)
    if jd_file:
        jd = load_jd_file(jd_file)
    preset = ArchetypePreset.load(archetype)

    # 工位 0+2：采集即隔离——每条经历抽原子事实并锁定到自己 id
    for e in exps:
        extract_facts(client, e)

    # 工位 1：JD 分析
    jda = analyze_jd(client, jd)

    # 工位 3a：模块选择
    modules = select_modules(client, preset, jda, bg_type)

    # 工位 3b+3c+3d：逐条 scope-bound 改写 + 审核 + 压力测试；违规自动修一次再审核
    tailored = []  # (exp, rewrite, verdict, stress_verdict)
    for e in exps:
        rw = tailor_experience(client, e, jda)
        tries = 0
        while not rw.bullets and tries < 2:  # 偶发空输出，最多再试 2 次
            tries += 1
            rw = tailor_experience(client, e, jda)
        v = verify(client, e, exps, rw)
        if not v.clean:
            fixed = tailor_experience_fix(client, e, jda, rw, v.violations)
            if fixed.bullets:
                rw = fixed
                v = verify(client, e, exps, rw)
        st = None
        if do_stress_test and rw.bullets:
            try:
                st = stress_test(client, e, rw, jda)
            except Exception:  # GLM 偶发内容安全/坏 JSON，不让它炸掉整条管线
                st = None
        tailored.append((e, rw, v, st))

    return _assemble_resume(modules, tailored), _assemble_report(modules, tailored)


def _assemble_resume(modules, tailored) -> str:
    lines = [modules.positioning or "(待生成定位)", ""]
    for exp, rw, v, st in tailored:
        flag = "   ⚠[审核有疑义，见报告]" if not v.clean else ""
        head = exp.role + (f" @ {exp.org}" if exp.org else "") + (f"  ({exp.dates})" if exp.dates else "") + flag
        lines.append(head)
        for b in rw.bullets:
            lines.append(f"  • {b.text}")
        lines.append("")
    return "\n".join(lines).strip()


def _assemble_report(modules, tailored) -> str:
    total_violations = sum(1 for _, _, v, _ in tailored if not v.clean)
    weak_claims = sum(1 for _, _, _, st in tailored if st for r in st.results if not r.holds)
    empty_bullets = sum(1 for _, rw, _, _ in tailored if not rw.bullets)
    lines = [
        "【模块选择】",
        "  " + (" > ".join(modules.modules) if modules.modules else "(空)"),
    ]
    lines += ["  理由: " + modules.rationale, ""] if modules.rationale else [""]
    lines.append(f"【审核】有违规（腾挪/编造）的经历数: {total_violations} / {len(tailored)}")
    lines.append(f"【压力测试】defend 不住的 claim 数: {weak_claims}（面试可能被问倒，建议改写）")
    lines.append(f"【产出】空 bullet 的经历数: {empty_bullets} / {len(tailored)}（应为 0）")
    lines += ["", "【追溯 + 压力测试】每条 bullet 的来源事实 + 面试官追问:", ""]
    for exp, rw, v, st in tailored:
        lines.append(f"  [{exp.id}] {exp.role}")
        for b in rw.bullets:
            lines.append(f"    • {b.text}")
            sf = "; ".join(b.source_facts) if b.source_facts else "(未标注来源)"
            lines.append(f"        <- {sf}")
        if not v.clean:
            for viol in v.violations:
                lines.append(f"    ⚠ 腾挪/编造: {viol}")
        if st and st.results:
            for r in st.results:
                mark = "✗" if not r.holds else "·"
                lines.append(f"    {mark} 追问: {r.hardest_question}")
                if not r.holds:
                    lines.append(f"        薄弱: {r.weakness} → {r.suggestion}")
        lines.append("")
    return "\n".join(lines).strip()
