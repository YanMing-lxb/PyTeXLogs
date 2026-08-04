"""PyTeXLogs 场景 4：工具链二次开发（latexmk / tectonic / arara 封装脚本嵌入）。
使用 parse_auxdir 一行拿到所有结果 + aggregate_stats 生成直方图数据源。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import pytexlogs


def main() -> int:
    results = pytexlogs.parse_auxdir(
        jobname="sample",
        auxdir=str(ROOT / "tests" / "fixtures"),
        steps=["pdflatex"],
        captured_outputs={
            "pdflatex": (
                "This is pdfTeX\n"
                "! Undefined control sequence.\n"
                "l.5 \\badcmd\n"
                "LaTeX Warning: Reference `missing' on page 1 undefined on input line 3.\n"
            )
        },
    )
    assert len(results) >= 1, "至少应该得到 1 条 pdflatex ToolResult"
    by_parser = pytexlogs.aggregate_stats(results, group_by="parser")
    by_level = pytexlogs.aggregate_stats(results, group_by="level")
    by_cat = pytexlogs.aggregate_stats(results, group_by="category")
    print("[toolchain_integration] by_parser:", by_parser)
    print("[toolchain_integration] by_level :", by_level)
    print("[toolchain_integration] by_cat   :", by_cat)
    assert "pdflatex" in by_parser, "应包含 pdflatex 统计"
    assert by_level.get("error", 0) >= 1, "至少 1 条 ERROR"
    print("PASS: examples/toolchain_integration.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
