"""PyTeXLogs 场景 6：批量教学报表。
扫一批 .log → 统一 CSV 汇总，方便 LaTeX 课程助教统计错误分布。
"""
import csv
import io
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import pytexlogs


def main() -> int:
    samples = {
        "alice.log": (
            "This is pdfTeX\n"
            "LaTeX Warning: Citation `x' on page 1 undefined on input line 2.\n"
            "! Undefined control sequence.\n"
            "l.3 \\badcmdA\n"
        ),
        "bob.log": (
            "This is pdfTeX\n"
            "LaTeX Warning: Overfull \\\\hbox (10pt too wide) in paragraph at lines 10--15\n"
        ),
        "charlie.log": (
            "This is pdfTeX\n"
            "! LaTeX Error: File `missingpackage.sty' not found.\n"
            "l.7 \\usepackage{missingpackage}\n"
        ),
    }
    all_tool_results = []
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        for name, content in samples.items():
            (td_path / name).write_text(content, encoding="utf-8")
            parsed = pytexlogs.parse_log_file(td_path / name)
            from pytexlogs.manager import ToolResult, ToolResultStats
            tr = ToolResult(
                tool_name=name,
                category="compile",
                importance="high" if parsed.errors else "medium",
                source_path=str(td_path / name),
                raw_text=parsed.raw_text,
                entries=parsed.entries,
                stats=ToolResultStats(len(parsed.entries), {"error": len(parsed.errors), "warning": len(parsed.warnings)}),
            )
            all_tool_results.append(tr)
        csv_text = pytexlogs.to_csv(all_tool_results)
        header, *rows = list(csv.reader(io.StringIO(csv_text)))
        assert header == ["file","line","level","category","tool","text","hint","source_path"], f"表头错误：{header}"
        assert len(rows) >= 3, f"至少 3 条错误/警告条目，实际 {len(rows)}"
        out = ROOT / "examples" / "output_batch.csv"
        out.write_text(csv_text, encoding="utf-8")
        print(f"[batch_csv_export] CSV 写盘: {out} 条目数={len(rows)}")
    print("PASS: examples/batch_csv_export.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
