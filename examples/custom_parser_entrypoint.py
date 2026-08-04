"""PyTeXLogs 场景 5：自定义 parser 通过 Entry Point 机制扩展。
演示用户自己的包（my_latex_tools）如何声明 entry point：

    # 别人项目的 pyproject.toml:
    [project.entry-points."pytexlogs.parsers"]
    mychktex = "my_latex_tools.chktex:MyChktexParser"

这里在当前进程直接手动注册一个 MyChktexParser 到 LogParserRegistry，效果等价于 entry_points。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import pytexlogs
from pytexlogs import BaseLogParser, LogEntry, LogLevel, ParsedLog


class MyChktexParser(BaseLogParser):  # 测试用：模拟 entry point 加载的类
    category = "lint"
    importance = "medium"

    def parse(self, log_text: str, root_file: str | None = None) -> ParsedLog:
        entries: list[LogEntry] = []
        for line_no, line in enumerate(log_text.splitlines(), 1):
            if "Cmd terminated with space" in line:
                entries.append(LogEntry(LogLevel.WARNING, root_file or "main.tex", line_no, line.strip()))
        return ParsedLog(entries=entries, raw_text=log_text, category=self.category, importance=self.importance)  # type: ignore[call-arg]


def main() -> int:
    registry = pytexlogs.LogParserRegistry()
    registry.register("mychktex", MyChktexParser)
    spec = registry.lookup("mychktex")
    assert spec is not None, "手动 register 应能 lookup 成功"
    mgr = pytexlogs.LogParserManager(registry)
    results = mgr.run(
        jobname="demo",
        auxdir=".",
        steps=["mychktex"],
        captured_outputs={"mychktex": "Warning 1 in main.tex:23:Cmd terminated with space.\n"},
    )
    assert len(results) == 1
    assert results[0].tool_name == "mychktex"
    assert len(results[0].warnings) >= 1
    print("[custom_parser_entrypoint] mychktex custom parser works. warnings =", len(results[0].warnings))
    print("PASS: examples/custom_parser_entrypoint.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
