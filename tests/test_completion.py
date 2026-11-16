"""CLI shell 补全回归测试。"""

import pytest

from pytexlogs.cli.args import build_parser
from pytexlogs.cli.completion import render_completion
from pytexlogs.cli.main import main


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish", "powershell"])
def test_completion_contains_new_options(shell: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--completion", shell]) == 0
    out = capsys.readouterr().out
    # fish 的语法是 ``-l jobname``，其他 shell 保留 ``--jobname``。
    assert ("-l jobname" in out) if shell == "fish" else ("--jobname" in out)
    assert ("-l baseline" in out) if shell == "fish" else ("--baseline" in out)
    assert ("-l severity" in out) if shell == "fish" else ("--severity" in out)
    assert "PyTeXLogs Summary" not in out


def test_bash_completion_registers_function(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--completion", "bash"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("# pytexlogs bash completion")
    assert "complete -o default -F _pytexlogs pytexlogs" in out


def test_completion_extracts_from_parser() -> None:
    parser = build_parser()
    text = render_completion("fish", parser)
    assert "complete -c pytexlogs -l jobname" in text
