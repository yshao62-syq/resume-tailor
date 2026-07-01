"""CLI 入口：python main.py <profile.yaml> [--jd jd.txt] [--archetype ai_builder] [--out out.txt]"""
import argparse

from pipeline import run


def main():
    ap = argparse.ArgumentParser(description="简历定制 agent（Phase 0：文本输出）")
    ap.add_argument("profile", help="简历档案 yaml（含 experiences + jd）")
    ap.add_argument("--jd", help="JD 文本文件，覆盖 profile 里的 jd", default=None)
    ap.add_argument("--archetype", default="ai_builder", help="archetype preset 名")
    ap.add_argument("--out", default=None, help="同时写入该文件")
    args = ap.parse_args()

    resume, report = run(args.profile, archetype=args.archetype, jd_file=args.jd)

    print("\n" + "=" * 60 + "\n定制简历\n" + "=" * 60 + "\n")
    print(resume)
    print("\n" + "=" * 60 + "\n追溯与审核报告\n" + "=" * 60 + "\n")
    print(report)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(resume + "\n\n" + "=" * 28 + " 报告 " + "=" * 27 + "\n\n" + report)
        print(f"\n已写入 {args.out}")


if __name__ == "__main__":
    main()
