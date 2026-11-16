"""可执行建议（hint）：把日志条目翻译成“下一步该做什么”。

设计原则：
- 提示词表与解析器同源（LATEX/BIBTEX/BIBER 三张表），不另起一套口径；
- 匹配时对反斜杠做归一化——原表里的 ``Overfull \\\\hbox`` 在源码中实际是
  两个反斜杠，而真实日志是 ``Overfull \\hbox``，不归一化就永远匹配不上；
- 对“缺文件/缺宏包/缺字体”这类可自动修复的问题，额外给出安装命令
  （同时给 TeX Live 与 MiKTeX 两种写法，调用方按发行版挑一条即可）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "Hint",
    "collect_hints",
    "detect_missing_package",
    "hint_for_entry",
    "hint_for_text",
]


@dataclass(frozen=True, slots=True)
class Hint:
    """一条可执行建议：说明文字 + 可选安装命令。"""

    text: str
    commands: tuple[str, ...] = ()
    kind: str = "general"
    #: 英文说明；为空时调用方回退到 ``text``，避免每条规则都必须准备两种语言。
    text_en: str = ""


def collect_hints() -> dict[str, str]:
    """合并三张提示表（LaTeX / BibTeX / Biber），供 CLI 与 CSV 共用。"""
    from .parsers.biber import BIBER_WARNING_HINTS
    from .parsers.bibtex import BIBTEX_ERROR_HINTS
    from .parsers.latex import LATEX_LOG_HINTS

    merged: dict[str, str] = {}
    merged.update(LATEX_LOG_HINTS)
    merged.update(BIBTEX_ERROR_HINTS)
    merged.update(BIBER_WARNING_HINTS)
    return merged


def _normalize(text: str) -> str:
    """统一反斜杠数量与空白，避免源码转义差异导致匹配失败。"""
    return text.replace("\\\\", "\\").replace("\u00a0", " ")


_MISSING_FILE_RE = re.compile(r"File\s+`([^']+)'\s+not\s+found", re.IGNORECASE)
_PACKAGE_ERROR_RE = re.compile(r"(?:Package|Class)\s+(\S+)\s+Error:", re.IGNORECASE)
_FONT_NOT_FOUND_RE = re.compile(
    r"Font(?: shape)?\s+`?([^'`]+)'?\s+(?:not found|undefined)", re.IGNORECASE
)
_UNICODE_RE = re.compile(r"Unicode character\s+(\S+)\s+\(U\+([0-9A-Fa-f]+)\)", re.IGNORECASE)
_UNDEFINED_CITATION_RE = re.compile(r"Citation\s+`([^']+)'\s+.*?undefined", re.IGNORECASE)
_UNDEFINED_REFERENCE_RE = re.compile(r"Reference\s+`([^']+)'\s+.*?undefined", re.IGNORECASE)
# LaTeX parser 会把这两类条目的展示文本翻译成“找不到 citation/reference `key`”；
# hint 必须同时认本地化后的文本，否则 CLI 摘要里只有条目、没有建议。
_UNDEFINED_CITATION_ZH_RE = re.compile(r"找不到\s+citation\s+`([^']+)`", re.IGNORECASE)
_UNDEFINED_REFERENCE_ZH_RE = re.compile(r"找不到\s+reference\s+`([^']+)`", re.IGNORECASE)
_UNDEFINED_ENV_RE = re.compile(r"Environment\s+(\S+)\s+undefined", re.IGNORECASE)
_BIB_DB_RE = re.compile(r"(?:I couldn't open database file|Cannot find file)\s+([^\s.]+)", re.IGNORECASE)
_MISSING_CHAR_RE = re.compile(r"Missing character:\s+There is no\s+(\S+)\s+in font", re.IGNORECASE)
_UNDEFINED_CONTROL_RE = re.compile(r"Undefined control sequence", re.IGNORECASE)
_CONTROL_NAME_RE = re.compile(r"\\([A-Za-z@]+)")
_END_MISMATCH_RE = re.compile(r"\\begin\{document\}\s+ended by\s+\\end\{(\w+)\}", re.IGNORECASE)

#: 只有这些后缀才代表“缺宏包/文档类”，其他 ``File ... not found`` 是缺图片/缺输入文件。
_PACKAGE_SUFFIXES = (".sty", ".cls", ".def", ".cfg", ".clo", ".ldf")
_GRAPHIC_SUFFIXES = (".png", ".jpg", ".jpeg", ".pdf", ".eps", ".ps", ".svg", ".bmp", ".tif", ".tiff")
_BIB_SUFFIXES = (".bib",)

#: 旧提示表（LATEX/BIBTEX/BIBER）的英文文案；键与中文表共用，供 --lang en 使用。
_LOG_HINT_EN = {
    "Undefined control sequence":
        "Check the command spelling, or confirm the package that provides it is loaded.",
    "Undefined reference":
        "The label is not recorded yet: rerun LaTeX once or twice (or check the \\label/\\ref name).",
    "Undefined citation":
        "Bibliography key not found: check that the .bib entry key matches \\cite{key} and that bibtex/biber ran.",
    "Overfull \\\\hbox":
        "A line/box exceeds the text width: add a manual break, use \\sloppy, or shrink the content.",
    "Underfull \\\\hbox":
        "A line/box is underfull: usually acceptable; add content or use \\linebreak if it looks bad.",
    "Missing character":
        "The current font lacks this glyph: switch to a font that contains it, or use \\usepackage[T1]{fontenc}.",
    "Rerun to get cross-references right":
        "Rerun LaTeX: page numbers/links in the .aux file need a second pass.",
    "Rerun to get citations correct":
        "Run bibtex/biber first, then rerun LaTeX once or twice to sync citations.",
    "I'm skipping whatever remains of this entry":
        "BibTeX entry syntax error: check for a missing comma, unbalanced braces, or a misspelled field name.",
    "I'm skipping whatever remains of this command":
        "@string/abbreviation definition error: check the @string{key = \"value\"} syntax.",
    "A bad cross reference":
        "A crossref points to a non-existent entry: check that crossref = {xxx} exists in the same .bib file.",
    "---while reading file":
        "Failed to read an auxiliary file: check that the .aux was generated (run pdflatex first) and that paths are correct.",
    "I didn't find a database entry":
        "Biber could not find the citation key: check the @xxx{key, entry in .bib and that it matches \\cite/\\autocite.",
    "entry `.+?' has":
        "Duplicate entry or conflicting fields: check for duplicate keys or repeated fields in .bib.",
    "WARN -":
        "Generic Biber warning: likely a data validation issue; check .bib fields against biblatex requirements.",
}


def _missing_file_name(text: str) -> str | None:
    """提取 ``File `xxx' not found`` 中的文件名（不做任何归因）。"""
    match = _MISSING_FILE_RE.search(text)
    return match.group(1) if match else None


def _package_stem(name: str) -> str | None:
    """把 ``siunitx.sty`` 转成 ``siunitx``；不是宏包后缀则返回 None。"""
    lowered = name.lower()
    for suffix in _PACKAGE_SUFFIXES:
        if lowered.endswith(suffix):
            return name[: -len(suffix)]
    return None


def detect_missing_package(text: str) -> str | None:
    """从「File `xxx.sty' not found」类日志里提取宏包名。

    只认宏包/文档类后缀（``.sty/.cls/.def/.cfg/.clo/.ldf``）。缺图片
    ``fig.png``、缺文献 ``refs.bib`` 不是宏包问题，返回 ``None``，避免给出
    错误的 ``tlmgr install fig.png``。

    Returns:
        宏包名（不含后缀）；无法判断时返回 ``None``。
    """
    name = _missing_file_name(text)
    if not name:
        # 单独的 ``Package X Error:`` 不能断言“缺宏包”——X 往往已经加载，
        # 真正的原因在错误正文里（字体缺失、选项冲突等）。这里只返回 None，
        # 由后面的规则按具体文本给出建议。
        return None
    stem = _package_stem(name)
    if stem is not None:
        # 日志里可能带相对/绝对路径（Windows 用反斜杠），安装命令只要包名。
        return re.split(r"[/\\]", stem)[-1]
    return None


def _install_commands(pkg: str) -> tuple[str, ...]:
    """给定宏包名，返回 TeX Live / MiKTeX 两条安装命令。"""
    return (f"tlmgr install {pkg}", f"miktex packages install {pkg}")


def _missing_file_hint(name: str) -> Hint | None:
    """对非宏包的 ``File ... not found`` 给出按类型区分的建议。"""
    lowered = name.lower()
    if any(lowered.endswith(suffix) for suffix in _GRAPHIC_SUFFIXES):
        return Hint(
            text=(
                f"找不到图片 `{name}`：确认路径相对主文件目录，"
                "或把图片目录写进 \\graphicspath{{...}}。"
            ),
            commands=(f"kpsewhich {name}", "\\graphicspath{{fig/}}"),
            kind="missing_graphic",
            text_en=(
                f"Image `{name}` not found: check the path relative to the main file, "
                "or add the directory to \\graphicspath{{...}}."
            ),
        )
    if any(lowered.endswith(suffix) for suffix in _BIB_SUFFIXES):
        return Hint(
            text=f"找不到文献数据库 `{name}`：确认 .bib 路径与文件名大小写。",
            commands=(f"kpsewhich {name}",),
            kind="missing_bib",
            text_en=f"Bibliography database `{name}` not found: check the .bib path and filename case.",
        )
    return Hint(
        text=(
            f"找不到文件 `{name}`：检查 \\input / \\include / \\includegraphics "
            "的路径（相对主文件目录），确认文件确实存在。"
        ),
        commands=(f"kpsewhich {name}",),
        kind="missing_file",
        text_en=(
            f"File `{name}` not found: check \\input / \\include / \\includegraphics "
            "paths relative to the main file."
        ),
    )


def _hint_for_text_raw(text: str) -> Hint | None:
    """内部实现：按一条日志文本给出建议（不做上下文替换）。"""
    if not text:
        return None
    normalized = _normalize(text)

    pkg = detect_missing_package(normalized)
    if pkg:
        return Hint(
            text=f"缺少宏包/文档类 `{pkg}`：请安装后重新编译（或改用已有宏包）。",
            commands=_install_commands(pkg),
            kind="missing_package",
            text_en=(
                f"Missing package/class `{pkg}`: install it, then rebuild "
                "(or switch to an existing package)."
            ),
        )

    missing_name = _missing_file_name(normalized)
    if missing_name:
        hint = _missing_file_hint(missing_name)
        if hint is not None:
            return hint

    font = _FONT_NOT_FOUND_RE.search(normalized)
    if font and "Missing character" not in normalized:
        family = font.group(1).strip()
        return Hint(
            text=f"字体/字形 `{family}` 不可用：检查字体是否安装，或改用 fontspec 可用的字族。",
            commands=(
                f"fc-list | grep -i '{family}'",
                "initexmf --update-fndb",
            ),
            kind="missing_font",
            text_en=(
                f"Font/glyph `{family}` is unavailable: check the font installation "
                "or switch to a fontspec-compatible family."
            ),
        )

    unicode_match = _UNICODE_RE.search(normalized)
    if unicode_match:
        char, codepoint = unicode_match.group(1), unicode_match.group(2)
        return Hint(
            text=(
                f"pdflatex 没有为 `{char}` (U+{codepoint}) 配置字形：改用 XeLaTeX/LuaLaTeX，"
                "或把它替换成 ASCII 的 LaTeX 命令（如 \\ensuremath{\\alpha}）。"
            ),
            commands=("xelatex <主文件>.tex", "lualatex <主文件>.tex"),
            kind="unicode",
            text_en=(
                f"pdflatex has no glyph set up for `{char}` (U+{codepoint}): "
                "switch to XeLaTeX/LuaLaTeX, or replace it with an ASCII LaTeX "
                "command (e.g. \\ensuremath{\\alpha})."
            ),
        )

    missing_char = _MISSING_CHAR_RE.search(normalized)
    if missing_char:
        char = missing_char.group(1)
        return Hint(
            text=(
                f"当前字体里没有字符 `{char}`：换用包含该字形的字体，"
                "或用 \\newunicodechar 显式映射。"
            ),
            commands=("\\usepackage{newunicodechar}", f"\\newunicodechar{{{char}}}{{<LaTeX 写法>}}"),
            kind="missing_glyph",
            text_en=(
                f"Current font has no glyph for `{char}`: use a font that contains it, "
                "or map it explicitly with \\newunicodechar."
            ),
        )

    citation = _UNDEFINED_CITATION_RE.search(normalized) or _UNDEFINED_CITATION_ZH_RE.search(normalized)
    if citation:
        return Hint(
            text=(
                f"引用键 `{citation.group(1)}` 未定义：检查 .bib 里是否存在该键，"
                "并确认 biber/bibtex 已经成功运行。"
            ),
            commands=("biber <jobname>", "bibtex <jobname>"),
            kind="undefined_citation",
            text_en=(
                f"Citation key `{citation.group(1)}` is undefined: check .bib for that key "
                "and confirm biber/bibtex ran successfully."
            ),
        )

    reference = _UNDEFINED_REFERENCE_RE.search(normalized) or _UNDEFINED_REFERENCE_ZH_RE.search(normalized)
    if reference:
        return Hint(
            text=(
                f"交叉引用 `{reference.group(1)}` 未定义：确认 \\label 拼写，"
                "并再编译一轮让 .aux 收敛。"
            ),
            commands=("xelatex <主文件>.tex  # 再跑一轮",),
            kind="undefined_reference",
            text_en=(
                f"Cross-reference `{reference.group(1)}` is undefined: check \\label spelling "
                "and rerun compilation to converge .aux."
            ),
        )

    env = _UNDEFINED_ENV_RE.search(normalized)
    if env:
        return Hint(
            text=(
                f"环境 `{env.group(1)}` 未定义：确认提供该环境的宏包已 \\usepackage，"
                "或检查环境名拼写/大小写。"
            ),
            kind="undefined_environment",
            text_en=(
                f"Environment `{env.group(1)}` is undefined: load the package that provides it, "
                "or check the environment name/case."
            ),
        )

    bib = _BIB_DB_RE.search(normalized)
    if bib:
        name = bib.group(1)
        stem = name[:-4] if name.lower().endswith(".bib") else name
        return Hint(
            text=f"找不到文献数据库 `{name}`：确认 .bib 路径（相对主文件目录）与文件名大小写。",
            commands=(f"kpsewhich {stem}.bib",),
            kind="missing_bib",
            text_en=f"Bibliography database `{name}` not found: check the .bib path (relative to the main file) and filename case.",
        )

    if "Too many unprocessed floats" in normalized:
        return Hint(
            text="浮动体太多：在章节间加 \\clearpage，或使用 [H] 位置与 float 宏包。",
            commands=("\\usepackage{float}", "\\clearpage"),
            kind="float_overflow",
            text_en="Too many unprocessed floats: add \\clearpage between sections, or use the float package with [H].",
        )

    if "TeX capacity exceeded" in normalized:
        return Hint(
            text="TeX 内存/栈耗尽：先排查无限递归或超长表格；确属容量问题再调高 main_memory / extra_mem_top。",
            commands=("initexmf --edit-config-file=texmf.cfg", "fmtutil-sys --all"),
            kind="capacity",
            text_en="TeX capacity exceeded: look for infinite recursion or oversized tables; only then raise main_memory / extra_mem_top.",
        )

    if "No pages of output" in normalized:
        return Hint(
            text="没有输出任何页面：检查 \\documentclass/\\begin{document} 是否完整，以及是否误用了 \\includeonly。",
            kind="no_output",
            text_en="No pages were produced: check \\documentclass/\\begin{document} and whether \\includeonly is too restrictive.",
        )

    if "Runaway argument" in normalized or "File ended while scanning" in normalized:
        return Hint(
            text="括号/环境没有闭合：从报错行往前找最近的未配对 { } 或 \\begin/\\end。",
            kind="runaway",
            text_en="Unbalanced braces/environment: look backwards from the error line for the nearest unmatched { } or \\begin/\\end.",
        )

    if "Missing $ inserted" in normalized:
        return Hint(
            text="数学模式不匹配：检查漏写的 $、\\text 中的特殊字符，或 \\ensuremath 的使用。",
            kind="math_mode",
            text_en="Math mode mismatch: check for a missing $, special characters inside \\text, or \\ensuremath usage.",
        )

    if "Emergency stop" in normalized or "Fatal error occurred" in normalized:
        return Hint(
            text="编译被致命错误中断：先修复日志里 Emergency stop 上方的第一条错误。",
            kind="fatal",
            text_en="Compilation was stopped by a fatal error: fix the first error above Emergency stop.",
        )

    if _UNDEFINED_CONTROL_RE.search(normalized):
        # 真实日志是 ``! Undefined control sequence.`` 后跟 ``l.5 ... \badcmd``；
        # 直接取全文第一个 \xxx 会误抓 \ref 之类已定义命令，优先取 l.N 行的最后一个。
        line_match = re.search(r"l\.?\d+\s+(.*)", normalized)
        target = line_match.group(1) if line_match else normalized
        controls = _CONTROL_NAME_RE.findall(target)
        name = controls[-1] if controls else "<命令>"
        return Hint(
            text=(
                f"未定义命令 `\\{name}`：检查拼写/大小写；若是宏包提供的命令，"
                "确认对应 \\usepackage 已加载。"
            ),
            commands=(
                f"grep -R \"\\\\{name}\" *.tex",
                f"tlmgr search --global --file {name}.sty",
            ),
            kind="undefined_control",
            text_en=(
                f"Undefined command `\\{name}`: check spelling/case; if a package provides it, "
                "confirm the matching \\usepackage is loaded."
            ),
        )

    if _END_MISMATCH_RE.search(normalized):
        return Hint(
            text=(
                "\\begin{document} 被错误的 \\end{...} 提前关闭：检查环境嵌套，"
                "确保每个 \\begin 都有同名 \\end。"
            ),
            kind="end_mismatch",
            text_en="\\begin{document} was ended by a wrong \\end{...}: check environment nesting so every \\begin has a matching \\end.",
        )

    if "Invalid UTF-8 byte sequence" in normalized:
        return Hint(
            text="源码不是有效 UTF-8：把报错文件另存为 UTF-8（无 BOM），并检查是否混入 GBK 字符。",
            commands=("file --mime-encoding <主文件>",),
            kind="invalid_utf8",
            text_en="Source is not valid UTF-8: save the offending file as UTF-8 (no BOM) and check for mixed GBK characters.",
        )

    if "Extra alignment tab" in normalized or "Misplaced alignment tab" in normalized:
        return Hint(
            text="表格列数不匹配：检查每行 `&` 数量是否与列格式（如 `lcr`）一致。",
            kind="alignment_tab",
            text_en="Column count mismatch: check that each row has the same number of `&` as the column spec (e.g. lcr).",
        )

    if "Missing number, treated as zero" in normalized:
        return Hint(
            text="长度/数字参数缺失：检查 \\vspace、\\hspace、\\includegraphics[width=...] 等是否漏写数字或单位。",
            kind="missing_number",
            text_en="Missing length/number argument: check \\vspace, \\hspace, \\includegraphics[width=...] for a missing number or unit.",
        )

    if "missing \\item" in normalized.lower():
        return Hint(
            text="列表环境里缺少 \\item：在 itemize/enumerate 的每个条目开头补 \\item。",
            kind="missing_item",
            text_en="Missing \\item in a list: add \\item at the start of each itemize/enumerate entry.",
        )

    package_error = _PACKAGE_ERROR_RE.search(normalized)
    if package_error:
        return Hint(
            text=(
                f"宏包 `{package_error.group(1)}` 报错：查看该行上下文与宏包选项，"
                "必要时升级/降级该宏包。"
            ),
            kind="package_error",
            text_en=(
                f"Package `{package_error.group(1)}` error: inspect the surrounding lines "
                "and package options; upgrade/downgrade if needed."
            ),
        )

    for key, value in collect_hints().items():
        if _normalize(key) in normalized:
            return Hint(
                text=value,
                kind="log_hint",
                text_en=_LOG_HINT_EN.get(key, ""),
            )
    return None


def _apply_context(hint: Hint, *, jobname: str | None, root_file: str | None) -> Hint:
    """把 ``<jobname>`` / ``<主文件>`` 占位符替换成当前项目的真实值。

    没有上下文时保留占位符，保证库调用方拿到的仍是可读模板，而不是空命令。
    """
    job = (jobname or "").strip()
    root = (root_file or "").strip()
    if not job and root:
        job = Path(root).stem
    if not root and job:
        root = f"{job}.tex"
    if not job and not root:
        return hint

    # ``<主文件>.tex`` 只能填 .tex；如果上下文给的是 .log/.blg，退回 jobname.tex。
    main_tex = root if root.lower().endswith(".tex") else (f"{job}.tex" if job else root)
    text = hint.text
    text_en = hint.text_en
    commands = list(hint.commands)
    if job:
        text = text.replace("<jobname>", job)
        text_en = text_en.replace("<jobname>", job)
        commands = [c.replace("<jobname>", job) for c in commands]
    if root:
        text = text.replace("<主文件>.tex", main_tex).replace("<主文件>", root)
        text_en = text_en.replace("<主文件>.tex", main_tex).replace("<主文件>", root)
        commands = [
            c.replace("<主文件>.tex", main_tex).replace("<主文件>", root)
            for c in commands
        ]
    return Hint(text=text, commands=tuple(commands), kind=hint.kind, text_en=text_en)


def hint_for_text(
    text: str,
    *,
    jobname: str | None = None,
    root_file: str | None = None,
    language: str | None = None,
) -> Hint | None:
    """按一条日志文本给出建议；无匹配返回 ``None``。

    Args:
        jobname: 可选，用于把 ``biber <jobname>`` 之类模板替换成真实命令。
        root_file: 可选，主 ``.tex`` 路径，用于替换 ``<主文件>``。
        language: ``"en"`` 时优先返回英文说明；其他值保持中文。
    """
    hint = _hint_for_text_raw(text)
    if hint is None:
        return None
    hint = _apply_context(hint, jobname=jobname, root_file=root_file)
    if language and language.lower() == "en" and hint.text_en:
        return Hint(
            text=hint.text_en,
            commands=hint.commands,
            kind=hint.kind,
            text_en=hint.text_en,
        )
    return hint


def hint_for_entry(
    entry: object,
    *,
    jobname: str | None = None,
    root_file: str | None = None,
    language: str | None = None,
) -> Hint | None:
    """对 ``LogEntry`` / ``ReportEntry`` 之类的条目给出建议。

    未显式传 ``jobname`` 时，从条目的 ``file`` 字段推断主文件 stem，
    让 ``biber <jobname>`` 直接变成 ``biber main``。
    """
    text = getattr(entry, "text", "") or ""
    entry_file = getattr(entry, "file", "") or ""
    return hint_for_text(
        text,
        jobname=jobname,
        root_file=root_file or entry_file or None,
        language=language,
    )

