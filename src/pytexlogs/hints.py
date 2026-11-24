"""可执行建议（hint）：把日志条目翻译成“下一步该做什么”。

设计原则：
- 提示词表与解析器同源（LATEX/BIBTEX/BIBER 三张表），不另起一套口径；
- 匹配时对反斜杠做归一化——原表里的 ``Overfull \\\\hbox`` 在源码中实际是
  两个反斜杠，而真实日志是 ``Overfull \\hbox``，不归一化就永远匹配不上；
- 对“缺文件/缺宏包/缺字体”这类可自动修复的问题，额外给出安装命令
  （同时给 TeX Live 与 MiKTeX 两种写法，调用方按发行版挑一条即可）。

规则改为显式表格（``_RULES``）：每条规则 = 匹配器 + 生成器，
``_hint_for_text_raw`` 只负责按顺序跑一遍。顺序就是语义（``Emergency stop``
必须先于 ``Undefined control sequence``），因此顺序被 ``RULE_IDS``
固化下来，供 ``tests/test_hints_precedence.py`` 做快照与优先级断言。

顺序要点（新增规则时必须保持）：
- ``font_not_loadable`` 早于 ``missing_font``：否则 ``Font \\foo=... not loadable``
  会被“字体未找到”的贪婪正则抓成整句垃圾字体名；
- ``missing_bbl`` 早于 ``undefined_citation``：先解决后端没跑，再谈引用键；
- ``biber_case_mismatch`` 早于 ``log_hint``：避免被通用 biber 文案吞掉；
- ``cjk_missing_glyph`` 与 ``missing_glyph`` 分开：前者是 xeCJK 字体族消息，
  后者是 TeX 引擎的缺字形消息；
- ``fontspec_font_not_found`` 早于 ``package_error``：否则只剩“查看上下文”兜底；
- ``missing_begin_document``/``extra_close_brace`` 等具体 LaTeX 错误早于
  ``package_error`` 与 ``log_hint``；
- ``capacity`` 仍早于 ``log_hint``，但内部按括号子类型分流根因。
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

__all__ = [
    "RULE_IDS",
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
    #: 英文命令；为空时调用方回退到 ``commands``。含中文槽位/注释的命令须在此提供
    #: 英文等价写法，避免 ``--lang en`` 输出残留中文。
    commands_en: tuple[str, ...] = ()
    #: 英文说明；为空时调用方回退到 ``text``，避免每条规则都必须准备两种语言。
    text_en: str = ""
    #: 命中的规则 id（与 ``RULE_IDS`` 一一对应）；空串表示不是规则表产出的 hint。
    #: 该字段用于 JSON/SARIF 的可追溯性与测试断言，不参与文案生成。
    rule_id: str = ""
    #: 一行版说明（``hint_style="brief"`` 时使用）；为空时回退到 ``text``。
    brief: str = ""
    #: 一行版英文说明；为空时回退到 ``brief`` 再回退到 ``text``。
    brief_en: str = ""


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


def _drop_quoted_lines(text: str) -> str:
    """去掉被当作引用/注释/讨论文本的行。

    日志讨论、复现说明里常把错误样例放在引用块（``> `` 前缀）、Markdown 注释
    （``% ``）、表格引用（``| ``）或成对引号包裹的整行；这些字符串不是真实
    编译输出，不能据此给出可执行建议。剥离后剩余空文本自然落到无匹配。
    """
    kept = [line for line in text.splitlines() if not _is_non_log_line(line)]
    return "\n".join(kept)


#: 行首即属于讨论/注释语境的前缀。
_NON_LOG_PREFIXES = ("> ", "% ", "| ")
#: 成对包裹整行的引号（含中英文弯引号）。
_LINE_QUOTES = ('"', "'", "“", "”", "‘", "’")


def _is_non_log_line(line: str) -> bool:
    stripped = line.lstrip()
    if stripped.startswith(_NON_LOG_PREFIXES):
        return True
    if len(stripped) >= 2 and stripped[0] in _LINE_QUOTES and stripped[-1] == stripped[0]:
        return True
    return False


#: 解释性散文线索：出现这些片段说明文本在“讲错误是什么”，不是错误日志本身。
_PROSE_CLUES = (
    " in the faq",
    " tutorial",
    " changelog",
    " means ",
    " explained",
    " occurs",
    "please fix",
    "says:",
    " appears",
    "the current font",
)


def _looks_like_prose(text: str) -> bool:
    lowered = text.lower()
    return any(clue in lowered for clue in _PROSE_CLUES)


#: 错误帧标志：行首 ``!``、``LaTeX Error:``/``LaTeX Warning:``、``Package <x> Error:``。
#: 命中其一即视为真实错误帧，续行里的说明性词语不能把整帧抑制成散文（M2）。
_ERROR_FLAG_RE = re.compile(r"package\s+\S+\s+error:", re.IGNORECASE)


def _has_error_flag(text: str) -> bool:
    for line in text.splitlines():
        stripped = line.strip().lower()
        if stripped.startswith("!"):
            return True
        if "latex error:" in stripped or "latex warning:" in stripped:
            return True
        if _ERROR_FLAG_RE.search(stripped):
            return True
    return False


#: TeX 日志按 79 列硬折行，长文件名会断成两行；单引号是文件名的右界，
#: 因此不能用 ``[^'\n]`` 排除换行，否则 ``File `pressure_cold_\nlayer5.pdf' not
#: found`` 会落到 ``package_error`` 兜底，丢掉“缺图片”的准确建议。
_MISSING_FILE_RE = re.compile(r"File\s+`([^']+)'\s+not\s+found", re.IGNORECASE)
_PACKAGE_ERROR_RE = re.compile(r"(?:Package|Class)\s+(\S+)\s+Error:", re.IGNORECASE)
_FONT_NOT_FOUND_RE = re.compile(r"Font(?: shape)?\s+`?([^\s'`]+)'?\s+(?:not found|undefined)", re.IGNORECASE)
#: ``! Font \foo=NoSuchFont at 10.0pt not loadable: Metric (TFM) file not found.``
#: 必须先于 missing_font 命中，否则后者的贪婪正则会把整句抓成垃圾字体名。
#: Xe/Lua 真实日志的规格是 NFSS 串（``TU/Family(0)/m/n/10`` 或
#: ``\TU/Family(0)/m/n/10``），``=`` 后是 ``name:Family:mode=node;...`` 描述，
#: 且名称可能被 max_print_line 折行；``loadable`` 也可能拆成 ``loada\nble``。
_FONT_NOT_LOADABLE_RE = re.compile(
    r"Font\s+(\\[^\s=]+|[^\s=]+)\s*=\s*([^\n]*(?:\n[^\n]*){0,2})\s+at\s+[0-9.]+\s*pt\s+"
    r"not\s+loada\s*ble(?::\s*([^.\n]+))?",
    re.IGNORECASE,
)
#: 显式带 ``.tfm`` 文件名的才是 pdfTeX 缺编码字体度量包；Xe/Lua 变体
#: ``Metric (TFM) file or installed font not found`` 没有 .tfm，不能把 ``or``
#: 抓成文件名，也不能走 pdflatex 的 ec/cm-super 排查链路。
_TFM_EXPLICIT_RE = re.compile(r"Metric \(TFM\) file\s+`?[^\s']+\.tfm", re.IGNORECASE)
#: pdflatex 缺 TFM 度量文件（缺编码字体宏包）；与 Xe/Lua 的 OpenType 字体族找不到是两条链路。
_TFM_MISSING_RE = re.compile(
    r"Metric \(TFM\) file\s+`?([^\s']+\.tfm)`?",
    re.IGNORECASE,
)
_UNICODE_RE = re.compile(r"Unicode character\s+(\S+)\s+\(U\+([0-9A-Fa-f]+)\)", re.IGNORECASE)
#: 引用键引号兼容 LaTeX 传统反引号 `` `key' ``、直单引号 `` 'key' `` 与双引号 `` "key" ``。
_UNDEFINED_CITATION_RE = re.compile(
    r"Citation\s+[`'\"]([^`'\"\s]+)[`'\" ]?\s+(?:on page \d+\s+)?undefined",
    re.IGNORECASE,
)
_UNDEFINED_REFERENCE_RE = re.compile(
    r"Reference\s+[`'\"]([^`'\"\s]+)[`'\" ]?\s+(?:on page \d+\s+)?undefined",
    re.IGNORECASE,
)
# LaTeX parser 会把这两类条目的展示文本翻译成 “找不到 citation/reference `key`”；
# 0.10 起改为语言中性的 “Undefined citation/reference `key`”。两种文案都要认，
# 否则 CLI 摘要里只有条目、没有建议。
_UNDEFINED_CITATION_DISPLAY_RE = re.compile(r"(?:找不到|Undefined)\s+citation\s+`([^']+)`", re.IGNORECASE)
_UNDEFINED_REFERENCE_DISPLAY_RE = re.compile(r"(?:找不到|Undefined)\s+reference\s+`([^']+)`", re.IGNORECASE)
_UNDEFINED_ENV_RE = re.compile(r"Environment\s+(\S+)\s+undefined", re.IGNORECASE)
_BIB_DB_RE = re.compile(r"(?:I couldn't open database file|Cannot find file)\s+([^\s.]+)", re.IGNORECASE)
#: 缺字形：XeLaTeX 真实日志是 ``There is no 中 (U+4E2D) in font ...;!``，
#: 字符与 ``in font`` 之间多了 ``(U+XXXX)``；旧正则只认 ``\S+`` 会整句失配。
#: 码位后缀可选（xeCJK/部分引擎不打印 U+XXXX）；字体名可能被 79 列折行，
#: 字体组允许跨行，匹配后在生成器里裁掉空白。
_MISSING_CHAR_RE = re.compile(
    r"Missing character:\s+There is no\s+(.+?)"
    r"(?:\s+\(U\+([0-9A-Fa-f]+)\))?\s+in font\s+([^!]+)",
    re.IGNORECASE,
)
#: xeCJK 缺字形：``CJKfamily 'song' (...) does not contain glyph '中' ( U + 4E2D )``，
#: 同时容忍 ``(U+4E2D)`` 与 ``( U + 4E2D )`` 两种空格写法。
_CJK_MISSING_GLYPH_RE = re.compile(
    r"CJKfamily\s+'([^']+)'\s*\(([^)]*)\)\s+does not contain glyph\s+'([^']+)'"
    r"\s*\(\s*U\s*\+\s*([0-9A-Fa-f]+)\s*\)",
    re.IGNORECASE,
)
_UNDEFINED_CONTROL_RE = re.compile(r"Undefined control sequence", re.IGNORECASE)
_CONTROL_NAME_RE = re.compile(r"\\([A-Za-z@]+)")
#: 定义类包装命令：``\newcommand``/``\renewcommand``/``\providecommand``/``\def``/
#: ``\newenvironment``（可带 ``*``）。命令名可在花括号内（带或不带反斜杠），也可直接
#: 以 ``\csname`` 形式给出。报错行出现这类写法时，被定义的裸名称才是线索；包装命令
#: 本身不是“未定义命令”，也没有对应 .sty 可装。
_DEF_COMMAND_RE = re.compile(
    r"\\(newcommand|renewcommand|providecommand|def|newenvironment)(\*)?"
    r"\s*(?:\{\\?([A-Za-z@]+)\}|\\([A-Za-z@]+))"
)
#: fontspec 按文件名加载的扩展名（手册 §2.2：靠 ``.otf`` 扩展名判定，也可用
#: ``Extension=`` 单独指定）。
_FONT_FILE_EXT_RE = re.compile(r"\.(otf|ttf|ttc|otc)\s*$", re.IGNORECASE)
_END_MISMATCH_RE = re.compile(r"\\begin\{document\}\s+ended by\s+\\end\{(\w+)\}", re.IGNORECASE)
#: 宏包选项冲突：真实日志是 ``LaTeX Error: Option clash for package graphicx.``，
#: 不是 ``Package X Error:`` 形式，因此必须独立成规则，否则只会落到兜底。
_OPTION_CLASH_RE = re.compile(r"Option\s+clash\s+for\s+package\s+([^\s.,]+)", re.IGNORECASE)
#: 上下标重复：``! Double subscript.`` / ``! Double superscript.``
_DOUBLE_SCRIPT_RE = re.compile(r"Double\s+(subscript|superscript)", re.IGNORECASE)
#: ``! Missing \begin{document}.``（忽略大小写）。
_MISSING_BEGIN_DOC_RE = re.compile(r"Missing\s+\\begin\{document\}", re.IGNORECASE)
#: ``! Too many }'s.`` 真实文本就是这个写法。
_EXTRA_CLOSE_BRACE_RE = re.compile(r"Too many \}'s", re.IGNORECASE)
_MISSING_RIGHT_RE = re.compile(r"Missing \\right\.?\s+inserted|Missing delimiter\s+([()])\.?\s+inserted", re.IGNORECASE)
_BAD_MATH_DELIMITER_RE = re.compile(r"Bad math environment delimiter|Display math should end with \$\$", re.IGNORECASE)
_MISPLACED_NOALIGN_RE = re.compile(r"Misplaced \\noalign", re.IGNORECASE)
_ILLEGAL_UNIT_RE = re.compile(r"Illegal unit of measure \(pt inserted\)", re.IGNORECASE)
_COMMAND_REDEFINED_RE = re.compile(r"Command\s+(\\[A-Za-z@]+)\s+already defined", re.IGNORECASE)
_NO_LINE_TO_END_RE = re.compile(r"There's no line here to end", re.IGNORECASE)
_PDF_STRING_RE = re.compile(r"Token not allowed in a PDF string", re.IGNORECASE)
_FONTSPEC_NOT_FOUND_RE = re.compile(r"The font\s+\"([^\"]+)\"\s+cannot be found", re.IGNORECASE)
_FONTSET_UNAVAILABLE_RE = re.compile(
    r"CTeX fontset\s+[`'\"]([^`'\"]+)[`'\"]\s+is unavailable in current"
    #: 真实日志 ``... in current\n(ctex) mode.`` / ``(ctexart) mode.``：
    #: current 与 mode 之间允许换行 + 宏包/类名续行前缀。
    r"(?:\s*\([^)]{1,40}\))?\s*mode",
    re.IGNORECASE,
)
_MISSING_BBL_RE = re.compile(r"No file\s+(\S+?)\.bbl[.;:?]?", re.IGNORECASE)

#: 工具名 → 引擎二进制名；``<engine>`` 占位符在 ``_apply_context`` 按实际 tool 回填。
_ENGINE_BINARIES = {
    "pdflatex": "pdflatex",
    "xelatex": "xelatex",
    "lualatex": "lualatex",
    "tectonic": "tectonic",
    "latex": "latex",
}
#: biblatex 首遍未跑后端的另一种措辞：``Package biblatex Warning: Please (re)run
#: Biber on the file:``，与 ``No file main.bbl.`` 同属“后端没跑”根因。
_RERUN_BIBLATEX_RE = re.compile(r"Please \(re\)run Biber", re.IGNORECASE)
_CAPACITY_RE = re.compile(r"TeX capacity exceeded, sorry \[([^\]]+)\]", re.IGNORECASE)
_RUNAWAY_SCAN_RE = re.compile(r"File ended while scanning use of\s+(\\[A-Za-z@]+)", re.IGNORECASE)
_MISSING_NUMBER_TOKEN_RE = re.compile(r"<to be read again>\s*(?:\r?\n\s*)?(\S+)")

#: 只有这些后缀才代表“缺宏包/文档类”，其他 ``File ... not found`` 是缺图片/缺输入文件。
_PACKAGE_SUFFIXES = (".sty", ".cls", ".def", ".cfg", ".clo", ".ldf")
_GRAPHIC_SUFFIXES = (".png", ".jpg", ".jpeg", ".pdf", ".eps", ".ps", ".svg", ".bmp", ".tif", ".tiff")
_BIB_SUFFIXES = (".bib",)

#: 旧提示表（LATEX/BIBTEX/BIBER）的英文文案；键与中文表共用，供 --lang en 使用。
_LOG_HINT_EN = {
    "Undefined control sequence": "Check the command spelling, or confirm the package that provides it is loaded.",
    "Undefined reference": "The label is not recorded yet: rerun LaTeX once or twice (or check the \\label/\\ref name).",
    "Undefined citation": "Bibliography key not found: check that the .bib entry key matches \\cite{key} and that bibtex/biber ran.",
    "Overfull \\\\hbox": "A line/box exceeds the text width: add a manual break, use \\sloppy, or shrink the content.",
    "Underfull \\\\hbox": "A line/box is underfull: usually acceptable; add content or use \\linebreak if it looks bad.",
    "Underfull \\\\vbox": "A page/box is underfull: usually acceptable; add content or adjust vertical spacing if it looks bad.",
    "Missing character": "The current font lacks this glyph: switch to a font that contains it, or map it with \\newunicodechar; "
    "for CJK/fullwidth characters, configure a ctex/xeCJK CJK font.",
    "Rerun to get cross-references right": "Rerun LaTeX: page numbers/links in the .aux file need a second pass.",
    "Rerun to get citations correct": "Run bibtex/biber first, then rerun LaTeX once or twice to sync citations.",
    "I'm skipping whatever remains of this entry": "BibTeX entry syntax error: check for a missing comma, unbalanced braces, or a misspelled field name.",
    "I'm skipping whatever remains of this command": '@string/abbreviation definition error: check the @string{key = "value"} syntax.',
    "A bad cross reference": "A crossref points to a non-existent entry: check that crossref = {xxx} exists in the same .bib file.",
    "---while reading file": "Failed to read an auxiliary file: check that the .aux was generated (run pdflatex first) and that paths are correct.",
    "I didn't find a database entry": "Biber could not find the citation key: check the @xxx{key, entry in .bib and that it matches \\cite/\\autocite.",
    "Duplicate entry key": "Duplicate bibliography entry key: check for duplicate keys in .bib.",
    "WARN -": "Generic Biber warning: likely a data validation issue; check .bib fields against biblatex requirements.",
}


def _join_wrapped_name(name: str) -> str:
    """把被 ``max_print_line`` 折断的文件名接回去。

    TeX 在 79 列处硬折行，断点可能落在文件名中间（``pressure_cold_`` +
    ``layer5.pdf``）。段尾/段首有空格时才补一个空格，否则直接粘合，避免给
    ``kpsewhich`` 造出一个实际上不存在的空格。
    """
    parts = name.split("\n")
    joined = parts[0]
    for part in parts[1:]:
        joined = f"{joined} {part.lstrip()}" if joined.endswith(" ") else joined + part
    return joined


def _missing_file_name(text: str) -> str | None:
    """提取 ``File `xxx' not found`` 中的文件名（不做任何归因）。"""
    match = _MISSING_FILE_RE.search(text)
    return _join_wrapped_name(match.group(1)) if match else None


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
            text=(f"找不到图片 `{name}`：确认路径相对主文件目录，或把图片目录写进 \\graphicspath{{{{...}}}}。"),
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
            f"File `{name}` not found: check \\input / \\include / \\includegraphics paths relative to the main file."
        ),
    )


# --- 规则表 ---------------------------------------------------------------
#
# 每条规则由「匹配器 + 生成器」组成：匹配器拿归一化后的日志文本，命中时返回
# 上下文（正则 Match / 提取到的名字 / 原文），生成器据此产出 Hint。
# 匹配器返回 None 或空串表示未命中；生成器返回 None 表示“这条规则放弃了，
# 交给后面的规则”（例如 ``File `x.png' not found`` 已由图片分支处理，
# 非图片后缀的缺文件规则不该吞掉）。


@dataclass(frozen=True, slots=True)
class _Rule:
    """一条提示规则。``rule_id`` 用于快照与优先级断言。"""

    rule_id: str
    match: Callable[[str], Any]
    build: Callable[..., Hint | None]
    #: 限定可命中的工具名（LaTeX 引擎集合）；``None`` 表示不限工具。
    #: 工具名为空（未知上下文）时一律放行；显式后端日志（biber/bibtex）下跳过。
    tools: frozenset[str] | None = None


#: 结构化 LaTeX 排版类规则只在 LaTeX 引擎日志下命中；后端日志不套用这些语义。
_LATEX_TOOLS = frozenset({"latex", "pdflatex", "xelatex", "lualatex", "tectonic"})
#: 文献链路后端工具；``missing_bib`` 跨 LaTeX / biber / bibtex 命中。
_BIB_BACKEND_TOOLS = frozenset({"biber", "bibtex"})
_BIB_SCOPED_TOOLS = _LATEX_TOOLS | _BIB_BACKEND_TOOLS


def _any_of(*needles: str, lower: bool = False) -> Callable[[str], bool]:
    """子串匹配器：任意一个 needle 出现即命中（等价于原来的 ``a in t or b in t``）。"""

    def _match(text: str) -> bool:
        haystack = text.lower() if lower else text
        return any(needle in haystack for needle in needles)

    return _match


def _match_package(text: str) -> str | None:
    return detect_missing_package(text)


def _build_package(pkg: str) -> Hint:
    return Hint(
        text=f"缺少宏包/文档类 `{pkg}`：请安装后重新编译（或改用已有宏包）。",
        commands=_install_commands(pkg),
        kind="missing_package",
        text_en=(f"Missing package/class `{pkg}`: install it, then rebuild (or switch to an existing package)."),
    )


def _match_missing_file(text: str) -> str | None:
    return _missing_file_name(text)


def _match_font_not_loadable(text: str) -> Any:
    # 快速短路：不含 loadable/loada 片段的条目（缺字形、畸形 Font 行等）
    # 直接跳过，避免宽松规格段在长文本上回溯。
    lowered = text.lower()
    if "loadable" not in lowered and "loada" not in lowered:
        return None
    match = _FONT_NOT_LOADABLE_RE.search(text)
    if match is None:
        return None
    # 显式 .tfm 度量文件缺失是 pdfTeX 缺编码字体包链路，交给 tfm_font_missing。
    if _TFM_EXPLICIT_RE.search(text):
        return None
    return match


def _font_family_from_match(match: Any) -> str:
    """从 ``Font <spec>=<after> at ...`` 提取可读字族名。

    优先取 ``name:<family>:...`` 描述段；否则从 NFSS 规格
    ``\\TU/<family>(0)/m/n/10`` 取编码后一段；最后回退到等号后原文。
    """
    cmd = (match.group(1) or "").strip()
    after_eq = re.sub(r"\s+", " ", (match.group(2) or "")).strip().strip('"')
    if after_eq.startswith("name:"):
        seg = after_eq.split(":")
        if len(seg) > 1 and seg[1]:
            return seg[1]
    nfss = cmd.lstrip("\\")
    if "/" in nfss:
        parts = nfss.split("/")
        if len(parts) > 1 and parts[1].split("(")[0]:
            return parts[1].split("(")[0]
    return after_eq or cmd


def _build_font_not_loadable(match: Any, tool_name: str = "") -> Hint:
    spec = _font_family_from_match(match)
    reason = (match.group(3) or "未知原因").strip()
    tool = (tool_name or "").lower()
    lowered_reason = reason.lower()
    #: Xe/Lua 的 “installed font not found” / “metric data not found or bad”
    #: 与 NFSS 规格是 OpenType/系统字体族找不到，没有 .tfm 度量文件一说；
    #: 不给 kpsewhich *.tfm / ec 包建议，LuaLaTeX 额外提示刷新字体缓存。
    opentype_backend = tool in {"xelatex", "lualatex"} or any(
        keyword in lowered_reason
        for keyword in ("installed font", "metric data", "font file not found", "not found or bad")
    )
    if opentype_backend:
        commands = [f'fc-list : family | grep -iF "{spec}"']
        if tool == "lualatex":
            commands.append("luaotfload-tool --update")
        return Hint(
            text=(
                f"字体 `{spec}` 无法加载（{reason}）。当前引擎按字体族名/OpenType "
                "查找字体失败：核对字体全名与拼写（大小写、重音、空格），确认字体已安装；"
                "按文件名加载时核对扩展名（`.otf/.ttf/.ttc`）与 `Path=` 目录，"
                "不要按 pdfTeX 的 TFM 度量包方向排查。"
            ),
            commands=tuple(commands),
            kind="missing_font",
            text_en=(
                f"Font `{spec}` cannot be loaded ({reason}): the current engine "
                "could not find the OpenType/system font by family name. Verify the "
                "full family name and spelling (case, accents, spaces) and that the "
                "font is installed; when loading by file name, check the extension "
                "(`.otf/.ttf/.ttc`) and the `Path=` directory. Do not debug this "
                "as a pdfTeX TFM metric package issue."
            ),
        )
    return Hint(
        text=(
            f"字体 `{spec}` 无法加载（{reason}）。TeX 找不到该字体的度量/字形文件："
            f"若是 `\\font\\foo={spec}` 直接指定，改用已安装字族；"
            "若是宏包内部字体，确认对应宏包完整安装"
            "（TeX Live：`tlmgr install <包名>`；MiKTeX：包管理器安装），"
            "不要手工伪造 TFM。"
        ),
        commands=(f"kpsewhich {spec.lower()}.tfm",),
        kind="missing_font_tfm",
        text_en=(
            f"Font `{spec}` cannot be loaded ({reason}): TeX cannot find its "
            "metric/glyph files. If specified directly with "
            f"`\\font\\foo={spec}`, switch to an installed family; if it is a "
            "package-internal font, confirm the package is fully installed "
            "(TeX Live: `tlmgr install <package>`; MiKTeX: install via the "
            "package manager). Do not hand-craft a TFM."
        ),
    )


def _match_tfm_missing(text: str) -> Any:
    return _TFM_MISSING_RE.search(text)


def _build_tfm_missing(match: Any, tool_name: str = "") -> Hint:
    tfm = (match.group(1) or "<name>.tfm").strip()
    if not tfm.lower().endswith(".tfm"):
        tfm = f"{tfm}.tfm"
    tool = (tool_name or "").lower()
    if tool in {"xelatex", "lualatex"}:
        return Hint(
            text=(
                f"当前引擎（{tool}）报告找不到 TFM 度量文件 `{tfm}`：TFM 是 8 位 "
                "pdfTeX 链路的概念，XeLaTeX/LuaLaTeX 一般不缺 TFM；先核对 OpenType/"
                "系统字体族是否安装，不要按 ec/cm-super 字体包方向排查。"
            ),
            commands=(f"kpsewhich {tfm}",),
            kind="tfm_font_missing",
            text_en=(
                f"The current engine ({tool}) reports a missing TFM metric file "
                f"`{tfm}`: TFM belongs to the 8-bit pdfTeX pipeline; XeLaTeX/"
                "LuaLaTeX usually do not miss TFM files. Check whether the OpenType/"
                "system family is installed first; do not debug this as an ec/"
                "cm-super font package issue."
            ),
        )
    return Hint(
        text=(
            f"pdflatex 找不到 TFM 度量文件 `{tfm}`：通常是缺编码字体宏包"
            "（如 `ecrm1000.tfm` 属 `ec`/`cm-super` 字体包），"
            "不是 fontspec 的“字体族找不到”，不要去系统字体目录找 OpenType 字体。"
            f"TeX Live：`tlmgr search --file {tfm} --global` 定位宏包后 "
            "`tlmgr install <包>`（或装 `collection-fontsrecommended`）；"
            "MiKTeX：用包管理器安装对应字体包。"
        ),
        commands=(f"tlmgr search --file {tfm} --global",),
        kind="tfm_font_missing",
        text_en=(
            f"pdflatex cannot find the TFM metric file `{tfm}`: this usually means a "
            "missing encoding-font package (e.g. `ecrm1000.tfm` belongs to the "
            "`ec`/`cm-super` font packages). It is not a fontspec “family not found” "
            "issue—do not look for an OpenType font in the system font directory. "
            f"TeX Live: run `tlmgr search --file {tfm} --global` to locate the package, "
            "then `tlmgr install <package>` (or install `collection-fontsrecommended`); "
            "MiKTeX: install the matching font package with the package manager."
        ),
    )


def _match_font(text: str) -> Any:
    # ``Missing character: There is no X in font Y`` 里也含 "in font"，
    # 但它属于缺字形，交给后面的 missing_glyph 规则，别在这里抢答。
    # 短路必须在正则搜索之前：贪婪字符类在多行文本上回溯代价过高（F1）。
    if "Missing character" in text:
        return None
    return _FONT_NOT_FOUND_RE.search(text)


def _build_font(match: Any) -> Hint:
    family = match.group(1).strip()
    return Hint(
        text=(
            f"字体/字形 `{family}` 不可用：检查字体是否安装，或改用 fontspec 可用的字族。"
            f"Linux/macOS 可用 `fc-list | grep -i '{family}'` 核对；"
            "Windows 没有 `fc-list`，先在系统字体设置里核对完整字体名。"
            "`initexmf --update-fndb` 只刷新 TeX 文件名数据库，不等于刷新系统字体缓存。"
        ),
        commands=(
            f"fc-list | grep -i '{family}'",
            "initexmf --update-fndb",
        ),
        kind="missing_font",
        text_en=(
            f"Font/glyph `{family}` is unavailable: check the font installation "
            "or switch to a fontspec-compatible family. On Linux/macOS verify "
            f"with `fc-list | grep -i '{family}'`; on Windows, check the full "
            "font name in system Font Settings (there is no `fc-list`). "
            "`initexmf --update-fndb` only refreshes the TeX filename database, "
            "not the system font cache."
        ),
    )


def _match_fontset_unavailable(text: str) -> Any:
    return _FONTSET_UNAVAILABLE_RE.search(text)


def _build_fontset_unavailable(match: Any) -> Hint:
    name = match.group(1)
    return Hint(
        text=(
            f"当前引擎模式不支持该 fontset：ctex 的 fontset `{name}` 在当前模式下不可用，"
            "adobe/fandol/mac/ubuntu 等 fontset 不支持 pdfLaTeX。"
            "按引擎选择匹配的 fontset（XeLaTeX/LuaLaTeX 可用 fandol/ubuntu/mac 之一），"
            "或在文档类选项里写 `fontset=none` 后用 `\\setCJKmainfont` 等命令自定义中文字体。"
        ),
        commands=(
            "xelatex <主文件>.tex",
            "\\usepackage[fontset=fandol]{ctex}",
        ),
        commands_en=(
            "xelatex <main file>.tex",
            "\\usepackage[fontset=fandol]{ctex}",
        ),
        kind="fontset_unavailable",
        text_en=(
            f"The ctex fontset `{name}` is unavailable in the current engine mode: "
            "fontsets such as adobe/fandol/mac/ubuntu do not support pdfLaTeX. "
            "Pick a fontset that matches your engine (e.g. fandol/ubuntu/mac for "
            "XeLaTeX/LuaLaTeX), or pass `fontset=none` to the class and define CJK "
            "fonts yourself with `\\setCJKmainfont`."
        ),
    )


def _match_unicode(text: str) -> Any:
    return _UNICODE_RE.search(text)


def _build_unicode(match: Any) -> Hint:
    char, codepoint = match.group(1), match.group(2)
    if _is_cjk_char(char):
        return Hint(
            text=(
                f"这条消息来自 pdfLaTeX/8 位引擎的 inputenc 层；"
                "XeLaTeX/LuaLaTeX 下同类问题表现为 `Missing character`。"
                f"字符 `{char}` (U+{codepoint}) 是中文/全角字符："
                "优先改用 XeLaTeX/LuaLaTeX + ctex；必须留在 pdfLaTeX 时，"
                "使用 CJK/ctex 的 pdfTeX 模式。"
            ),
            commands=("xelatex <主文件>.tex", "lualatex <主文件>.tex"),
            commands_en=("xelatex <main file>.tex", "lualatex <main file>.tex"),
            kind="unicode",
            text_en=(
                f"This message comes from the inputenc layer of pdfLaTeX/8-bit "
                "engines; under XeLaTeX/LuaLaTeX the same problem appears as "
                f"`Missing character`. Character `{char}` (U+{codepoint}) is a "
                "CJK/fullwidth character: prefer XeLaTeX/LuaLaTeX with ctex; if you "
                "must stay on pdfLaTeX, use the CJK/ctex pdfTeX mode."
            ),
        )
    return Hint(
        text=(
            f"这条消息来自 pdfLaTeX/8 位引擎的 inputenc 层；"
            "XeLaTeX/LuaLaTeX 下同类问题表现为 `Missing character`。"
            f"字符 `{char}` (U+{codepoint}) 是符号：优先替换为等价 LaTeX 命令"
            "（如 `\\ensuremath{\\alpha}`），或用 `\\newunicodechar` 映射；"
            "确有必要再考虑切换引擎。"
        ),
        commands=(
            f"\\ensuremath{{{char}}}",
            "\\usepackage{newunicodechar}",
        ),
        kind="unicode",
        text_en=(
            f"This message comes from the inputenc layer of pdfLaTeX/8-bit "
            "engines; under XeLaTeX/LuaLaTeX the same problem appears as "
            f"`Missing character`. Character `{char}` (U+{codepoint}) is a "
            "symbol: first replace it with an equivalent LaTeX command "
            "(e.g. `\\ensuremath{\\alpha}`) or map it with `\\newunicodechar`; "
            "switch engines only if really necessary."
        ),
    )


def _match_cjk_missing_glyph(text: str) -> Any:
    return _CJK_MISSING_GLYPH_RE.search(text)


def _build_cjk_missing_glyph(match: Any) -> Hint:
    family, font, char, code = match.groups()
    font = font.strip() or "未知字体"
    return Hint(
        text=(
            f"CJK 字体族 `{family}`（`{font}`）没有字形 `{char}` (U+{code})。"
            "按顺序排查：① 确认 `\\setCJKmainfont`/`\\newCJKfontfamily` "
            "给该 family 配的字体确实包含这个字；② 检查 FallBack 字体"
            "（`\\setCJKfallbackfamilyfont` / xeCJK 的 fallback 列表）是否覆盖该字；"
            "③ 前两步都确认后仍缺，再更换含该字的中文字体，或用 `\\newunicodechar` 做局部映射。"
        ),
        kind="cjk_missing_glyph",
        text_en=(
            f"The CJK family `{family}` (`{font}`) has no glyph for `{char}` "
            f"(U+{code}). Check in order: ① confirm the font assigned to this "
            "family via `\\setCJKmainfont`/`\\newCJKfontfamily` actually contains "
            "the character; ② check whether the FallBack font "
            "(`\\setCJKfallbackfamilyfont` / the xeCJK fallback list) covers it; "
            "③ only after both, switch to a CJK font containing it or map it "
            "locally with `\\newunicodechar`."
        ),
    )


def _match_missing_glyph(text: str) -> Any:
    return _MISSING_CHAR_RE.search(text)


def _is_cjk_char(char: str) -> bool:
    """判断缺字形字符是否属于 CJK（含全角标点）。"""
    return any(
        "\u3000" <= c <= "\u303f"  # CJK punctuation
        or "\u3400" <= c <= "\u4dbf"  # CJK Extension A
        or "\u4e00" <= c <= "\u9fff"  # CJK Unified Ideographs
        or "\uf900" <= c <= "\ufaff"  # CJK Compatibility Ideographs
        or "\ufe30" <= c <= "\ufe4f"  # CJK Compatibility Forms
        or "\uff00" <= c <= "\uffef"  # Halfwidth/Fullwidth Forms
        for c in char
    )


def _normalize_font_spec(font: str) -> str:
    """把 fontspec 内部 spec 规范成可读字族名。

    去掉 ``name:`` 前缀与 ``:key=value`` / ``;...`` 参数段（mode/script/
    language/jfm 等）；原始 spec 仍保留在条目文本/error_pos 中，不在此丢失。
    """
    f = (font or "").strip().strip('"').strip("'")
    if f.lower().startswith("name:"):
        f = f[5:]
    f = re.split(r"[:;]", f, maxsplit=1)[0].strip()
    return f or (font or "").strip()


def _build_missing_glyph(match: Any, tool_name: str = "") -> Hint:
    char = match.group(1).strip()
    codepoint = match.group(2)
    raw_font = re.sub(r"\s+", " ", match.group(3)).strip()
    font = _normalize_font_spec(raw_font)
    if "nullfont" in raw_font:
        return Hint(
            text=(
                f"这是前面致命错误的连锁症状（nullfont）：`{char}` "
                "并没有真正进入排版。先修日志里更早的第一条错误，不要在这里换字体。"
            ),
            kind="missing_glyph",
            text_en=(
                f"This is a cascade of an earlier fatal error (nullfont): `{char}` "
                "never really reached typesetting. Fix the first error earlier in "
                "the log; do not switch fonts here."
            ),
        )
    if _is_cjk_char(char):
        codepoint_label = f"（U+{codepoint}）" if codepoint else ""
        engine = (tool_name or "").lower()
        if engine in {"xelatex", "lualatex", "tectonic"}:
            # 已在 Unicode 引擎：症结就是当前 CJK 字体不含该字，不再建议换引擎。
            return Hint(
                text=(
                    f"当前 CJK 字体 `{font}` 不含中文字形 `{char}`{codepoint_label}。"
                    "用 `\\setCJKmainfont`/`\\setCJKsansfont` 换一个含该字的中文字体，"
                    "或补 FallBack 字体；Xe/Lua 引擎可按字体文件名加载，"
                    "不需要 NFSS 的 `\\DeclareFontFamily`/`\\DeclareFontShape`。"
                ),
                commands=("\\setCJKmainfont{<含该字的中文字体>}",),
                commands_en=("\\setCJKmainfont{<CJK font containing the glyph>}",),
                kind="missing_glyph",
                text_en=(
                    f"The current CJK font `{font}` has no glyph for `{char}`"
                    f"{f' (U+{codepoint})' if codepoint else ''}. Switch to a CJK font "
                    "containing it via `\\setCJKmainfont`/`\\setCJKsansfont`, or add a "
                    "FallBack font. Xe/Lua engines can load a font by file name "
                    "directly; NFSS `\\DeclareFontFamily`/`\\DeclareFontShape` are "
                    "not needed."
                ),
            )
        # pdfLaTeX / 空 / 未知上下文：保留两步排查与换引擎建议；
        # 编译命令不写死单一引擎，给出 XeLaTeX/LuaLaTeX 两个可选。
        return Hint(
            text=(
                f"字体 `{font}` 没有中文字形 `{char}`{codepoint_label}。分两步排查："
                "① 若还在 pdfLaTeX，中文不能交给默认拉丁字体，改用 XeLaTeX/LuaLaTeX + ctex"
                "（或 xeCJK）；② 已在 Xe/Lua + ctex/xeCJK 时，症结是当前 CJK 字体不含该字："
                "用 `\\setCJKmainfont`/`\\setCJKsansfont` 换含该字的中文字体，或补 FallBack 字体。"
                "xeCJK 可直接按字体文件名加载（如 `\\setCJKmainfont{ukai.ttc}`），"
                "不需要 NFSS 的 `\\DeclareFontFamily`/`\\DeclareFontShape`。"
            ),
            commands=("\\usepackage{ctex}", "XeLaTeX/LuaLaTeX <主文件>.tex"),
            commands_en=("\\usepackage{ctex}", "XeLaTeX/LuaLaTeX <main file>.tex"),
            kind="missing_glyph",
            text_en=(
                f"Font `{font}` has no glyph for CJK character `{char}`"
                f"{f' (U+{codepoint})' if codepoint else ''}. Check in two "
                "steps: ① if still on pdfLaTeX, Chinese must not be typeset with the "
                "default Latin font—switch to XeLaTeX/LuaLaTeX with ctex (or xeCJK); "
                "② if already on Xe/Lua + ctex/xeCJK, the current CJK font lacks the "
                "character: switch to a CJK font containing it via `\\setCJKmainfont`/"
                "`\\setCJKsansfont`, or add a FallBack font. xeCJK can load a font by "
                "file name directly (e.g. `\\setCJKmainfont{ukai.ttc}`); NFSS "
                "`\\DeclareFontFamily`/`\\DeclareFontShape` declarations are not needed."
            ),
        )
    return Hint(
        text=(
            f"当前字体里没有字符 `{char}`。换用包含该字形的字体，"
            "或用 \\newunicodechar 显式映射；注意 \\newunicodechar 只把字符映射到已有 "
            "LaTeX 写法，不会凭空造字形，若字体本身缺该字形仍要换字体。"
        ),
        commands=("\\usepackage{newunicodechar}", f"\\newunicodechar{{{char}}}{{<LaTeX 写法>}}"),
        commands_en=(
            "\\usepackage{newunicodechar}",
            f"\\newunicodechar{{{char}}}{{<LaTeX command>}}",
        ),
        kind="missing_glyph",
        text_en=(
            f"Current font has no glyph for `{char}`: use a font that contains it, "
            "or map it explicitly with \\newunicodechar. Note that \\newunicodechar "
            "only maps the character to an existing LaTeX construct; it does not "
            "create a glyph—if the font itself lacks it, switch fonts."
        ),
    )


def _match_missing_bbl(text: str) -> Any:
    return _MISSING_BBL_RE.search(text) or _RERUN_BIBLATEX_RE.search(text)


def _build_missing_bbl(match: Any) -> Hint:
    has_job = match.lastindex is not None and match.group(1) is not None
    job = match.group(1) if has_job else "<jobname>"
    if has_job:
        zh_opening = f"未找到 `{job}.bbl`："
        en_opening = f"`{job}.bbl` is missing: "
    else:
        # `Please (re)run Biber` 分支：日志里没有 .bbl 文件名，只说后端尚未完成，
        # 不声称 .bbl 缺失，也不残留 `<jobname>.bbl`。
        zh_opening = ""
        en_opening = ""
    return Hint(
        text=(
            f"{zh_opening}文献后端还没有成功跑过。"
            "biblatex + biber 流程：导言区用 `\\addbibresource{refs.bib}`"
            "（必须带 `.bib` 扩展名），编译顺序 latex → biber `<jobname>` → latex（两轮），走 `.bcf`；"
            "传统 BibTeX 流程：用 `\\bibliography{refs}`（不带 `.bib`）与 "
            "`\\bibliographystyle{...}`，编译顺序 latex → bibtex `<jobname>` → latex。"
            "先确认文档声明的 backend 与实际执行的命令一致。"
        ),
        commands=("biber <jobname>", "bibtex <jobname>"),
        kind="missing_bbl",
        text_en=(
            f"{en_opening}The bibliography backend has not completed successfully. "
            "biblatex + biber: declare `\\addbibresource{refs.bib}` "
            "(extension required), then latex → biber `<jobname>` → latex (two passes) "
            "via the `.bcf`; traditional BibTeX: use `\\bibliography{refs}` (no `.bib`) "
            "and `\\bibliographystyle{...}`, then latex → bibtex `<jobname>` → latex. "
            "First confirm the declared backend matches the command you run."
        ),
    )


def _match_undefined_citation(text: str) -> Any:
    return _UNDEFINED_CITATION_RE.search(text) or _UNDEFINED_CITATION_DISPLAY_RE.search(text)


def _build_undefined_citation(match: Any) -> Hint:
    return Hint(
        text=(
            f"引用键 `{match.group(1)}` 未定义：检查 .bib 里是否存在该键，"
            "并确认 biber/bibtex 已经成功运行。biblatex 的 `bibwarn` 默认开启，"
            "同一条文献告警可能在 `.blg` 与 `.log` 里各出现一次，不是两个独立问题；"
            "先看 `.blg` 里后端的原始消息，按三级定位：① 打不开 `.bst` 样式文件；"
            "② 打不开 `.bib` 数据库；③ 条目键找不到。biblatex 下未定义引用在 PDF 里"
            "显示为粗体引用键（经典 BibTeX 显示 `[?]`），别误以为没报错。"
            "条目找不到还要查 `.bib` 是否被 `filecontents` 以非覆盖方式写成了陈旧文件，"
            "或工程目录残留旧 `.bib`。若日志出现 `No file <jobname>.bbl`，"
            "说明文献后端还没跑过：biber 路线用 `\\addbibresource{refs.bib}`"
            "（带 `.bib`）+ `biber <jobname>`；bibtex 路线用 `\\bibliography{refs}`"
            "（不带 `.bib`）+ `bibtex <jobname>`；然后再编译两轮。"
        ),
        commands=("biber <jobname>", "bibtex <jobname>"),
        kind="undefined_citation",
        brief=f"引用键 `{match.group(1)}` 未定义：先看 `.blg` 的后端原始消息，再核对 .bib 键名。",
        brief_en=(
            f"Citation key `{match.group(1)}` is undefined: check the backend message in "
            "`.blg` first, then verify the key in the .bib file."
        ),
        text_en=(
            f"Citation key `{match.group(1)}` is undefined: check .bib for that key "
            "and confirm biber/bibtex ran successfully. biblatex's `bibwarn` is on by "
            "default, so the same bibliography warning may appear once in `.blg` and "
            "once in `.log`—they are not two independent issues; check the original "
            "backend message in `.blg` first, in three levels: ① cannot open the "
            "`.bst` style; ② cannot open the `.bib` database; ③ entry key not found. "
            "Under biblatex an undefined citation shows as a bold key in the PDF "
            "(classic BibTeX shows `[?]`), so do not mistake it for “no error”. If "
            "the entry is missing, also check whether a stale `.bib` was written "
            "without overwrite by `filecontents`, or an old `.bib` lingers in the "
            "project directory. If the log shows `No file <jobname>.bbl`, the "
            "bibliography backend has not run yet: biber route uses "
            "`\\addbibresource{refs.bib}` (with `.bib`) + `biber <jobname>`; BibTeX "
            "route uses `\\bibliography{refs}` (no `.bib`) + `bibtex <jobname>`; "
            "then compile two more passes."
        ),
    )


def _match_undefined_reference(text: str) -> Any:
    return _UNDEFINED_REFERENCE_RE.search(text) or _UNDEFINED_REFERENCE_DISPLAY_RE.search(text)


def _build_undefined_reference(match: Any) -> Hint:
    return Hint(
        text=(f"交叉引用 `{match.group(1)}` 未定义：确认 \\label 拼写，并用当前引擎再编译一轮让 .aux 收敛。"),
        commands=("<引擎> <主文件>.tex  # 用当前引擎再跑一轮",),
        commands_en=("<engine> <main file>.tex",),
        kind="undefined_reference",
        text_en=(
            f"Cross-reference `{match.group(1)}` is undefined: check \\label spelling "
            "and rerun with the current engine to converge .aux."
        ),
    )


def _match_undefined_environment(text: str) -> Any:
    return _UNDEFINED_ENV_RE.search(text)


def _build_undefined_environment(match: Any) -> Hint:
    return Hint(
        text=(f"环境 `{match.group(1)}` 未定义：确认提供该环境的宏包已 \\usepackage，或检查环境名拼写/大小写。"),
        kind="undefined_environment",
        text_en=(
            f"Environment `{match.group(1)}` is undefined: load the package that provides it, "
            "or check the environment name/case."
        ),
    )


def _match_missing_bib(text: str) -> Any:
    return _BIB_DB_RE.search(text)


def _build_missing_bib(match: Any) -> Hint:
    name = match.group(1)
    stem = name[:-4] if name.lower().endswith(".bib") else name
    return Hint(
        text=(
            f"找不到文献数据库 `{name}`：确认 .bib 路径（相对主文件目录）与文件名大小写。"
            "注意两条命令的写法差异：biblatex 的 `\\addbibresource{refs.bib}` "
            "必须带 `.bib` 扩展名；传统 BibTeX 的 `\\bibliography{refs}` 不带 `.bib`。"
        ),
        commands=(f"kpsewhich {stem}.bib",),
        kind="missing_bib",
        text_en=(
            f"Bibliography database `{name}` not found: check the .bib path (relative "
            "to the main file) and filename case. Note the syntax difference: biblatex's "
            "`\\addbibresource{refs.bib}` must include the `.bib` extension; legacy "
            "BibTeX's `\\bibliography{refs}` must not."
        ),
    )


def _match_biber_case(text: str) -> str | None:
    """大小写键名冲突的子串匹配（工具作用域由 :func:`_match_biber_case_scoped` 把关）。"""
    return "case mismatch" if "case mismatch" in text.lower() else None


def _match_biber_case_scoped(text: str, tool_name: str) -> str | None:
    """biber 专项：显式 latex 日志不得套用；未指定工具时按文本放行（F6）。"""
    if tool_name:
        name = tool_name.lower()
        if not name.startswith("biber"):
            return None
    return _match_biber_case(text)


def _build_biber_case_mismatch(_match: str) -> Hint:
    return Hint(
        text=(
            "biber 对引用键与数据源条目键区分大小写：逐字符核对 `\\cite{Key}` 与 "
            ".bib 里的 `@type{Key,` 是否完全一致（含大小写）。注意 entrytype 与 "
            "fieldname 在输入侧不区分大小写；数据模型之外的字段默认被忽略，"
            "需要报告时加 `--validate-datamodel`。"
        ),
        kind="biber_key_case",
        text_en=(
            "Biber is case-sensitive for citation keys and data-source entry keys: "
            "compare `\\cite{Key}` against `@type{Key,` in the .bib character by "
            "character, including case. Entrytype and fieldname are case-insensitive "
            "on input; fields outside the data model are ignored by default—run with "
            "`--validate-datamodel` to report them."
        ),
    )


def _build_float_overflow(_match: bool) -> Hint:
    return Hint(
        text="浮动体太多：在章节间加 \\clearpage，或使用 [H] 位置与 float 宏包。",
        commands=("\\usepackage{float}", "\\clearpage"),
        kind="float_overflow",
        text_en="Too many unprocessed floats: add \\clearpage between sections, or use the float package with [H].",
    )


_CAPACITY_ADVICE_ZH: dict[str, str] = {
    "input stack size": (
        "TeX 输入栈耗尽：循环点可能是自写宏/环境无限递归（如 `\\def\\a{\\a\\a}`），"
        "也可能在宏包/书目样式展开链里（如 hyperref 与书目样式互相包裹链接命令）。"
        "顺着日志 `->` 展开行定位进入循环的宏包/样式，先断开循环；"
        "不要去调大容量，递归栈溢出与内存大小无关。"
    ),
    "main memory size": (
        "TeX 主内存耗尽：常见于超长宏、过多 `\\index`/`\\glossary` 条目、"
        "复杂表格/浮动体堆积，以及 pgfplots 大数据量图形。pgfplots 场景优先外置化"
        "（每幅图单独编译、主任务只插图）、降低点数、插 `\\clearpage` 释放浮动体；"
        "确认不是结构问题后再考虑调高容量。"
    ),
    "pool size": (
        "TeX 字符串池耗尽：标签/命令名过多过长，或 `\\newenvironment` 等定义漏写右花括号。"
        "先检查未闭合的定义与过长的标签名。"
    ),
    "save size": "TeX 保存栈耗尽：环境/宏嵌套过深。梳理嵌套层级，把深嵌套拆成多个环境或宏。",
    "buffer size": (
        "TeX 缓冲区耗尽：`\\caption`/章节可选参数/目录条目文本过长。缩短这些参数文本，或把长文本移到短参数 + 长正文。"
    ),
    "hash size": "TeX 哈希表耗尽：命令名或标签数量过多。清理不再使用的命令与标签。",
}

_CAPACITY_ADVICE_EN: dict[str, str] = {
    "input stack size": (
        "TeX input stack exhausted: the loop may be an infinite self-recursive "
        "macro/environment (e.g. `\\def\\a{\\a\\a}`), or it may live in a package/"
        "bibliography-style expansion chain (e.g. hyperref and a style wrapping link "
        "commands into each other). Follow the `->` expansion lines in the log to "
        "locate the looping package/style and break the cycle first; do not raise "
        "capacity—stack overflow has nothing to do with memory size."
    ),
    "main memory size": (
        "TeX main memory exhausted: often very long macros, too many `\\index`/"
        "`\\glossary` entries, piled-up complex tables/floats, or large pgfplots "
        "graphics. For pgfplots, prefer externalization (compile each plot as a "
        "separate job and include it in the main task), reduce data points, and insert "
        "`\\clearpage` to release floats; only consider raising capacity after "
        "ruling out structural causes."
    ),
    "pool size": (
        "TeX string pool exhausted: too many/too long labels or command names, or a "
        "missing closing brace in a `\\newenvironment` definition. Check unclosed "
        "definitions and over-long labels first."
    ),
    "save size": "TeX save stack exhausted: environments/macros are nested too deeply. Flatten the nesting into multiple environments or macros.",
    "buffer size": (
        "TeX buffer exhausted: `\\caption`, section optional arguments, or TOC entries "
        "are too long. Shorten these argument texts, or move long text out of the "
        "short argument into the body."
    ),
    "hash size": "TeX hash table exhausted: too many command names or labels. Clean up unused commands and labels.",
}

_CAPACITY_TAIL_ZH = (
    "确认不是结构问题后再调容量：TeX Live 编辑 `kpsewhich texmf.cnf` 指向的文件后 "
    "执行 `fmtutil-sys --all`；MiKTeX 用 `initexmf --edit-config-file=texmf.cnf` 修改后 "
    "`initexmf --dump`。"
)
_CAPACITY_TAIL_EN = (
    "Only after ruling out structural causes, raise the capacity: on TeX Live, edit the "
    "file pointed to by `kpsewhich texmf.cnf` and run `fmtutil-sys --all`; on MiKTeX, "
    "edit with `initexmf --edit-config-file=texmf.cnf` and run `initexmf --dump`."
)


def _match_capacity(text: str) -> Any:
    return _CAPACITY_RE.search(text)


def _build_capacity(match: Any) -> Hint:
    bracket = match.group(1).strip()
    # ``input stack size=5000`` → 子类型名取等号之前的部分。
    subtype = bracket.split("=", 1)[0].strip().lower()
    advice_zh = _CAPACITY_ADVICE_ZH.get(subtype)
    advice_en = _CAPACITY_ADVICE_EN.get(subtype)
    if advice_zh is None:
        advice_zh = "TeX 容量耗尽：先排查无限递归、超长表格/浮动体与未闭合的宏定义；确认不是结构问题后再调高容量。"
        advice_en = (
            "TeX capacity exhausted: look for infinite recursion, oversized "
            "tables/floats, and unclosed macro definitions; only then raise capacity."
        )
    return Hint(
        text=f"{advice_zh}{_CAPACITY_TAIL_ZH}",
        commands=(
            "kpsewhich texmf.cnf",
            "fmtutil-sys --all",
            "initexmf --edit-config-file=texmf.cnf",
            "initexmf --dump",
        ),
        kind="capacity",
        text_en=f"{advice_en}{_CAPACITY_TAIL_EN}",
    )


def _build_no_output(_match: bool) -> Hint:
    return Hint(
        text=(
            "没有输出任何页面：检查 `\\documentclass`/`\\begin{document}` 是否完整；"
            "空文档本来就不产生页面；可删除陈旧的 `.aux` 后重跑一轮。"
            "注意 `\\includeonly` 是正常配置，不是本错误的成因。"
        ),
        kind="no_output",
        text_en=(
            "No pages were produced: check that `\\documentclass`/"
            "`\\begin{document}` are complete; an empty document produces no pages "
            "by design; delete stale `.aux` files and rerun. Note that `\\includeonly` "
            "is a normal setting and is not the cause of this error."
        ),
    )


def _match_runaway(text: str) -> tuple[str | None, str | None] | None:
    scan = _RUNAWAY_SCAN_RE.search(text)
    if scan:
        return ("scan", scan.group(1))
    if "Runaway argument" in text:
        return ("argument", None)
    return None


def _build_runaway(context: tuple[str | None, str | None]) -> Hint:
    _kind, command = context
    if command:
        text = (
            f"参数没有闭合就遇到文件结束（EOF）：报错行号是 TeX 耗尽空间的位置，"
            "常常不可信；真正线索是 `Runaway argument?` 后面被吞掉的文本。"
            f"从命令 `{command}` 的参数向前回溯未配对的 `{{}}` 或未闭合环境。"
        )
        text_en = (
            "The argument reached EOF without closing: the error line number is where "
            "TeX ran out of space and is often unreliable; the real clue is the text "
            f"swallowed after `Runaway argument?`. Walk back from `{command}`'s "
            "argument for an unmatched `{}` or an unclosed environment."
        )
    else:
        text = (
            "括号/环境没有闭合：报错行号常不可信，真正线索是 `Runaway argument?` "
            "后面被吞掉的文本；从报错行往前找最近的未配对 `{}` 或 `\\begin/\\end`。"
        )
        text_en = (
            "Unbalanced braces/environment: the line number is often unreliable; the "
            "real clue is the text swallowed after `Runaway argument?`. Look backwards "
            "from the error line for the nearest unmatched `{}` or `\\begin/\\end`."
        )
    return Hint(text=text, kind="runaway", text_en=text_en)


def _build_math_mode(_match: bool) -> Hint:
    return Hint(
        text="数学模式不匹配：检查漏写的 $、\\text 中的特殊字符，或 \\ensuremath 的使用。",
        kind="math_mode",
        text_en="Math mode mismatch: check for a missing $, special characters inside \\text, or \\ensuremath usage.",
    )


def _build_fatal(_match: bool) -> Hint:
    return Hint(
        text="编译被致命错误中断：先修复日志里 Emergency stop 上方的第一条错误。",
        kind="fatal",
        text_en="Compilation was stopped by a fatal error: fix the first error above Emergency stop.",
    )


def _match_undefined_control(text: str) -> str | None:
    # ``Missing \begin{document}`` 是更具体的首条 LaTeX 错误，优先于未定义命令兜底。
    if _MISSING_BEGIN_DOC_RE.search(text):
        return None
    return text if _UNDEFINED_CONTROL_RE.search(text) else None


def _skip_definition_groups(text: str, start: int) -> int:
    """跳过定义构造命令名之后紧随的可选 ``[...]`` 与平衡 ``{...}`` 分组。

    定义体（如 ``\\def\\foo{\\textbf{x}}`` 里的 ``{\\textbf{x}}``）属于构造内部，
    其中的控制序列不能当成“构造之后另有未定义命令”。这里只做括号配平、不解析宏体
    语义；遇未闭合分组即停在当前位置，剩余文本交给常规控制序列提取。
    """
    i = start
    n = len(text)
    while i < n:
        while i < n and text[i] in " \t":
            i += 1
        if i >= n or text[i] not in "[{":
            break
        opener = text[i]
        closer = "]" if opener == "[" else "}"
        depth = 0
        j = i
        closed = False
        while j < n:
            if text[j] == "\\":
                j += 2
                continue
            if text[j] == opener:
                depth += 1
            elif text[j] == closer:
                depth -= 1
                if depth == 0:
                    closed = True
                    j += 1
                    break
            j += 1
        if not closed:
            break
        i = j
    return i


def _build_definition_control(match: re.Match[str]) -> Hint:
    """定义命令行（``\\newcommand``/``\\def`` 等）上的未定义序列提示。

    被定义的裸名称才是线索；包装命令不报成未定义，也不给 ``<name>.sty`` 安装命令。
    """
    wrapper = match.group(1)
    starred = bool(match.group(2))
    name = match.group(3) or match.group(4) or ""
    if wrapper == "def":
        example = f"\\def\\{name}{{...}}"
    elif wrapper == "newenvironment":
        example = f"\\newenvironment{{\\{name}}}{{...}}{{...}}"
    else:
        star = "*" if starred else ""
        example = f"\\{wrapper}{star}{{\\{name}}}{{...}}"
    is_env = wrapper == "newenvironment"
    what = "环境" if is_env else "宏"
    what_en = "environment" if is_env else "macro"
    return Hint(
        text=(
            f"该行看起来是在定义{what} `\\{name}`：包装命令 `\\{wrapper}` 本身不是未定义命令，"
            "也不需要安装对应 .sty。检查定义语法（命令名要带反斜杠、参数与花括号是否闭合）；"
            f"修法示例：`{example}`。"
        ),
        commands=(f'grep -R "\\\\{name}" *.tex',),
        kind="undefined_control",
        text_en=(
            f"This line looks like a definition of the {what_en} `\\{name}`; the wrapper "
            f"command `\\{wrapper}` itself is not undefined and no .sty package needs "
            f"installing. Check the definition syntax (the command name needs a leading "
            f"backslash; arguments and braces must close). Example fix: `{example}`."
        ),
    )


def _build_undefined_control(text: str) -> Hint:
    # 真实日志是 ``! Undefined control sequence.`` 后跟 ``l.5 ... \badcmd``，
    # 且 l.N 行可能折行：命令在下一行。取 l.N 行 + 紧随一行拼成窗口，
    # 优先取 l.N 行内最后一个控制序列；该行没有则取续行第一个；仍无则回退全文。
    lines = text.splitlines()
    l_index = next((i for i, line in enumerate(lines) if re.search(r"l\.?\d+", line)), None)
    main_line = lines[l_index] if l_index is not None else ""
    cont_line = lines[l_index + 1] if l_index is not None and l_index + 1 < len(lines) else ""

    name: str | None = None
    if l_index is not None:
        def_match = _DEF_COMMAND_RE.search(main_line)
        def_line = main_line
        if def_match is None and cont_line:
            def_match = _DEF_COMMAND_RE.search(cont_line)
            def_line = cont_line
        if def_match is not None:
            # 切掉命令名与紧随的参数/定义体分组后，剩余文本若还有控制序列，那才是
            # 真正未定义命令；只有剩余为空时才报定义语法笔误（避免把 \badcmd 误判成
            # 被定义的宏名）。
            end = _skip_definition_groups(def_line, def_match.end())
            leftover = _CONTROL_NAME_RE.findall(def_line[end:])
            if leftover:
                name = leftover[-1]
            else:
                return _build_definition_control(def_match)

    if name is None:
        if l_index is not None:
            main_controls = _CONTROL_NAME_RE.findall(main_line)
            if main_controls:
                name = main_controls[-1]
            elif cont_line:
                continuation = _CONTROL_NAME_RE.findall(cont_line)
                if continuation:
                    name = continuation[0]
    if name is None:
        controls = _CONTROL_NAME_RE.findall(text)
        name = controls[-1] if controls else None
    if name is None:
        return Hint(
            text="未定义命令：检查拼写/大小写；若是宏包提供的命令，确认对应 \\usepackage 已加载。",
            kind="undefined_control",
            text_en="Undefined command: check spelling/case; if a package provides it, confirm the matching \\usepackage is loaded.",
        )
    return Hint(
        text=(f"未定义命令 `\\{name}`：检查拼写/大小写；若是宏包提供的命令，确认对应 \\usepackage 已加载。"),
        commands=(
            f'grep -R "\\\\{name}" *.tex',
            f"tlmgr search --global --file {name}.sty",
        ),
        kind="undefined_control",
        text_en=(
            f"Undefined command `\\{name}`: check spelling/case; if a package provides it, "
            "confirm the matching \\usepackage is loaded."
        ),
    )


def _match_end_mismatch(text: str) -> Any:
    return _END_MISMATCH_RE.search(text)


def _build_end_mismatch(_match: Any) -> Hint:
    return Hint(
        text=("\\begin{document} 被错误的 \\end{...} 提前关闭：检查环境嵌套，确保每个 \\begin 都有同名 \\end。"),
        kind="end_mismatch",
        text_en="\\begin{document} was ended by a wrong \\end{...}: check environment nesting so every \\begin has a matching \\end.",
    )


def _match_option_clash(text: str) -> Any:
    stripped = text.lstrip().lower()
    # 散文里提到 “Option clash ...” 不算日志错误；要求处于错误行语境。
    if not (stripped.startswith("option clash") or stripped.startswith("latex error") or stripped.startswith("!")):
        return None
    return _OPTION_CLASH_RE.search(text)


def _build_option_clash(match: Any) -> Hint:
    pkg = match.group(1)
    return Hint(
        text=(
            f"宏包 `{pkg}` 的选项冲突：它被加载了两次且选项不同。先读错误文本里的两组选项"
            "（`already been loaded with options: [...]` 与 `attempt to load with "
            "options [...]`）。修法任选：① 合并为单次 `\\usepackage`；"
            f"② 第一次加载前用 `\\PassOptionsToPackage{{<选项>}}{{{pkg}}}` 预埋；"
            "③ 把冲突选项提升为 `\\documentclass[...,<选项>]{<文档类>}` 全局选项。"
            "注意先加载者可能是被其他宏包间接拉入的。"
        ),
        commands=(f"\\PassOptionsToPackage{{<选项>}}{{{pkg}}}",),
        commands_en=(f"\\PassOptionsToPackage{{<option>}}{{{pkg}}}",),
        kind="option_clash",
        text_en=(
            f"Option clash for package `{pkg}`: it is loaded twice with different options. "
            "First read the two option sets in the error text (`already been loaded with "
            "options: [...]` and `attempt to load with options [...]`). Fix by one of: "
            "① merge into a single `\\usepackage`; ② preload the option with "
            f"`\\PassOptionsToPackage{{<option>}}{{{pkg}}}` before the first load; "
            "③ promote the conflicting option to a `\\documentclass[...,<option>]{<class>}` "
            "global option. The first loader may have been pulled in indirectly by another "
            "package."
        ),
    )


def _match_double_script(text: str) -> Any:
    stripped = text.lstrip().lower()
    # 散文里提到 “Double subscript” 不算日志错误；要求错误串处于行首。
    if not (stripped.startswith("double ") or stripped.startswith("! double")):
        return None
    return _DOUBLE_SCRIPT_RE.search(text)


def _build_double_script(match: Any) -> Hint:
    what = match.group(1).lower()
    if what == "subscript":
        text = (
            "下标重复：`x_1_2` 这种写法非法。先分清分组意图：嵌套下标写 "
            "`x_{n_i}`；整体（外层）带下标写 `${x_n}_i$`，两者排版层级不同。"
            "多字符下标加花括号，上下标并存写成 `x_{1}^{2}`。"
            "重音原子特例：若子公式只含重音原子（如 `\\hat{a}` 及其下标），外层花括号会被 "
            "TeX 剥掉，`${\\hat{a}_b}_c$` 仍报 Double subscript；在重音前插一个空组，"
            "写成 `${{}\\hat{a}_b}_c$`，再加更多花括号也无效。"
        )
        text_en = (
            "Double subscript: `x_1_2` is illegal. First decide the grouping intent: "
            "a nested subscript is `x_{n_i}`; a subscript on the whole group is "
            "`${x_n}_i$`—they typeset at different levels. Wrap multi-character "
            "subscripts in braces, and combine sub/superscripts as `x_{1}^{2}`. "
            "Accent-atom caveat: if a subformula only contains an accent atom (e.g. "
            "`\\hat{a}` with its subscript), TeX strips the outer braces, so "
            "`${\\hat{a}_b}_c$` still errors. Insert an empty group before the accent: "
            "`${{}\\hat{a}_b}_c$`; more braces do not help."
        )
    else:
        text = (
            "上标重复：`x^2^3` 这种写法非法。多字符上标加花括号，"
            "如 `x^{2,3}`；上下标并存写成 `x^{2}_{3}`；整体分组带上标同样用 `${x^2}^3$`。"
        )
        text_en = (
            "Double superscript: `x^2^3` is illegal. Wrap multi-character superscripts "
            "in braces, e.g. `x^{2,3}`, and combine sub/superscripts as `x^{2}_{3}`; "
            "a superscript on the whole group uses `${x^2}^3$`."
        )
    return Hint(text=text, kind="double_script", text_en=text_en)


def _build_invalid_utf8(_match: bool) -> Hint:
    return Hint(
        text=(
            "源码不是有效 UTF-8：把报错文件另存为 UTF-8（无 BOM），并检查是否混入 GBK 字符。"
            "`file --mime-encoding` 是 Unix/Linux 工具；Windows 上可在编辑器（VS Code 等）"
            "状态栏查看文件编码，或用 PowerShell 读取字节判断。"
        ),
        commands=("file --mime-encoding <主文件>",),
        commands_en=("file --mime-encoding <main file>",),
        kind="invalid_utf8",
        text_en=(
            "Source is not valid UTF-8: save the offending file as UTF-8 (no BOM) and check for "
            "mixed GBK characters. `file --mime-encoding` is a Unix/Linux tool; on Windows check "
            "the encoding in your editor (e.g. VS Code status bar) or inspect the bytes with PowerShell."
        ),
    )


def _build_alignment_tab(_match: bool) -> Hint:
    return Hint(
        text="表格列数不匹配：检查每行 `&` 数量是否与列格式（如 `lcr`）一致。",
        kind="alignment_tab",
        text_en="Column count mismatch: check that each row has the same number of `&` as the column spec (e.g. lcr).",
    )


def _match_missing_number(text: str) -> str | None:
    if "Missing number, treated as zero" not in text:
        return None
    token_match = _MISSING_NUMBER_TOKEN_RE.search(text)
    return token_match.group(1) if token_match else " "


def _build_missing_number(token: str) -> Hint:
    token = token.strip()
    zh_part = f"（待读入 token：`{token}`）" if token else ""
    en_part = f" (token to be read: `{token}`)" if token else ""
    return Hint(
        text=(
            f"长度/数字参数缺失{zh_part}：检查 \\vspace、\\hspace、\\rule、"
            "\\includegraphics[width=...] 等是否漏写数字或单位。"
        ),
        kind="missing_number",
        text_en=(
            f"Missing length/number argument{en_part}: check \\vspace, \\hspace, "
            "\\rule, and \\includegraphics[width=...] for a missing number or unit."
        ),
    )


def _build_missing_item(_match: bool) -> Hint:
    return Hint(
        text=(
            "列表环境里缺少 \\item：在 itemize/enumerate 的每个条目开头补 \\item。"
            "另外，列表被放进 \\fbox/\\mbox/\\makebox、或 enumerate 被放进 tabular "
            "单元格也会触发此错；此时补 \\item 无效，应把列表移出盒子/单元格。"
        ),
        kind="missing_item",
        text_en=(
            "Missing \\item in a list: add \\item at the start of each "
            "itemize/enumerate entry. A list placed inside \\fbox/\\mbox/\\makebox, "
            "or an enumerate inside a tabular cell, also triggers this; adding \\item "
            "will not help—move the list out of the box/cell."
        ),
    )


def _match_missing_begin_document(text: str) -> Any:
    stripped = text.lstrip().lower()
    # 散文里提到 “Missing \begin{document}” 不算日志错误；要求处于错误行语境。
    if not (stripped.startswith("missing \\begin") or stripped.startswith("latex error") or stripped.startswith("!")):
        return None
    return _MISSING_BEGIN_DOC_RE.search(text)


def _build_missing_begin_document(_match: Any) -> Hint:
    return Hint(
        text=(
            "正文或排版命令出现在 `\\begin{document}` 之前。按可能性检查："
            "① `\\documentclass` 之后直接写了正文、`\\maketitle`、`\\section`；"
            "② 文件开头有不可见字符或 UTF-8 BOM（用“UTF-8 无 BOM”重新保存）；"
            "③ 误用 `\\endinput`、或把正文写进了导言区；"
            "④ 导言区 `\\newcommand`/`\\def`/`\\newenvironment` 定义笔误"
            "（命令名漏写反斜杠，如写成 `\\newcommand{dice}...`），命令名被当成正文排版。"
            "`\\includeonly` 不是本错误的原因。"
        ),
        kind="missing_begin_document",
        text_en=(
            "Body text or typesetting commands appear before `\\begin{document}`. "
            "Check in order: ① body/`\\maketitle`/`\\section` written right after "
            "`\\documentclass`; ② an invisible character or UTF-8 BOM at file start "
            "(re-save as UTF-8 without BOM); ③ a stray `\\endinput`, or body text "
            "placed in the preamble; ④ a typo in a preamble `\\newcommand`/`\\def`/"
            "`\\newenvironment` definition (e.g. the command name missing its backslash, "
            "as in `\\newcommand{dice}...`), so the name is typeset as body text. "
            "`\\includeonly` is not the cause of this error."
        ),
    )


def _match_extra_close_brace(text: str) -> Any:
    stripped = text.lstrip().lower()
    # 散文里提到 “Too many }'s” 不算日志错误；要求错误串处于行首。
    if not (stripped.startswith("too many") or stripped.startswith("! too many")):
        return None
    return _EXTRA_CLOSE_BRACE_RE.search(text)


def _build_extra_close_brace(_match: Any) -> Hint:
    return Hint(
        text=(
            "右花括号比左花括号多。用编辑器括号匹配从报错行向前回溯；"
            "常见于 `\\section{a}}`、`\\textbf{a}}`、行尾 `\\\\` 后多打了一个 `}`；"
            "`\\verb` 里的括号不参与配对。"
        ),
        kind="extra_close_brace",
        text_en=(
            "More closing braces than opening ones. Use your editor's brace matching "
            "to walk backwards from the error line; common cases are `\\section{a}}`, "
            "`\\textbf{a}}`, or an extra `}` after a line-ending `\\\\`. Braces inside "
            "`\\verb` do not participate in pairing."
        ),
    )


def _match_missing_right(text: str) -> Any:
    return _MISSING_RIGHT_RE.search(text)


def _build_missing_right(_match: Any) -> Hint:
    return Hint(
        text=(
            "`\\left` 必须与 `\\right` 成对：补 `\\right)`/`\\right]`/`\\right.`。"
            "其中 `.` 表示该侧无可见围栏，是合法的隐形定界符"
            "（如单侧大括号 `\\left\\{ ... \\right.`），不是漏写标点，不要删掉。"
            "跨行或跨表格单元格时，把 `\\left...\\right` 放在同一组内，"
            "或改用 `\\bigl...\\bigr` 手动定尺寸。"
        ),
        kind="missing_delimiter",
        text_en=(
            "`\\left` must pair with `\\right`: add the matching "
            "`\\right)`/`\\right]`/`\\right.`. The `.` is a legal invisible delimiter "
            "meaning no fence on that side (e.g. a single brace `\\left\\{ ... \\right.`); "
            "it is not a missing punctuation mark—do not delete it. If it spans lines or "
            "table cells, keep `\\left...\\right` in the same group, or use manually "
            "sized `\\bigl...\\bigr`."
        ),
    )


def _match_bad_math_delimiter(text: str) -> Any:
    return _BAD_MATH_DELIMITER_RE.search(text)


def _build_bad_math_delimiter(_match: Any) -> Hint:
    return Hint(
        text=(
            "数学定界符交叉/嵌套：`$...$`、`\\(...\\)`、`\\[...\\]` 不能互相包含。"
            "先修首条 `Display math should end with $$`，下游的 delimiter 报错多为连锁，"
            "不要单独改。"
        ),
        kind="math_delimiter",
        text_en=(
            "Math delimiters are crossed or nested: `$...$`, `\\(...\\)`, and "
            "`\\[...\\]` cannot contain one another. Fix the first "
            "`Display math should end with $$`; later delimiter errors are mostly "
            "cascades—do not fix them in isolation."
        ),
    )


def _match_misplaced_noalign(text: str) -> Any:
    return _MISPLACED_NOALIGN_RE.search(text)


def _build_misplaced_noalign(_match: Any) -> Hint:
    return Hint(
        text=(
            "`\\hline`/`\\toprule` 只能出现在表格行之间：放在某行 `\\\\` 之后，"
            "或 `\\begin{tabular}` 后、第一行之前；表格外或单元格内使用会报此错。"
        ),
        kind="misplaced_noalign",
        text_en=(
            "`\\hline`/`\\toprule` may only appear between table rows: place it after "
            "a row's `\\\\`, or after `\\begin{tabular}` before the first row. Using it "
            "outside the table or inside a cell triggers this error."
        ),
    )


def _match_illegal_unit(text: str) -> str | None:
    if not _ILLEGAL_UNIT_RE.search(text):
        return None
    token_match = _MISSING_NUMBER_TOKEN_RE.search(text)
    return token_match.group(1) if token_match else " "


def _build_illegal_unit(token: str) -> Hint:
    token = token.strip()
    zh_part = f" 报错里待读入的字符是 `{token}`，即拼错的单位首字母。" if token else ""
    en_part = f" The pending character is `{token}`, the first letter of the misspelled unit." if token else ""
    return Hint(
        text=(
            "长度缺单位或单位拼错：`\\vspace{2}` 会被当成 2pt；"
            "写 `2pt/2mm/2cm/2em/2ex`。"
            "报错里 `<to be read again>` 后面的字符就是拼错的单位首字母。" + zh_part
        ),
        kind="illegal_unit",
        text_en=(
            "A length is missing its unit or the unit is misspelled: `\\vspace{2}` is "
            "treated as 2pt; write `2pt/2mm/2cm/2em/2ex`. The character after "
            "`<to be read again>` is the first letter of the misspelled unit." + en_part
        ),
    )


def _match_command_redefined(text: str) -> Any:
    return _COMMAND_REDEFINED_RE.search(text)


def _build_command_redefined(match: Any) -> Hint:
    name = match.group(1)
    return Hint(
        text=(
            f"命令 `{name}` 已被定义（来自宏包、文档类或前文）。"
            "① 自己重复定义：用 `\\renewcommand` 或 `\\providecommand`；"
            "② 与宏包命令重名：换名（如 `\\myfoo`）；"
            "③ 不要用 `\\def` 覆盖内核命令。"
        ),
        kind="command_conflict",
        text_en=(
            f"Command `{name}` is already defined (by a package, the class, or earlier "
            "text). ① If you redefined it yourself, use `\\renewcommand` or "
            "`\\providecommand`; ② if it clashes with a package command, rename yours "
            "(e.g. `\\myfoo`); ③ do not override kernel commands with `\\def`."
        ),
    )


def _match_no_line_to_end(text: str) -> Any:
    return _NO_LINE_TO_END_RE.search(text)


def _build_no_line_to_end(_match: Any) -> Hint:
    return Hint(
        text=(
            "`\\newline`/`\\\\` 出现在没有内容的段落开头。删掉它，或先写内容；"
            "段落之间用 `\\par`/`\\medskip`，不要用 `\\newline` 代替空行。"
        ),
        kind="no_line_to_end",
        text_en=(
            "`\\newline`/`\\\\` appears at the start of an empty paragraph. Delete it, "
            "or write some content first; separate paragraphs with `\\par`/`\\medskip`, "
            "not `\\newline` as a blank line."
        ),
    )


def _match_pdf_string(text: str) -> Any:
    return _PDF_STRING_RE.search(text)


def _build_pdf_string(_match: Any) -> Hint:
    return Hint(
        text=(
            "PDF 书签只接受纯文本，`\\textbf`、数学、`^`/`_` 等 token 会被移除。"
            "给标题/章节写 `\\texorpdfstring{排版版}{书签纯文本}`；"
            "或在导言区用 `\\pdfstringdefDisableCommands` 统一降级。"
        ),
        commands=("\\texorpdfstring{<TeX 版>}{<纯文本>}",),
        commands_en=("\\texorpdfstring{<TeX version>}{<plain text>}",),
        kind="hyperref_pdf_string",
        text_en=(
            "PDF bookmarks accept plain text only; tokens such as `\\textbf`, math, or "
            "`^`/`_` are stripped. Write `\\texorpdfstring{typeset version}{plain "
            "bookmark text}` for titles/sections, or use `\\pdfstringdefDisableCommands` "
            "in the preamble to disable commands globally."
        ),
    )


def _match_fontspec_not_found(text: str) -> Any:
    stripped = text.lstrip()
    # 散文里的 “The font ... cannot be found” 不是 fontspec 报错；
    # 必须带 `Package fontspec Error` 前缀，或以 `! The font` 错误行开头。
    if "Package fontspec Error" not in stripped and not stripped.lower().startswith("! the font"):
        return None
    return _FONTSPEC_NOT_FOUND_RE.search(text)


def _build_fontspec_not_found(match: Any, tool_name: str = "") -> Hint:
    # fontspec 手册 §2：字体既可按“字体名”加载，也可按“文件名”加载，二者排查方向
    # 不同；按文件名判定依据是 .otf/.ttf/.ttc 扩展名或路径（§2.2）。
    name = match.group(1).strip()
    file_mode = bool(_FONT_FILE_EXT_RE.search(name) or "/" in name or "\\" in name)
    tool = tool_name.lower()
    if file_mode:
        text = (
            f"fontspec 按文件名找不到字体 `{name}`。"
            "① 核对扩展名（`.otf/.ttf/.ttc`）与拼写；fontspec 靠 `.otf` 扩展名判定按文件名加载，"
            "也可用 `Extension=` 单独指定扩展名；"
            "② 文件不在默认搜索路径时，用 `Path=<目录>` 给出所在目录（旧名 `ExternalLocation` 已弃用）；"
            "③ 按文件名加载必须显式给出粗体/斜体等变体（`UprightFont=`/`BoldFont=`/`ItalicFont=`）；"
            "用 `*` 缩写时 `UprightFont=` 为必需，除非提供了 .fontspec 文件；"
            f'④ 用 `kpsewhich "{name}"` 确认文件位于 TeX 能搜到的位置（TEXMF 树或当前目录）。'
        )
        commands = (f'kpsewhich "{name}"',)
        text_en = (
            f"fontspec cannot find the font file `{name}`. "
            "① Check the extension (`.otf/.ttf/.ttc`) and spelling; fontspec selects by file "
            "name from the `.otf` extension, or set the extension separately with `Extension=`. "
            "② If the file is outside the default search path, give its directory with "
            "`Path=<dir>` (the old `ExternalLocation` is deprecated). "
            "③ When loading by file name you must declare bold/italic variants explicitly "
            "(`UprightFont=`/`BoldFont=`/`ItalicFont=`); with the `*` shorthand `UprightFont=` "
            "is required unless a .fontspec file is supplied. "
            f'④ Run `kpsewhich "{name}"` to confirm the file is somewhere TeX can find '
            "(TEXMF tree or current directory)."
        )
    else:
        text = (
            f"fontspec 按字体名找不到族 `{name}`。"
            f"① 在标准字体目录里核对族全名（Linux/macOS："
            f'`fc-list : family | grep -iF "{name}"`；Windows：在“字体设置”里核对完整名称）；'
            "族名可以含空格，注意大小写与重音；"
            "② 字体若在 TEXMF 树内：LuaTeX 可按名字加载；XeTeX 在 Windows/Linux 可以，"
            "macOS 不行——macOS 上 TEXMF 树内的字体只能按文件名加载；"
            "③ 若用 LuaLaTeX，首次排版前可运行 `luaotfload-tool --update`，否则首次排版可能"
            "停顿数分钟；XeLaTeX 不走该缓存，无需执行；"
            "④ 可用 TeX 自带字体（Latin Modern）先验证文档本身没问题。"
        )
        commands: list[str] = [f'fc-list : family | grep -iF "{name}"']
        if tool == "lualatex":
            commands.append("luaotfload-tool --update")
        text_en = (
            f"fontspec cannot find the family `{name}` by font name. "
            "① Verify the full family name in the standard font directories "
            f'(Linux/macOS: `fc-list : family | grep -iF "{name}"`; Windows: check the full '
            "name in Font Settings); family names may contain spaces — mind case and accents. "
            "② For fonts inside the TEXMF tree: LuaTeX can load them by name; XeTeX can on "
            "Windows and Linux, but not on macOS — there such fonts can only be loaded by file name. "
            "③ On LuaLaTeX you may need `luaotfload-tool --update` before first typesetting, "
            "otherwise the first run may pause for several minutes; XeLaTeX does not use this cache. "
            "④ First verify the document itself works with a TeX built-in font (Latin Modern)."
        )
    return Hint(
        text=text,
        commands=tuple(commands),
        kind="missing_font_family",
        text_en=text_en,
    )


def _match_package_error(text: str) -> Any:
    return _PACKAGE_ERROR_RE.search(text)


def _build_package_error(match: Any) -> Hint:
    return Hint(
        text=(f"宏包 `{match.group(1)}` 报错：查看该行上下文与宏包选项，必要时升级/降级该宏包。"),
        kind="package_error",
        text_en=(
            f"Package `{match.group(1)}` error: inspect the surrounding lines "
            "and package options; upgrade/downgrade if needed."
        ),
    )


def _legacy_hint_table(tool_name: str = "") -> dict[str, str]:
    """按工具选择旧提示表；没有工具上下文时保持原来的合并行为。"""
    if not tool_name:
        return collect_hints()
    name = tool_name.lower()
    if name.startswith("biber"):
        from .parsers.biber import BIBER_WARNING_HINTS

        return BIBER_WARNING_HINTS
    if name.startswith("bibtex"):
        from .parsers.bibtex import BIBTEX_ERROR_HINTS

        return BIBTEX_ERROR_HINTS
    if name in {"latex", "pdflatex", "xelatex", "lualatex", "tectonic"}:
        from .parsers.latex import LATEX_LOG_HINTS

        return LATEX_LOG_HINTS
    # 未知工具不要套用其他工具的提示，避免 ``WARN -`` 之类的 key 跨工具误命中。
    return {}


def _match_legacy_hint(text: str, tool_name: str = "") -> str | None:
    """返回命中的旧表键；多个键同时命中时取最具体者。

    不依赖字典插入顺序：通用兜底键（``WARN -``）永远排在具体键之后，
    具体键之间按长度优先（更长的子串通常更具体）。
    """
    matched = [key for key in _legacy_hint_table(tool_name) if _normalize(key) in text]
    if not matched:
        return None
    matched.sort(key=lambda key: (key == "WARN -", -len(key)))
    return matched[0]


def _build_legacy_hint(key: str) -> Hint:
    hint = Hint(
        text=collect_hints()[key],
        kind="log_hint",
        text_en=_LOG_HINT_EN.get(key, ""),
    )
    if key == "Duplicate entry key":
        # 手册行为（非逐字告警）：biber 默认跳过重复键；需要保留重复条目时加
        # `--noskipduplicates`。逐字告警片段 `Duplicate entry key` 已由真实 biber
        # 日志核实（见 docs/hints-research/round5-review.md 修复结果 H1）。
        hint = replace(
            hint,
            text=hint.text + " biber 默认跳过重复键；需要保留重复条目时可用 `--noskipduplicates`。",
            text_en=hint.text_en + " Biber skips duplicate keys by default; use `--noskipduplicates` to retain them.",
        )
    return hint


_BIB_NON_ASCII_KEY_RE = re.compile(r"database entry for\s+[\"']([^\"']+)[\"']", re.IGNORECASE)
_MAKEINDEX_SPECIFIER_RE = re.compile(r"Unknown specifier\s+(\S+)")


def _match_bib_key_non_ascii(text: str) -> Any:
    """只接管“键名本身含非 ASCII 字符”的数据库缺失告警。"""
    match = _BIB_NON_ASCII_KEY_RE.search(text)
    if not match:
        return None
    key = match.group(1)
    return match if any(ord(ch) > 127 for ch in key) else None


def _build_bib_key_non_ascii(match: Any) -> Hint:
    key = match.group(1)
    ascii_key = "".join(ch if ord(ch) < 128 else ch.encode("ascii", "ignore").decode() or "x" for ch in key)
    return Hint(
        text=(
            f"BibTeX 只接受 ASCII 键名，`{key}` 里的非 ASCII 字符导致后端找不到条目。"
            f"把 .bib 与正文里的 `\\cite` 一起改成纯 ASCII（例如 `{ascii_key}`），再跑一遍 bibtex。"
        ),
        kind="bib_key_non_ascii",
        brief=f"键名 `{key}` 含非 ASCII 字符：改成纯 ASCII 后重跑 bibtex。",
        text_en=(
            f"BibTeX accepts ASCII keys only; the non-ASCII characters in `{key}` make the "
            f"backend miss the entry. Rename the key in the .bib and every `\\cite` to plain "
            f"ASCII (e.g. `{ascii_key}`), then rerun bibtex."
        ),
        brief_en=f"Key `{key}` contains non-ASCII characters: rename it to plain ASCII and rerun bibtex.",
    )


def _match_makeindex_style_specifier(text: str) -> Any:
    if "Input style error" not in text:
        return None
    return _MAKEINDEX_SPECIFIER_RE.search(text)


def _build_makeindex_style_specifier(match: Any) -> Hint:
    specifier = match.group(1)
    return Hint(
        text=(
            f"`{specifier}` 是 `.ist` 样式里的新说明符，当前 makeindex 版本不认识。"
            "这是样式与工具版本不匹配，不是索引内容错误；只要索引产物（`.ind`/`.nls`）"
            "已生成即可忽略，要彻底消除可换用与样式匹配的 TeX 发行版或删掉该样式里的 lethead_* 选项。"
        ),
        kind="makeindex_style_specifier",
        brief=f"`.ist` 说明符 `{specifier}` 与 makeindex 版本不匹配；索引产物已生成可忽略。",
        text_en=(
            f"`{specifier}` is a newer `.ist` specifier that this makeindex build does not "
            "understand. It is a style/tool version mismatch, not bad index content; if the "
            "index output (`.ind`/`.nls`) was produced you can ignore it, otherwise use a "
            "matching TeX distribution or drop the lethead_* options from the style."
        ),
        brief_en=(
            f"`.ist` specifier `{specifier}` does not match this makeindex build; "
            "ignore it if the index output was produced."
        ),
    )


#: 规则表。**顺序即语义**：更具体/更致命的规则必须排在前面
#: （``Emergency stop`` 先于 ``Undefined control sequence``，
#:  缺宏包先于缺文件，多行错误先于内建提示表）。
_RULES: tuple[_Rule, ...] = (
    _Rule("missing_package", _match_package, _build_package, _LATEX_TOOLS),
    _Rule("missing_file", _match_missing_file, _missing_file_hint, _LATEX_TOOLS),
    _Rule("font_not_loadable", _match_font_not_loadable, _build_font_not_loadable, _LATEX_TOOLS),
    _Rule("tfm_font_missing", _match_tfm_missing, _build_tfm_missing, _LATEX_TOOLS),
    _Rule("missing_font", _match_font, _build_font, _LATEX_TOOLS),
    _Rule("fontset_unavailable", _match_fontset_unavailable, _build_fontset_unavailable, _LATEX_TOOLS),
    _Rule("unicode", _match_unicode, _build_unicode, _LATEX_TOOLS),
    _Rule("cjk_missing_glyph", _match_cjk_missing_glyph, _build_cjk_missing_glyph, _LATEX_TOOLS),
    _Rule("missing_glyph", _match_missing_glyph, _build_missing_glyph, _LATEX_TOOLS),
    _Rule("missing_bbl", _match_missing_bbl, _build_missing_bbl, _LATEX_TOOLS),
    _Rule("undefined_citation", _match_undefined_citation, _build_undefined_citation, _LATEX_TOOLS),
    _Rule("undefined_reference", _match_undefined_reference, _build_undefined_reference, _LATEX_TOOLS),
    _Rule("undefined_environment", _match_undefined_environment, _build_undefined_environment, _LATEX_TOOLS),
    _Rule("missing_bib", _match_missing_bib, _build_missing_bib, _BIB_SCOPED_TOOLS),
    _Rule("biber_case_mismatch", _match_biber_case, _build_biber_case_mismatch),
    _Rule("float_overflow", _any_of("Too many unprocessed floats"), _build_float_overflow, _LATEX_TOOLS),
    _Rule("capacity", _match_capacity, _build_capacity, _LATEX_TOOLS),
    _Rule("no_output", _any_of("No pages of output"), _build_no_output, _LATEX_TOOLS),
    _Rule("runaway", _match_runaway, _build_runaway, _LATEX_TOOLS),
    _Rule("math_mode", _any_of("Missing $ inserted"), _build_math_mode, _LATEX_TOOLS),
    _Rule("double_script", _match_double_script, _build_double_script, _LATEX_TOOLS),
    _Rule("fatal", _any_of("Emergency stop", "Fatal error occurred"), _build_fatal, _LATEX_TOOLS),
    _Rule("undefined_control", _match_undefined_control, _build_undefined_control, _LATEX_TOOLS),
    _Rule("end_mismatch", _match_end_mismatch, _build_end_mismatch, _LATEX_TOOLS),
    _Rule("option_clash", _match_option_clash, _build_option_clash, _LATEX_TOOLS),
    _Rule("invalid_utf8", _any_of("Invalid UTF-8 byte sequence"), _build_invalid_utf8, _LATEX_TOOLS),
    _Rule(
        "alignment_tab", _any_of("Extra alignment tab", "Misplaced alignment tab"), _build_alignment_tab, _LATEX_TOOLS
    ),
    _Rule("missing_number", _match_missing_number, _build_missing_number, _LATEX_TOOLS),
    _Rule("missing_item", _any_of("missing \\item", lower=True), _build_missing_item, _LATEX_TOOLS),
    _Rule("missing_begin_document", _match_missing_begin_document, _build_missing_begin_document, _LATEX_TOOLS),
    _Rule("extra_close_brace", _match_extra_close_brace, _build_extra_close_brace, _LATEX_TOOLS),
    _Rule("missing_right", _match_missing_right, _build_missing_right, _LATEX_TOOLS),
    _Rule("bad_math_delimiter", _match_bad_math_delimiter, _build_bad_math_delimiter, _LATEX_TOOLS),
    _Rule("misplaced_noalign", _match_misplaced_noalign, _build_misplaced_noalign, _LATEX_TOOLS),
    _Rule("illegal_unit", _match_illegal_unit, _build_illegal_unit, _LATEX_TOOLS),
    _Rule("command_already_defined", _match_command_redefined, _build_command_redefined, _LATEX_TOOLS),
    _Rule("no_line_to_end", _match_no_line_to_end, _build_no_line_to_end, _LATEX_TOOLS),
    _Rule("hyperref_pdf_string", _match_pdf_string, _build_pdf_string, _LATEX_TOOLS),
    _Rule("fontspec_font_not_found", _match_fontspec_not_found, _build_fontspec_not_found, _LATEX_TOOLS),
    _Rule("package_error", _match_package_error, _build_package_error, _LATEX_TOOLS),
    _Rule("bib_key_non_ascii", _match_bib_key_non_ascii, _build_bib_key_non_ascii, _BIB_SCOPED_TOOLS),
    _Rule(
        "makeindex_style_specifier",
        _match_makeindex_style_specifier,
        _build_makeindex_style_specifier,
        frozenset({"makeindex"}),
    ),
    _Rule("log_hint", _match_legacy_hint, _build_legacy_hint),
)

#: 规则 id 的固定顺序（测试用它做快照；新增规则只能追加或显式调整顺序）。
RULE_IDS: tuple[str, ...] = tuple(rule.rule_id for rule in _RULES)


def _hint_for_text_raw(text: str, tool_name: str = "") -> Hint | None:
    """内部实现：按规则表给出建议（不做上下文替换）。"""
    if not text:
        return None
    normalized = _drop_quoted_lines(_normalize(text))
    if not normalized.strip():
        return None
    # 解释性散文（FAQ/教程/changelog 里提到错误名）不是日志，不产出可执行建议。
    # 但错误帧优先：首行含 ``!``/``LaTeX Error:``/``LaTeX Warning:``/``Package … Error:``
    # 时，续行的说明性词语不能把整帧一起吞掉（M2）。
    if _looks_like_prose(normalized) and not _has_error_flag(normalized):
        return None
    tool = tool_name.lower()
    for rule in _RULES:
        # 工具白名单：LaTeX 专属规则不在 biber/bibtex 后端日志下触发；
        # 工具名为空（未知上下文）时保持放行。
        if rule.tools is not None and tool and tool not in rule.tools:
            continue
        # 旧提示表与 biber 专项规则必须按工具隔离；其余规则保持单参数匹配器。
        if rule.rule_id == "log_hint":
            context = _match_legacy_hint(normalized, tool_name)
        elif rule.rule_id == "biber_case_mismatch":
            context = _match_biber_case_scoped(normalized, tool_name)
        else:
            context = rule.match(normalized)
        if not context:
            continue
        if rule.rule_id == "fontspec_font_not_found":
            # 生成器需要引擎上下文：luaotfload 缓存命令只对 LuaLaTeX 给出。
            hint = rule.build(context, tool)
        elif rule.rule_id in {"font_not_loadable", "tfm_font_missing"}:
            # 字体规则按引擎区分 OpenType 族找不到 / pdfTeX 缺 TFM 度量包。
            hint = rule.build(context, tool)
        elif rule.rule_id == "missing_glyph":
            # 缺字形按引擎区分：已在 Xe/Lua 时不再建议换引擎。
            hint = rule.build(context, tool)
        else:
            hint = rule.build(context)
        if hint is not None:
            # 规则 id 由规则表统一注入，生成器不必逐条重复写；这让 JSON/SARIF
            # 能稳定标识“命中了哪条规则”，而文案改动不会影响该标识。
            return replace(hint, rule_id=rule.rule_id)
    return None


def _apply_context(
    hint: Hint,
    *,
    jobname: str | None,
    root_file: str | None,
    tool_name: str | None = None,
) -> Hint:
    """把 ``<jobname>`` / ``<主文件>`` / ``<engine>`` 占位符替换成真实值。

    没有上下文时保留占位符，保证库调用方拿到的仍是可读模板，而不是空命令。
    """
    job = (jobname or "").strip()
    root = (root_file or "").strip()
    if not job and root:
        job = Path(root).stem
    if not root and job:
        root = f"{job}.tex"

    # ``<主文件>`` / ``<main file>`` 只能填 .tex；上下文给的是 .log/.blg 时退回
    # jobname.tex；两者都没有则保留占位符，避免诊断命令指向日志文件而非源码。
    if root.lower().endswith(".tex"):
        main_file = root
    elif job:
        main_file = f"{job}.tex"
    else:
        main_file = ""
    text = hint.text
    text_en = hint.text_en
    brief = hint.brief
    brief_en = hint.brief_en
    commands = list(hint.commands)
    commands_en = list(hint.commands_en)
    if job:
        text = text.replace("<jobname>", job)
        text_en = text_en.replace("<jobname>", job)
        brief = brief.replace("<jobname>", job)
        brief_en = brief_en.replace("<jobname>", job)
        commands = [c.replace("<jobname>", job) for c in commands]
        commands_en = [c.replace("<jobname>", job) for c in commands_en]
    if main_file:
        text = text.replace("<主文件>.tex", main_file).replace("<主文件>", main_file)
        text_en = text_en.replace("<主文件>.tex", main_file).replace("<主文件>", main_file)
        brief = brief.replace("<主文件>.tex", main_file).replace("<主文件>", main_file)
        brief_en = brief_en.replace("<主文件>.tex", main_file).replace("<主文件>", main_file)
        commands = [c.replace("<主文件>.tex", main_file).replace("<主文件>", main_file) for c in commands]
        commands_en = [c.replace("<main file>.tex", main_file).replace("<main file>", main_file) for c in commands_en]
    engine_bin = _ENGINE_BINARIES.get((tool_name or "").lower())
    if engine_bin:
        commands = [c.replace("<engine>", engine_bin).replace("<引擎>", engine_bin) for c in commands]
        commands_en = [c.replace("<engine>", engine_bin) for c in commands_en]
    return Hint(
        text=text,
        commands=tuple(commands),
        kind=hint.kind,
        text_en=text_en,
        commands_en=tuple(commands_en),
        rule_id=hint.rule_id,
        brief=brief,
        brief_en=brief_en,
    )


def hint_for_text(
    text: str,
    *,
    jobname: str | None = None,
    root_file: str | None = None,
    language: str | None = None,
    tool_name: str | None = None,
) -> Hint | None:
    """按一条日志文本给出建议；无匹配返回 ``None``。

    Args:
        jobname: 可选，用于把 ``biber <jobname>`` 之类模板替换成真实命令。
        root_file: 可选，主 ``.tex`` 路径，用于替换 ``<主文件>``。
        language: ``"en"`` 时优先返回英文说明；其他值保持中文。
        tool_name: 可选，产生该条目的工具（latex/pdflatex/bibtex/biber 等）。
            提供时只使用该工具的旧提示表，避免 Biber 的 ``WARN -`` 命中 LaTeX 警告。
    """
    hint = _hint_for_text_raw(text, tool_name=tool_name or "")
    if hint is None:
        return None
    hint = _apply_context(hint, jobname=jobname, root_file=root_file, tool_name=tool_name)
    if language and language.lower() == "en" and hint.text_en:
        return Hint(
            text=hint.text_en,
            commands=hint.commands_en or hint.commands,
            kind=hint.kind,
            text_en=hint.text_en,
            commands_en=hint.commands_en,
            rule_id=hint.rule_id,
            brief=hint.brief_en,
            brief_en=hint.brief_en,
        )
    return hint


def hint_for_entry(
    entry: object,
    *,
    jobname: str | None = None,
    root_file: str | None = None,
    language: str | None = None,
    tool_name: str | None = None,
) -> Hint | None:
    """对 ``LogEntry`` / ``ReportEntry`` 之类的条目给出建议。

    未显式传 ``jobname`` 时，顶层文件名（不含路径分隔符）可用于推断主文件 stem；
    条目 ``file`` 含路径分隔符（``/`` 或反斜杠）时视为子文件，不据此推导主文件，
    保留 ``<jobname>`` 占位符。调用方如果有项目级 jobname（run_pipeline / CLI），
    应显式传入，不能把子文件当成主文件。
    """
    text = getattr(entry, "text", "") or ""
    error_pos_text = getattr(entry, "error_pos_text", "") or ""
    # ``! Undefined control sequence.`` 的实际命令在 parser 的 error_pos_text 里，
    # 不在 text 里；把两段拼起来，规则才能拿到 ``\badcmd``。
    if error_pos_text and error_pos_text not in text:
        text = f"{text}\n{error_pos_text}"
    entry_file = getattr(entry, "file", "") or ""
    # 显式 jobname 代表项目主文件；此时子文件（chapters/intro.tex）不能拿来
    # 填 ``<主文件>``，否则 ``xelatex`` 建议会指向一个无法单独编译的章节。
    if jobname or root_file:
        context_root = root_file or (f"{jobname}.tex" if jobname else None)
    elif "/" in entry_file or "\\" in entry_file:
        context_root = None
    else:
        context_root = entry_file or None
    return hint_for_text(
        text,
        jobname=jobname,
        root_file=context_root,
        language=language,
        tool_name=tool_name,
    )
