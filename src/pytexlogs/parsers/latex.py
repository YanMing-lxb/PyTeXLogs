"""LaTeX 引擎 .log 日志解析器实现。"""

import os
import re
from pathlib import Path
from typing import Any

from ..core.models import BaseLogParser, LogEntry, LogLevel, ParsedLog

__all__ = [
    "LATEX_LOG_HINTS",
    "LatexLogParser",
    "class_warning_info_re",
    "file_stack_open_re",
    "font_warning_re",
    "hyphenation_warning_re",
    "latex_error_re1",
    "latex_error_re2",
    "latex_warn_re",
    "makeindex_warning_re",
    "marginpar_warning_re",
    "missing_char_re",
    "nag_package_sense_re",
    "overfull_box_alt_re",
    "overfull_box_output_re",
    "overfull_box_re",
    "package_warning_extra_lines_re",
    "package_warning_info_re",
    "pages_output_re",
    "rerun_get_cross_references_re",
    "rerun_to_get_citations_re",
    "undefined_label_multi_re",
    "undefined_reference_re",
    "underfull_box_alt_re",
    "underfull_box_output_re",
    "underfull_box_re",
]


LATEX_LOG_HINTS: dict[str, str] = {
    "Undefined control sequence": "检查 \\ 命令名拼写，或确认是否已 \\usepackage 对应宏包。",
    "Undefined reference": "LaTeX 标签尚未被记录：通常需要再编译一到两次（或检查 \\label / \\ref 名）。",
    "Undefined citation": "参考文献键未找到：检查 .bib 文件中的 @xxx{key, 是否与 \\cite{key} 一致，并确认已跑过 bibtex/biber。",
    "Overfull \\\\hbox": "行/盒子过宽超过页面边距：手动断行、放宽 \\sloppy、或调整图文尺寸。",
    "Underfull \\\\hbox": "行/盒子文字不足导致间距拉伸：可接受，或在相应段落补充内容/使用 \\\\linebreak。",
    "Underfull \\\\vbox": "页/盒子文字不足导致间距拉伸：通常可接受，或在相应段落补充内容/调整垂直间距。",
    "Missing character": "当前字体不含该字形：更换包含该字符的字体，或用 \\newunicodechar 映射；"
    "中文/全角字符请配置 ctex/xeCJK 中文字体。",
    "Rerun to get cross-references right": "提示再跑一轮 pdflatex：跨引用页码/链接在 .aux 中更新后需要二次编译。",
    "Rerun to get citations correct": "提示先跑 bibtex/biber，再跑 pdflatex 一到两次以同步参考文献引用。",
}

latex_error_re1 = re.compile(r"^(?:(.*):(\d+):|!)(?: (.+) Error:)? (.+?)$")
latex_error_re2 = re.compile(r"^!(?: (.+) Error:)? (.+?)$")

overfull_box_re = re.compile(r"^(Overfull \\[vh]box \([^)]+\)) in paragraph at lines (\d+)--(\d+)$")
overfull_box_alt_re = re.compile(r"^(Overfull \\[vh]box \([^)]+\)) detected at line (\d+)$")
overfull_box_output_re = re.compile(
    r"^(Overfull \\[vh]box \([^)]+\)) has occurred while \\output is active(?: \((\d+)\))?$"
)

underfull_box_re = re.compile(r"^(Underfull \\[vh]box \([^)]+\)) in paragraph at lines (\d+)--(\d+)$")
underfull_box_alt_re = re.compile(r"^(Underfull \\[vh]box \([^)]+\)) detected at line (\d+)$")
underfull_box_output_re = re.compile(
    r"^(Underfull \\[vh]box \([^)]+\)) has occurred while \\output is active(?: \((\d+)\))?$"
)

latex_warn_re = re.compile(
    r"^((?:(?:Class|Package|Module) \S+)|LaTeX(?: \S*)?|LaTeX3) "
    r"(Warning|Info):\s+(.*?)(?: on(?: input)? line (\d+))?(\.|\?)?$"
)

package_warning_extra_lines_re = re.compile(r"^\(([A-Za-z][A-Za-z0-9-]*)\)\s+(.+?)(?: +on input line (\d+))?$")

missing_char_re = re.compile(r"^\s*(Missing character:.+?[?!])$")

#: 拆出缺失字符与字体，供按 (文件, 字体) 聚合使用。CJK 文本没有配置字体时，
#: pdfTeX 会为每个缺字形各打印一行 ``Missing character``；逐行建条会把几千条
#: 同源警告灌进摘要。聚合后保留首个字符作为可读代表，hints 仍能命中。
_missing_char_detail_re = re.compile(
    r"^Missing character:\s+There is no\s+(?P<char>\S+)"
    r"(?:\s+\(U\+(?P<codepoint>[0-9A-Fa-f]+)\))?\s+in font\s+"
    r"(?P<font>.+?)[!?]$",
    re.IGNORECASE,
)

undefined_reference_re = re.compile(
    r"^LaTeX Warning: (Reference|Citation) [`'\"](.*?)[`'\" ]? on page \d+ undefined on input line (\d+)\.$"
)

#: 错误帧 ``l.N ...`` 的行号与上下文。旧的 ``message_line_re`` 分组会把
#: ``l.5 \foobar`` 的 ``\fo`` 吞进 group(1)，已由本模式取代。
_error_context_re = re.compile(r"^l\.(?P<line>\d+)\s(?P<text>.*)$")

#: 栈项路径允许空格（``C:\Program Files\...\biblatex.sty``）；到行尾或下一个
#: 括号为止，路径段在入栈前再 strip。旧版 ``\S*`` 会在第一个空格处截断路径。
file_stack_open_re = re.compile(r"(?<![^\s])\(([^()\n]+)")

pages_output_re = re.compile(r"Output written on .*\((\d+) page")

class_warning_info_re = re.compile(r"^Class (\S+) Warning:\s+(.*?)(?: +on input line (\d+))?\.?$")
package_warning_info_re = re.compile(r"^Package (\S+) Warning:\s+(.*?)(?: +on input line (\d+))?\.?$")
font_warning_re = re.compile(r"^LaTeX Font Warning:\s+(.*?)(?: +on input line (\d+))?\.?$")
nag_package_sense_re = re.compile(r"^Package nag Warning:\s+(.*?)(?: +on input line (\d+))?\.?$")
marginpar_warning_re = re.compile(r"^LaTeX Warning:\s+Marginpar on page \w+ moved\.?$")
hyphenation_warning_re = re.compile(r"^Underfull \\hbox \(badness (\d+)\) has occurred while \\hyphenation is active")
makeindex_warning_re = re.compile(r"^## Warning \(input\) = (.+)$")
undefined_label_multi_re = re.compile(
    r"^LaTeX Warning: (?:There were (?P<n>\d+) undefined references\.?|There were multiply-defined labels\.?)$"
)
rerun_get_cross_references_re = re.compile(
    r"^LaTeX Warning: Label\(s\) may have changed\. Rerun to get cross-references right\.?$"
)
rerun_to_get_citations_re = re.compile(
    r"^(?:Package (\S+) Warning: Please \(re\)run Biber(?: to get citations right| on the file):?\.?|"
    r"LaTeX Warning: Citation\(s\) may have changed\. Rerun to get citations correct\.?)$"
)
#: biblatex 首遍未跑后端：``No file main.bbl.`` 必须保留为可诊断警告，
#: 否则 hints 的 missing_bbl 看不到条目，只留下 undefined_citation。
no_file_bbl_re = re.compile(r"^No file\s+(\S+?\.bbl)[.;:?]?\s*$")


#: 解析过程中暂存的条目字段；用 dict 别名而不是空子类，避免无意义的类型包装。
_TempEntry = dict[str, Any]


def _join_wrapped_parts(parts: list[str]) -> str:
    """拼接被 max_print_line 折行的片段：词内断行直接粘合，行尾/行首有空白才插空格。"""
    out = ""
    for part in parts:
        if not out:
            out = part
        elif out.endswith(" ") or part.startswith(" "):
            out += " " + part.strip()
        else:
            out += part
    return out


#: 「多行条目的续行」判定用：命中任意一个就说明该行是新条目开头。
#: 模块级常量，避免每行都重新构造列表（原实现每行新建 15 元列表）。
_ENTRY_START_PATTERNS: tuple[re.Pattern[str], ...] = (
    latex_error_re1,
    latex_error_re2,
    undefined_reference_re,
    latex_warn_re,
    missing_char_re,
    class_warning_info_re,
    package_warning_info_re,
    font_warning_re,
    nag_package_sense_re,
    marginpar_warning_re,
    hyphenation_warning_re,
    makeindex_warning_re,
    undefined_label_multi_re,
    rerun_get_cross_references_re,
    rerun_to_get_citations_re,
    no_file_bbl_re,
)

#: 错误行候选模式（两种写法：`file.tex:12: msg` 与 `! msg`）。
_ERROR_PATTERNS: tuple[re.Pattern[str], ...] = (latex_error_re1, latex_error_re2)

#: 坏盒子（overfull/underfull box）的候选模式 + 该模式是否算 overfull。
_BAD_BOX_PATTERNS: tuple[tuple[re.Pattern[str], bool], ...] = (
    (overfull_box_re, True),
    (overfull_box_alt_re, True),
    (overfull_box_output_re, True),
    (underfull_box_re, False),
    (underfull_box_alt_re, False),
    (underfull_box_output_re, False),
)


class LatexLogParser(BaseLogParser):
    """LaTeX .log 日志解析器（兼容旧 API）。"""

    def __init__(self, root_file: str | None = None, quiet: bool = False) -> None:
        """初始化 LatexLogParser（新）：调用父类并设置 latex 默认工具元数据。"""
        super().__init__(root_file)
        self.quiet = quiet
        self.build_log: list[LogEntry] = []
        self.current_result: _TempEntry | None = None
        self.file_stack: list[str] = []
        self.search_empty_line = False
        self.inside_error = False
        self.nested = 0
        #: 预检阶段命中的坏盒子匹配，缓存给 ``_parse_bad_box`` 复用，避免二次遍历正则。
        self._pending_bad_box: Any | None = None
        self._resolved_paths: dict[str, str] = {}
        self._root_dir: str = ""
        self._undefined_refs = 0
        self._undefined_cites = 0
        self._overfull_boxes = 0
        self._underfull_boxes = 0
        #: (文件, 字体) -> {字符: (次数, 码位 U+XXXX 或 None)}；
        #: Missing character 在 parse 结束时按字体合并输出，码位随代表字符保留。
        self._missing_characters: dict[tuple[str, str], dict[str, tuple[int, str | None]]] = {}
        #: 被 max_print_line 折行的 Missing character 续行缓冲，攒到 !/? 再合并。
        self._missing_char_buffer: list[str] = []

    def parse_lines(self, lines: list[str], root_file: str | None = None) -> ParsedLog:
        """兼容旧 API：接收行列表，委托给 parse。"""
        return self.parse("\n".join(lines), root_file=root_file)

    def parse(self, log_text: str, root_file: str | None = None) -> ParsedLog:
        """解析 LaTeX .log 文本并返回 ParsedLog。"""
        if root_file:
            self.root_file = root_file
        elif not self.root_file:
            self.root_file = "main.tex"

        # 调用方直接传文本（captured_outputs / subprocess.stdout）时，文件读取层的
        # utf-8-sig 兜底不生效，这里在解析前统一去 BOM 与 CRLF，避免首行锚定漏匹配。
        log_text = log_text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "")

        # root 目录只在 parse 开头算一次，避免每次取当前文件都重建 pathlib 对象。
        self._root_dir = str(Path(self.root_file).parent)
        self.file_stack = []
        self.build_log.clear()
        self._resolved_paths.clear()
        self._undefined_refs = 0
        self._undefined_cites = 0
        self._overfull_boxes = 0
        self._underfull_boxes = 0
        self._reset_state()

        lines = log_text.split("\n")
        for line in lines:
            self._parse_line(line)

        self._flush_current()

        # 同源缺字形警告在最后统一输出：CJK 文档未配置字体时可能有数千行。
        self._flush_missing_characters()

        # 截断日志（续行不以 !/? 结尾）残留的缓冲降级保留原文，不在 EOF 静默丢弃。
        if self._missing_char_buffer:
            self._record_missing_character(_join_wrapped_parts(self._missing_char_buffer))
            self._missing_char_buffer = []

        pages_output = 0
        m = pages_output_re.search(log_text)
        if m:
            pages_output = int(m.group(1))

        # 单次遍历统计各等级条数：比两次 sum(生成器) 少扫一遍列表。
        level_counts: dict[LogLevel, int] = {}
        for entry in self.build_log:
            level_counts[entry.level] = level_counts.get(entry.level, 0) + 1

        stats: dict[str, Any] = {
            "errors_count": level_counts.get(LogLevel.ERROR, 0),
            "warnings_count": level_counts.get(LogLevel.WARNING, 0),
            "undefined_refs": self._undefined_refs,
            "undefined_cites": self._undefined_cites,
            "overfull_boxes": self._overfull_boxes,
            "underfull_boxes": self._underfull_boxes,
            "pages_output": pages_output,
        }

        return ParsedLog(
            entries=self.build_log[:],
            raw_text=log_text,
            tool_name="latex",
            category="compile",
            importance="high",
            stats=stats,
        )

    def _reset_state(self) -> None:
        self.current_result = _TempEntry(
            type=None,
            file="",
            line=1,
            text="",
            error_pos_text="",
        )
        self.search_empty_line = False
        self.inside_error = False
        self.nested = 0
        self._pending_bad_box = None
        self._missing_characters.clear()
        self._missing_char_buffer.clear()

    def _flush_current(self) -> None:
        if self.current_result is None:
            return
        t = self.current_result.get("type")
        if t is None:
            return
        entry = LogEntry(
            level=t,
            file=str(self.current_result.get("file", "")),
            line=int(self.current_result.get("line", 1) or 1),
            text=str(self.current_result.get("text", "")).rstrip(),
            error_pos_text=str(self.current_result.get("error_pos_text", "")),
        )
        self.build_log.append(entry)
        # 重置为空缓冲：否则下一分支入口的 ``type is not None`` guard 仍命中旧字典，
        # 同一条目会被第二次 flush（连续两条警告时重复入队）。
        self.current_result = _TempEntry(
            type=None,
            file="",
            line=1,
            text="",
            error_pos_text="",
        )

    def _record_missing_character(self, text: str) -> None:
        """把一条 ``Missing character`` 记到 (文件, 字体) 桶里，不立即建条目。

        中文文档未设置 CJK 字体时，pdfTeX 会为每个缺字形打印一行；逐行建条
        会让默认摘要被同一条根因淹没。这里只累加字符计数，parse 结束时按字体
        合并为一条可读警告。
        """
        match = _missing_char_detail_re.match(text)
        if match is None:
            # 非标准格式（某些引擎会改写措辞）：不吞掉，保持原来的逐条行为。
            self.build_log.append(
                LogEntry(
                    level=LogLevel.WARNING,
                    file=self._get_current_file(),
                    line=1,
                    text=text,
                    error_pos_text="",
                )
            )
            return
        file = self._get_current_file()
        font = match.group("font").strip()
        char = match.group("char")
        codepoint = match.group("codepoint")
        bucket = self._missing_characters.setdefault((file, font), {})
        count, old_codepoint = bucket.get(char, (0, None))
        bucket[char] = (count + 1, codepoint or old_codepoint)

    def _flush_missing_characters(self) -> None:
        """把累计的缺字形按 (文件, 字体) 合并输出；单条保持原文不变。"""
        for (file, font), chars in self._missing_characters.items():
            total = sum(count for count, _ in chars.values())
            first_char = next(iter(chars))
            first_codepoint = chars[first_char][1]
            char_label = f"{first_char} (U+{first_codepoint})" if first_codepoint else first_char
            if total == 1:
                text = f"Missing character: There is no {char_label} in font {font}!"
            else:
                distinct = len(chars)
                examples = list(chars)[:8]
                suffix = ", ".join(chars) if distinct <= 8 else ", ".join(examples) + ", …"
                text = (
                    f"Missing character: There is no {char_label} in font {font}! "
                    f"({total} occurrences, {distinct} distinct glyphs: {suffix})"
                )
            self.build_log.append(
                LogEntry(
                    level=LogLevel.WARNING,
                    file=file,
                    line=1,
                    text=text,
                    error_pos_text="",
                )
            )

    def _parse_line(self, line: str) -> None:
        if self.current_result is None:
            return
        line = line.strip("\x00\r")

        if self.search_empty_line:
            if not line or (self.inside_error and line.startswith(" ")):
                self.current_result["text"] = str(self.current_result.get("text", "")) + "\n" + line
                self.search_empty_line = False
                self.inside_error = False
                return

            # TeX 的 ``l.N ...`` 是错误帧的一部分，不是普通续行。先把它解析成
            # 行号和 error_pos_text，再结束 frame；否则 ! 错误会永远停在 line=1。
            if self.inside_error:
                frame_match = _error_context_re.match(line)
                if frame_match:
                    self.current_result["line"] = int(frame_match.group("line"))
                    self.current_result["error_pos_text"] = frame_match.group("text").strip()
                    self.search_empty_line = False
                    self.inside_error = False
                    return

            # 纯文件栈行（``(./chapter.tex`` / ``)``）不是警告续行：先收尾当前条目，
            # 再交给文件栈解析，避免栈名被拼进警告文本。
            if self._is_stack_line(line):
                if self.current_result and self.current_result.get("type") is not None:
                    self._flush_current()
                self.search_empty_line = False
                self.inside_error = False
                self._parse_file_stack(line)
                return

            is_new_entry_start = False
            for pat in _ENTRY_START_PATTERNS:
                if pat.match(line):
                    is_new_entry_start = True
                    break
            bad_box = self._match_bad_box(line)
            self._pending_bad_box = bad_box
            if not is_new_entry_start and bad_box is None:
                package_match = package_warning_extra_lines_re.match(line)
                if package_match:
                    self.current_result["text"] = str(self.current_result.get("text", "")) + "\n" + line
                    if package_match.group(3):
                        self.current_result["line"] = int(package_match.group(3))
                else:
                    self.current_result["text"] = str(self.current_result.get("text", "")) + "\n" + line
                self.search_empty_line = False
                return
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            self.search_empty_line = False
            self.inside_error = False

        error_match = None
        for pattern in _ERROR_PATTERNS:
            error_match = pattern.match(line)
            if error_match:
                break
        if error_match:
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            file = error_match.group(1) or self._get_current_file()
            line_num = int(error_match.group(2)) if error_match.group(2) else 1
            # ``latex_error_re1`` 的 group(3) 是 ``Package foo`` / ``LaTeX`` 这类
            # 前缀，不含 ``Error:``；group(4) 才是正文。无前缀时不能硬拼 ": "，
            # 否则 ``! Undefined control sequence.`` 会变成 ": Undefined..."。
            prefix = f"{error_match.group(3)} Error: " if error_match.group(3) else ""
            msg = (prefix + (error_match.group(4) or "")).strip()
            self.current_result = _TempEntry(
                type=LogLevel.ERROR,
                file=file,
                line=line_num,
                text=msg,
                error_pos_text="",
            )
            self.search_empty_line = True
            self.inside_error = True
            return

        undef_match = undefined_reference_re.match(line)
        if undef_match:
            ref_type, label, line_num = undef_match.groups()  # type: ignore[assignment]
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            if ref_type == "Reference":
                self._undefined_refs += 1
            else:
                self._undefined_cites += 1
            self.current_result = _TempEntry(
                type=LogLevel.WARNING,
                file=self._get_current_file(),
                line=int(line_num),
                text=f"Undefined {ref_type.lower()} `{label}`",
                error_pos_text=label,
            )
            self.search_empty_line = False
            return

        if self._parse_bad_box(line):
            return

        # 折行的缺字形消息：续行先并入缓冲，直到行尾出现 !/? 再合并成一条记录。
        if self._missing_char_buffer:
            # 新错误帧 / 空白行 / 文件栈行不属于缺字形续行：先收尾缓冲，再落到
            # 下方正常分支解析当前行，避免缓冲跨条目串味。
            closes_buffer = (
                line.startswith("!")
                or not line
                or self._is_stack_line(line)
                or line.lstrip().startswith("Missing character:")
                or any(pat.match(line) for pat in _ENTRY_START_PATTERNS)
            )
            if closes_buffer:
                self._record_missing_character(_join_wrapped_parts(self._missing_char_buffer))
                self._missing_char_buffer = []
            else:
                self._missing_char_buffer.append(line.strip())
                if line.rstrip().endswith(("!", "?")):
                    self._record_missing_character(_join_wrapped_parts(self._missing_char_buffer))
                    self._missing_char_buffer = []
                return

        miss_match = missing_char_re.match(line)
        if miss_match or line.lstrip().startswith("Missing character:"):
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            self.current_result = _TempEntry(
                type=None,
                file="",
                line=1,
                text="",
                error_pos_text="",
            )
            first = miss_match.group(1).strip() if miss_match else line.strip()
            self._missing_char_buffer = [first]
            if line.rstrip().endswith(("!", "?")):
                self._record_missing_character(_join_wrapped_parts(self._missing_char_buffer))
                self._missing_char_buffer = []
            self.search_empty_line = False
            return

        if self.inside_error:
            match = _error_context_re.match(line)
            if match:
                self.current_result["line"] = int(match.group("line"))
                self.current_result["error_pos_text"] = match.group("text").strip()
                self.search_empty_line = False
                self.inside_error = False
                return

        extra_match = None

        extra_match = class_warning_info_re.match(line)
        if extra_match:
            _cls_name, _msg, line_num = extra_match.groups()  # type: ignore[assignment]
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            self.current_result = _TempEntry(
                type=LogLevel.WARNING,
                file=self._get_current_file(),
                line=int(line_num) if line_num else 1,
                text=extra_match.group(0),
                error_pos_text="",
            )
            self.search_empty_line = False
            return

        extra_match = font_warning_re.match(line)
        if extra_match:
            _font_msg, line_num = extra_match.groups()  # type: ignore[assignment]
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            self.current_result = _TempEntry(
                type=LogLevel.WARNING,
                file=self._get_current_file(),
                line=int(line_num) if line_num else 1,
                text=extra_match.group(0),
                error_pos_text="",
            )
            self.search_empty_line = False
            return

        extra_match = nag_package_sense_re.match(line)
        if extra_match:
            _nag_msg, line_num = extra_match.groups()  # type: ignore[assignment]
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            self.current_result = _TempEntry(
                type=LogLevel.WARNING,
                file=self._get_current_file(),
                line=int(line_num) if line_num else 1,
                text=extra_match.group(0),
                error_pos_text="",
            )
            self.search_empty_line = False
            return

        extra_match = marginpar_warning_re.match(line)
        if extra_match:
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            self.current_result = _TempEntry(
                type=LogLevel.WARNING,
                file=self._get_current_file(),
                line=1,
                text=extra_match.group(0),
                error_pos_text="",
            )
            self.search_empty_line = False
            return

        extra_match = hyphenation_warning_re.match(line)
        if extra_match:
            badness = extra_match.group(1)
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            self.current_result = _TempEntry(
                type=LogLevel.WARNING,
                file=self._get_current_file(),
                line=1,
                text=f"Underfull \\hbox (badness {badness}) has occurred while \\hyphenation is active",
                error_pos_text="",
            )
            self.search_empty_line = False
            self._underfull_boxes += 1
            return

        extra_match = makeindex_warning_re.match(line)
        if extra_match:
            msg = extra_match.group(1)
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            self.current_result = _TempEntry(
                type=LogLevel.WARNING,
                file=self._get_current_file(),
                line=1,
                text=f"MakeIndex Warning: {msg}",
                error_pos_text="",
            )
            self.search_empty_line = False
            return

        extra_match = undefined_label_multi_re.match(line)
        if extra_match:
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            n = extra_match.group("n")
            text = f"There were {n} undefined references." if n else "There were multiply-defined labels."
            self.current_result = _TempEntry(
                type=LogLevel.WARNING,
                file=self._get_current_file(),
                line=1,
                text=f"LaTeX Warning: {text}",
                error_pos_text="",
            )
            self.search_empty_line = False
            return

        extra_match = rerun_get_cross_references_re.match(line)
        if extra_match:
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            self.current_result = _TempEntry(
                type=LogLevel.WARNING,
                file=self._get_current_file(),
                line=1,
                text="LaTeX Warning: Label(s) may have changed. Rerun to get cross-references right.",
                error_pos_text="",
            )
            self.search_empty_line = False
            return

        extra_match = rerun_to_get_citations_re.match(line)
        if extra_match:
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            self.current_result = _TempEntry(
                type=LogLevel.WARNING,
                file=self._get_current_file(),
                line=1,
                text=line.strip(),
                error_pos_text="",
            )
            self.search_empty_line = True
            return

        # 通用 Package 分支放在 nag / rerun 之后：``package_warning_info_re``
        # 能匹配任意 ``Package <name> Warning``，若提前执行会吞掉 nag 提示与
        # biblatex 的 ``(re)run Biber`` 专用分支。
        extra_match = package_warning_info_re.match(line)
        if extra_match:
            _pkg_name, _pkg_msg, line_num = extra_match.groups()  # type: ignore[assignment]
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            self.current_result = _TempEntry(
                type=LogLevel.WARNING,
                file=self._get_current_file(),
                line=int(line_num) if line_num else 1,
                text=extra_match.group(0),
                error_pos_text="",
            )
            self.search_empty_line = False
            return

        extra_match = no_file_bbl_re.match(line)
        if extra_match:
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            self.current_result = _TempEntry(
                type=LogLevel.WARNING,
                file=self._get_current_file(),
                line=1,
                text=f"No file {extra_match.group(1)}.",
                error_pos_text="",
            )
            self.search_empty_line = False
            return

        # 通用 Class/Package/LaTeX 告警放在专用分支之后：否则 latex_warn_re 会
        # 提前吞掉上面的 font/nag/marginpar/undefined-label/rerun 分支，使专用
        # 结构化文案永远不可达。
        warn_match = latex_warn_re.match(line)
        if warn_match:
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            category = warn_match.group(1)
            level = warn_match.group(2)
            message = warn_match.group(3) or ""
            line_num = warn_match.group(4)  # type: ignore[assignment]
            suffix = warn_match.group(5) or ""
            full_message = f"{category} {level}: {message}"
            # 正则把句末 . / ? 单独捕获；不要在 message 已带标点时再拼一次，
            # 否则 ``... on input line 3.`` 会变成 ``... line 3..``。
            if suffix and not message.rstrip().endswith(suffix):
                full_message += suffix
            log_type = LogLevel.WARNING if level == "Warning" else LogLevel.INFO
            self.current_result = _TempEntry(
                type=log_type,
                file=self._get_current_file(),
                line=int(line_num) if line_num else 1,
                text=full_message,
                error_pos_text="",
            )
            self.search_empty_line = True
            return

        self._parse_file_stack(line)

    @staticmethod
    def _match_bad_box(line: str) -> tuple[Any, Any, bool, bool] | None:
        """返回首个命中的坏盒子 ``(pattern, match, is_overfull, is_output)``；未命中返回 None。

        ``is_output`` 表示该模式是 ``... has occurred while \\output is active`` 变体：
        它的 group(2) 是页号而不是行号，调用方不能把它当行号使用。

        空白行不可能命中坏盒子正则，直接跳过整张正则表，避免尾随空续行上的冗余扫描。
        """
        if not line.strip():
            return None
        # 所有坏盒子模式都以 Overfull/Underfull 开头；先做 O(1) 前缀判断，
        # 避免普通警告行也逐条扫完整张正则表。
        if not line.startswith(("Overfull", "Underfull")):
            return None
        for pattern, is_overfull in _BAD_BOX_PATTERNS:
            match = pattern.match(line)
            if match:
                is_output = pattern is overfull_box_output_re or pattern is underfull_box_output_re
                return (pattern, match, is_overfull, is_output)
        return None

    def _parse_bad_box(self, line: str) -> bool:
        if self.current_result is None:
            return False
        # 预检阶段已匹配过的结果直接复用，避免同一行二次遍历正则表。
        matched = self._pending_bad_box
        self._pending_bad_box = None
        if matched is None:
            matched = self._match_bad_box(line)
        if matched is None:
            return False
        _pattern, match, is_overfull, is_output = matched
        if self.current_result and self.current_result.get("type") is not None:
            self._flush_current()
        file = self._get_current_file()
        if is_output:
            # ``has occurred while \output is active (7)`` 的括号里是页号；
            # 冒充行号会给出错误的源码定位，因此行号固定 1，并保留整句（含页号）。
            text = match.group(0)
            line_num = 1
        else:
            text = match.group(1)
            line_num = int(match.group(2)) if match.group(2) else 1
        if is_overfull:
            self._overfull_boxes += 1
        else:
            self._underfull_boxes += 1
        self.current_result = _TempEntry(
            type=LogLevel.TYPESET,
            file=file,
            line=line_num,
            text=text,
            error_pos_text="",
        )
        self.search_empty_line = False
        return True

    @staticmethod
    def _stack_path_is_file(path: str) -> bool:
        """栈项分组内容是否像文件路径：含分隔符、``./``/``../`` 或已知日志后缀。"""
        if "/" in path or "\\" in path or path.startswith(("./", "../")):
            return True
        return bool(
            re.search(
                r"\.(?:tex|sty|cls|aux|fd|cfg|def|ldf|clo|bbl|blg|idx|ind|gls|glo|"
                r"acr|nls|nlo|toc|lof|lot|out|log|ist|alg|slg|dvi|pdf|ps|eps)\b",
                path,
            )
        )

    @classmethod
    def _is_stack_line(cls, line: str) -> bool:
        """纯文件栈行：单独的 ``)`` / ``(``，或以 ``(`` 开头的栈项路径。

        续行前缀 ``(ctex) mode.`` / ``(biblatex) main`` 虽以括号开头，但不是文件
        栈项：仅当分组内容是路径形态时才判为栈行。
        """
        stripped = line.strip()
        if stripped in (")", "("):
            return True
        m = file_stack_open_re.match(line)
        return bool(m and cls._stack_path_is_file(m.group(1)))

    @classmethod
    def _stack_prefix_is_paths(cls, prefix: str) -> bool:
        """回退保护：本行前缀含 ``(``，且去掉括号后每个 token 都是文件路径。

        ``(./b.tex) )`` 这类“上一行打开、本行连续闭合”的写法里，末尾的 ``)``
        前缀不含本行自己的开括号，但前缀里的路径 token 全部是文件，说明它们都是
        文件栈括号；而普通文本行里的孤立 ``)`` 前缀要么没有 ``(``，要么夹带非
        路径 token，因此不会被误判为弹栈。
        """
        if "(" not in prefix:
            return False
        tokens = prefix.replace("(", " ").replace(")", " ").split()
        return bool(tokens) and all(cls._stack_path_is_file(token) for token in tokens)

    def _parse_file_stack(self, line: str) -> None:
        # 绝大多数日志行没有文件栈括号；先做一次 O(1) 字符检查，避免逐字符循环。
        if "(" not in line and ")" not in line:
            return
        i = 0
        n = len(line)
        # 本行打开的文件数。必须是计数器而不是布尔：同一行的多个 ``)`` 都要能
        # 各自弹掉一个本行打开的文件，否则 ``(./a.tex) (./b.tex))`` 会残留栈。
        opens_on_line = 0
        while i < n:
            ch = line[i]
            if ch == "(":
                if i == 0 or line[i - 1].isspace():
                    m = file_stack_open_re.match(line, i)
                    if m:
                        path_part = m.group(1).strip()
                        if self._stack_path_is_file(path_part):
                            self.file_stack.append(path_part)
                            opens_on_line += 1
                        else:
                            self.nested += 1
                        i = m.end()
                        continue
                i += 1
            elif ch == ")":
                if self.nested > 0:
                    self.nested -= 1
                elif self.file_stack and (
                    not line[:i].strip() or opens_on_line > 0 or self._stack_prefix_is_paths(line[:i])
                ):
                    self.file_stack.pop()
                    opens_on_line = max(opens_on_line - 1, 0)
                i += 1
            else:
                i += 1

    def _get_current_file(self) -> str:
        current_path = self.file_stack[-1] if self.file_stack else self.root_file
        if current_path in self._resolved_paths:
            return self._resolved_paths[current_path]

        root_dir = self._root_dir
        # 用 os.path.normpath 而不是 Path.resolve()：前者只做字符串规范化（无系统调用），
        # 后者在 Windows 上会为每个路径触发 nt._getfinalpathname / readlink 解析符号链接，
        # 真实日志上占约 19 ms。这里只用于错误归属展示，不需要真实路径解析。
        resolved = os.path.normpath(os.path.join(str(root_dir), current_path))

        self._resolved_paths[current_path] = resolved
        return resolved
