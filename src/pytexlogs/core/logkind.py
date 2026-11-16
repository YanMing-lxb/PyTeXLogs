"""日志类型嗅探与默认解析步骤规划。

背景：不同工具会写同一后缀的日志（``.blg`` 既属于 BibTeX 也属于 Biber，
``.ilg`` 既属于 makeindex 也属于 xindy，``.log`` 既属于引擎也容易被
Asymptote 的规则误认）。如果按“固定 10 个 step”逐个探测，同一份文件会被
多个 parser 各解析一次，统计翻倍、归因错乱。

本模块只做两件事：
1. :func:`sniff_bib_tool` / :func:`sniff_index_tool` —— 读日志头部判断真实工具；
2. :func:`plan_default_steps` —— 按 auxdir 里实际存在的文件，生成“每个日志
   只会被一个 step 消费”的步骤列表。

判定优先级刻意保守：拿不准时退回到最常见的那一个（BibTeX / makeindex），
宁可少认一个工具，也不重复解析同一份日志。
"""

from __future__ import annotations

from pathlib import Path

__all__ = [
    "plan_default_steps",
    "sniff_bib_tool",
    "sniff_index_tool",
    "sniff_tex_engine",
]

#: 读取日志头部用于嗅探的最大字符数；再大也没有意义，反而拖慢启动。
_HEAD_BYTES = 4096


def _head(path: Path) -> str:
    """读取文件头部文本（多编码兜底，失败返回空串）。"""
    try:
        data = path.read_bytes()[:_HEAD_BYTES]
    except OSError:
        return ""
    for encoding in ("utf-8", "utf-8-sig", "gbk", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace")


def sniff_bib_tool(path: Path) -> str:
    """判断 ``.blg`` 是 BibTeX 还是 Biber 写出的。

    判定顺序：
    1. 同名 ``.bcf`` 存在 → Biber（biblatex + biber 的强特征，BibTeX 不产 bcf）；
    2. 日志头部出现 ``Biber`` / ``biblatex`` → Biber；
    3. 其余一律按 BibTeX（包括空文件与读不到内容的情况）。
    """
    p = Path(path)
    if p.with_suffix(".bcf").exists():
        return "biber"
    head = _head(p).lower()
    if "biber" in head or "biblatex" in head:
        return "biber"
    return "bibtex"


def sniff_tex_engine(path: Path) -> str | None:
    """从 ``.log`` 头部判断 TeX 引擎，返回 registry 认识的 step 名。

    真实日志第一行通常是 ``This is pdfTeX / XeTeX / LuaHBTeX, Version ...``。
    目录模式下如果固定用 ``pdflatex``，XeLaTeX/LuaLaTeX 项目会在报告里被
    错误标注为 pdflatex；这里只做保守判断，认不出就返回 ``None``。
    """
    head = _head(Path(path)).lower()
    if "xetex" in head:
        return "xelatex"
    if "luahbtex" in head or "luatex" in head:
        return "lualatex"
    if "pdftex" in head:
        return "pdflatex"
    # 老式 latex（DVI 引擎）的头部是 “This is TeX, Version ...”
    if "this is tex" in head:
        return "latex"
    return None


def sniff_index_tool(path: Path) -> str:
    """判断 ``.ilg`` 是 makeindex 还是 xindy 写出的。"""
    head = _head(Path(path)).lower()
    if "xindy" in head:
        return "xindy"
    if "makeindex" in head or "mendex" in head or "upmendex" in head:
        return "makeindex"
    # 头部无特征时看同目录是否只有 xindy 产物（.xdy）而没有 .idx
    # 注意：Path.glob() 返回生成器，布尔值恒为 True；必须用 any() 判断是否真的存在。
    parent = Path(path).parent
    if any(parent.glob("*.xdy")):
        return "xindy"
    return "makeindex"


def plan_default_steps(jobname: str, auxdir: str | Path) -> list[str]:
    """按 auxdir 里实际存在的日志文件，规划默认解析步骤（同一日志只归一个 step）。"""
    aux = Path(auxdir)
    log_path = aux / f"{jobname}.log"
    engine = sniff_tex_engine(log_path) if log_path.exists() else None
    steps: list[str] = [engine or "pdflatex"]
    if not aux.exists():
        return steps

    # --- 参考文献：.bcf/.blg 只交给一个 parser ---
    blg = aux / f"{jobname}.blg"
    bcf = aux / f"{jobname}.bcf"
    if bcf.exists() or blg.exists():
        steps.append(sniff_bib_tool(blg) if blg.exists() else "biber")

    # --- 主索引：只解析 .ilg ---
    ilg = aux / f"{jobname}.ilg"
    if ilg.exists():
        steps.append(sniff_index_tool(ilg))

    # --- 术语表：.glg/.alg/.slg 交给 GlossariesParser（它同时兼容 makeindex/xindy）---
    if any((aux / f"{jobname}{suffix}").exists() for suffix in (".glg", ".alg", ".slg")):
        steps.append("makeglossaries")

    # --- 符号表 ---
    if (aux / f"{jobname}.nlg").exists():
        steps.append("nomencl")

    # --- 代码块/外部工具：只有真存在产物才解析，避免空结果污染报告 ---
    if (aux / f"{jobname}.pytxcode").exists() or any(aux.glob("pythontex-files-*")):
        steps.append("pythontex")
    if any(aux.glob("*.asy")):
        steps.append("asymptote")
    if any(aux.glob("*.pygmented")):
        steps.append("minted")

    return steps
