"""Shell 补全脚本生成器。

选项清单从 argparse 解析器自动提取，避免 CLI 新增参数后补全脚本漂移。
"""

from __future__ import annotations

import argparse

__all__ = ["render_completion", "option_strings"]


def option_strings(parser: argparse.ArgumentParser) -> list[str]:
    """提取解析器支持的全部选项字符串（短选项 + 长选项），保持声明顺序。"""
    result: list[str] = []
    for action in parser._actions:  # noqa: SLF001 - argparse 没有公开的 actions 接口
        for opt in action.option_strings:
            if opt not in result:
                result.append(opt)
    return result


def render_completion(shell: str, parser: argparse.ArgumentParser, prog: str = "pytexlogs") -> str:
    """生成指定 shell 的补全脚本；只补选项名，不猜文件/项目名。"""
    options = " ".join(option_strings(parser))
    func = f"_{prog}"

    if shell == "bash":
        return f"""# {prog} bash completion
{func}() {{
    local cur prev
    COMPREPLY=()
    cur="${{COMP_WORDS[COMP_CWORD]}}"
    prev="${{COMP_WORDS[COMP_CWORD-1]}}"
    if [[ "$cur" == -* ]]; then
        COMPREPLY=( $(compgen -W "{options}" -- "$cur") )
    fi
}}
complete -o default -F {func} {prog}
"""

    if shell == "zsh":
        return f"""#compdef {prog}
# {prog} zsh completion
{func}() {{
    local -a opts
    opts=({options})
    compadd -- $opts
}}
compdef {func} {prog}
"""

    if shell == "fish":
        lines = [
            f"# {prog} fish completion",
            *(f"complete -c {prog} -l {opt[2:]}" for opt in option_strings(parser) if opt.startswith("--")),
        ]
        return "\n".join(lines) + "\n"

    if shell == "powershell":
        quoted = ",".join(f"'{opt}'" for opt in option_strings(parser))
        return f"""# {prog} powershell completion
Register-ArgumentCompleter -Native -CommandName '{prog}' -ScriptBlock {{
    param($wordToComplete, $commandAst, $cursorPosition)
    $options = @({quoted})
    $options | Where-Object {{ $_ -like "$wordToComplete*" }} | ForEach-Object {{
        [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
    }}
}}
"""

    raise ValueError(f"unsupported shell: {shell}")
