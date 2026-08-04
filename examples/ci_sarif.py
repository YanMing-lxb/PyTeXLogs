"""PyTeXLogs 场景 2：CI 质量门禁。
把解析结果导出 SARIF，可直接配合 `github/codeql-action/upload-sarif` 上传告警。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import pytexlogs


def main() -> int:
    report = pytexlogs.run_pipeline(
        "main",
        str(ROOT / "tests" / "fixtures"),
        captured_outputs={
            "pdflatex": (
                "This is pdfTeX, Version 3.14159265-2.6-1.40.25\n"
                "(./main.tex\n"
                "LaTeX Warning: Reference `missing' on page 1 undefined on input line 3.\n"
                "! Undefined control sequence.\n"
                "l.5 \\badcmd\n"
            )
        },
        print_terminal=False,
        pytexmk_version="ci-demo",
    )
    sarif = pytexlogs.to_sarif(report)
    assert sarif["$schema"].endswith("sarif-schema-2.1.0.json"), "SARIF 2.1.0 schema"
    assert sarif["version"] == "2.1.0"
    assert sarif["runs"][0]["tool"]["driver"]["name"] == "pytexlogs"
    out = ROOT / "examples" / "output_ci.sarif"
    out.write_text(json.dumps(sarif, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ci_sarif] SARIF 写盘: {out}")
    print(f"[ci_sarif] results 条数: {len(sarif['runs'][0]['results'])}")
    print("PASS: examples/ci_sarif.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
