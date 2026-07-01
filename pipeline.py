"""编排：工位 0→3 串起来，组装定制简历文本 + 追溯/审核报告。"""
from config import load_llm_config
from llm import LLMClient
from intake import load_profile, load_jd_file
from fact_locker import extract_facts
from jd_analyzer import analyze_jd
from module_selector import ArchetypePreset, select_modules
from tailor import tailor_experience, tailor_experience_fix
from verifier import verify


def run(profile_path: str, archetype: str = "ai_builder", jd_file: str | None = None):
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

    # 工位 3b+3c：逐条 scope-bound 改写 + 审核；违规就自动修一次再审核
    tailored = []  # (exp, rewrite, verdict)
    for e in exps:
        rw = tailor_experience(client, e, jda)
        tries = 0
        while not rw.bullets and tries < 2:  # 偶发空输出，最多再试 2 次（共 3 次）
            tries += 1
            rw = tailor_experience(client, e, jda)
        v = verify(client, e, exps, rw)
        if not v.clean:
            fixed = tailor_experience_fix(client, e, jda, rw, v.violations)
            if fixed.bullets:  # 修复版非空才采用；空就保留原版（有内容，报告里标违规）
                rw = fixed
                v = verify(client, e, exps, rw)
        tailored.append((e, rw, v))

    resume_text = _assemble_resume(modules, tailored)
    report = _assemble_report(modules, tailored)
    return resume_text, report


def _assemble_resume(modules, tailored) -> str:
    lines = [modules.positioning or "(待生成定位)", ""]
    for exp, rw, v in tailored:
        flag = "   ⚠[审核有疑义，见报告]" if not v.clean else ""
        head = exp.role + (f" @ {exp.org}" if exp.org else "") + (f"  ({exp.dates})" if exp.dates else "") + flag
        lines.append(head)
        for b in rw.bullets:
            lines.append(f"  • {b.text}")
        lines.append("")
    return "\n".join(lines).strip()


def _assemble_report(modules, tailored) -> str:
    total_violations = sum(1 for _, _, v in tailored if not v.clean)
    empty_bullets = sum(1 for _, rw, _ in tailored if not rw.bullets)
    lines = [
        "【模块选择】",
        "  " + (" > ".join(modules.modules) if modules.modules else "(空)"),
    ]
    if modules.rationale:
        lines += ["  理由: " + modules.rationale, ""]
    else:
        lines.append("")
    lines.append(f"【审核】有违规（腾挪/编造）的经历数: {total_violations} / {len(tailored)}")
    lines.append(f"【产出】空 bullet 的经历数: {empty_bullets} / {len(tailored)}（应为 0；>0 说明该段没产出内容）")
    lines.append("")
    lines.append("【追溯】每条 bullet 的来源事实（检查是否每条都挂得上真实经历）:")
    lines.append("")
    for exp, rw, v in tailored:
        lines.append(f"  [{exp.id}] {exp.role}")
        for b in rw.bullets:
            lines.append(f"    • {b.text}")
            sf = "; ".join(b.source_facts) if b.source_facts else "(未标注来源)"
            lines.append(f"        <- {sf}")
        if not v.clean:
            for viol in v.violations:
                lines.append(f"    ⚠ {viol}")
        lines.append("")
    return "\n".join(lines).strip()
