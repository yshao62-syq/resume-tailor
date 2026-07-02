"""对话式 agent：理解全局 → 再隔离动笔。

比 pipeline.run()（一次性生成器）多了两个交互环节：
  - 提问式挖掘（miner）：材料不足时，按 JD 追问补全事实
  - narrative synthesis：推断职业主线，给候选人确认 + JD 取舍（heavy/light/drop）

流程：
  intake → 抽事实 → JD 分析
  → [提问式挖掘 Q&A] → narrative synthesis（确认主线 + 取舍）
  → 模块选择（用确认的定位）→ 按 heavy/light/drop 改写 + 审核
  → 压力测试 → 组装简历 + 报告

交互用 input()；--auto 跳过追问、自动采纳推断主线（便于测试 / CI）。
"""
import argparse

from config import load_llm_config
from llm import LLMClient
from intake import load_profile, load_jd_file
from fact_locker import extract_facts
from jd_analyzer import analyze_jd
from miner import generate_questions
from narrative import synthesize
from module_selector import ArchetypePreset, select_modules
from tailor import tailor_experience, tailor_experience_fix
from verifier import verify
from stress_test import stress_test
from models import Experience


def _ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        return ""


def _ingest_answer(client: LLMClient, exps: list[Experience], target_skill: str, answer: str) -> None:
    """把挖掘到的回答作为新经历抽事实、加入容器（采集即隔离）。"""
    new = Experience(
        id=f"mined{len(exps)}",
        type="practice",
        role=f"挖掘补全·{target_skill}",
        org="",
        dates="",
        original_text=answer,
    )
    extract_facts(client, new)
    exps.append(new)


def run(profile_path: str, archetype: str = "ai_builder", jd_file: str | None = None,
        interactive: bool = True):
    cfg = load_llm_config()
    client = LLMClient(cfg)
    exps, jd, bg_type = load_profile(profile_path)
    if jd_file:
        jd = load_jd_file(jd_file)
    preset = ArchetypePreset.load(archetype)

    for e in exps:
        extract_facts(client, e)
    jda = analyze_jd(client, jd)

    # ---- 理解全局 ①：提问式挖掘 ----
    if interactive:
        mining = generate_questions(client, jda, exps)
        if mining.questions:
            print("\n=== 提问式挖掘（从 JD 视角补材料，回车可跳过）===")
            for i, q in enumerate(mining.questions, 1):
                print(f"\n[{i}] (补 JD: {q.target_skill}) {q.question}")
                if q.why:
                    print(f"    why: {q.why}")
                ans = _ask("    你的回答: ")
                if ans:
                    _ingest_answer(client, exps, q.target_skill, ans)

    # ---- 理解全局 ②：narrative synthesis（推断主线 + 确认）----
    narr = synthesize(client, exps, jda, bg_type)
    print("\n=== 职业主线（推断，请确认）===")
    print("主线:", narr.mainline)
    if narr.positioning:
        print("定位:", narr.positioning)
    for d in narr.decisions:
        print(f"  [{d.experience_id}] {d.emphasis} — {d.reason}")
    if interactive:
        override = _ask("\n回车=采纳这条主线；或输入你想改的定位: ")
        if override:
            narr.positioning = override
    emphasis = {d.experience_id: d.emphasis for d in narr.decisions}

    # ---- 再隔离动笔：模块选择 + 按 emphasis 改写 ----
    modules = select_modules(client, preset, jda, bg_type)
    if narr.positioning:
        modules.positioning = narr.positioning

    tailored = []  # (exp, rewrite, verdict, stress_verdict, emphasis)
    for e in exps:
        emp = emphasis.get(e.id, "heavy")
        if emp == "drop":
            continue
        max_b = 1 if emp == "light" else None
        rw = tailor_experience(client, e, jda, max_bullets=max_b)
        tries = 0
        while not rw.bullets and tries < 2:
            tries += 1
            rw = tailor_experience(client, e, jda, max_bullets=max_b)
        if emp == "light":
            # max_bullets=1 偶发空输出；兜底用无约束改写再截到 1 条
            if not rw.bullets:
                rw = tailor_experience(client, e, jda)
            rw.bullets = rw.bullets[:1]
        v = verify(client, e, exps, rw)
        if not v.clean:
            fixed = tailor_experience_fix(client, e, jda, rw, v.violations)
            if fixed.bullets:
                rw = fixed
                v = verify(client, e, exps, rw)
        st = None
        if rw.bullets:
            try:
                st = stress_test(client, e, rw, jda)
            except Exception as ex:
                print(f"  (stress-test 跳过 {e.id}: {ex})")
        tailored.append((e, rw, v, st, emp))

    return _assemble_resume(modules, tailored), _assemble_report(modules, tailored), narr


def _assemble_resume(modules, tailored) -> str:
    lines = [modules.positioning or "(待生成定位)", ""]
    for exp, rw, v, st, emp in tailored:
        tag = "（轻）" if emp == "light" else ""
        flag = "   ⚠[审核有疑义，见报告]" if not v.clean else ""
        head = exp.role + (f" @ {exp.org}" if exp.org else "") + (f"  ({exp.dates})" if exp.dates else "") + tag + flag
        lines.append(head)
        for b in rw.bullets:
            lines.append(f"  • {b.text}")
        lines.append("")
    return "\n".join(lines).strip()


def _assemble_report(modules, tailored) -> str:
    total_violations = sum(1 for _, _, v, _, _ in tailored if not v.clean)
    weak = sum(1 for _, _, _, st, _ in tailored if st for r in st.results if not r.holds)
    lines = [
        "【模块选择】 " + (" > ".join(modules.modules) if modules.modules else "(空)"),
        f"【审核】腾挪/编造经历数: {total_violations} / {len(tailored)}",
        f"【压力测试】defend 不住的 claim 数: {weak}（面试可能被问倒）",
        "",
        "【追溯 + 压力测试】",
        "",
    ]
    for exp, rw, v, st, emp in tailored:
        lines.append(f"  [{exp.id}] {exp.role} ({emp})")
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


def main():
    ap = argparse.ArgumentParser(description="对话式简历 agent（理解全局→再隔离动笔）")
    ap.add_argument("profile", help="简历档案 yaml")
    ap.add_argument("--jd", default=None, help="JD 文本文件，覆盖 profile 里的 jd")
    ap.add_argument("--archetype", default="ai_builder")
    ap.add_argument("--auto", action="store_true", help="非交互：跳过追问、自动采纳主线（测试用）")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    resume, report, _ = run(
        args.profile, archetype=args.archetype, jd_file=args.jd, interactive=not args.auto
    )
    print("\n" + "=" * 60 + "\n定制简历\n" + "=" * 60 + "\n")
    print(resume)
    print("\n" + "=" * 60 + "\n报告\n" + "=" * 60 + "\n")
    print(report)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(resume + "\n\n" + "=" * 28 + " 报告 " + "=" * 27 + "\n\n" + report)
        print(f"\n已写入 {args.out}")


if __name__ == "__main__":
    main()
