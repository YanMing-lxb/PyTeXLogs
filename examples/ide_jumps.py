"""PyTeXLogs 场景 1：IDE / 编辑器集成。
把 .log 或整个 auxdir 解析成 file:line:message 三元组，直接送 VS Code Problems / Neovim quickfix。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import pytexlogs


def main() -> int:
    sample_log = ROOT / "tests" / "fixtures" / "sample.log"
    parsed = pytexlogs.parse_log_file(sample_log)
    jumps = pytexlogs.format_editor_jumps(parsed.entries)
    assert isinstance(jumps, list), "format_editor_jumps 应返回 list"
    assert len(jumps) >= 1, "sample.log 至少应产出 1 条跳转条目"
    first = jumps[0]
    assert isinstance(first, str), "条目应是字符串 file:line: message"
    assert ":" in first, "格式 file:line: message 需要含冒号分隔符"
    print(f"[ide_jumps] 共产出 {len(jumps)} 条编辑器跳转")
    print(f"[ide_jumps] 第 1 条: {first!r}")
    print("PASS: examples/ide_jumps.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
