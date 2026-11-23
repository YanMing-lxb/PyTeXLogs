"""BibTeX 参考文献 .blg 日志解析器实现。"""

import re
from typing import Any

from ..core.models import BaseLogParser, LogEntry, LogLevel, ParsedLog
from .path_utils import resolve_relative_path_from

__all__ = [
    "BIBTEX_ERROR_HINTS",
    "BibtexParser",
    "bad_cross_ref_bibtex_re",
    "database_file_re",
    "entries_processed_re",
    "error_aux_file_re",
    "multi_line_bibtex_warning_re",
    "re_error",
    "single_line_bibtex_warning_re",
]


BIBTEX_ERROR_HINTS: dict[str, str] = {
    "I'm skipping whatever remains of this entry": "BibTeX 条目语法错误：检查该条目中是否缺逗号、括号不配对，或字段名拼写错误。",
    "I'm skipping whatever remains of this command": '@string / 缩写宏定义错误：检查 @string{key = "value"} 语法。',
    "A bad cross reference": "交叉引用指向不存在的条目：检查 crossref = {xxx} 中 xxx 是否存在于同一 .bib 文件。",
    "---while reading file": "读取辅助文件失败：检查 .aux 是否正常生成（先跑一次 pdflatex），路径是否正确。",
}

single_line_bibtex_warning_re = re.compile(r"^Warning--(.+?)(?:\s+in\s+(?:file\s+)?(\S+))?\s*$")
multi_line_bibtex_warning_re = re.compile(r"(?m)^Warning--(.+)\n--line (\d+) of file (.+)$")
#: 帧体用否定前瞻约束不得跨越下一条 ``---line`` 错误头：旧写法 ``[\s\S]*?``
#: 在大量重复帧上会退化成 O(n²) 回溯（5000 帧约 6s），这里把帧体限制在
#: 当前错误头与收尾行之间。
bad_cross_ref_bibtex_re = re.compile(
    r'^(A bad cross reference---entry ".+?"\nrefers to entry.+?, which doesn\'t exist)$',
    re.MULTILINE,
)
error_aux_file_re = re.compile(r"^(.*)---while reading file (.*)$", re.MULTILINE)

re_error = re.compile(r"---(line (?P<line>[0-9]+) of|while reading) file (?P<file>.*)")

database_file_re = re.compile(r"^Database file #\d+: (.+)$", re.MULTILINE)
# BibTeX 的条目统计有三种写法：
#   TeX Live    `39 entries, 2 warnings`      （单行带 warnings）
#   TeX Live 旧  `(39 entries)`              （括号内）
#   MiKTeX      `You've used 39 entries,`     （带缩进、逗号收尾、warnings 单独成行）
# 用「紧邻数字前的断言」而非「必须前面有空白/括号」：行首的 `39 entries, ...`
# 前面没有任何字符，要求 [(\s] 会直接漏掉整个 TeX Live 单行写法。
# 真实 .blg 全文只有一处 "N entries" 字样，因此宽松匹配无误报风险。
entries_processed_re = re.compile(r"(?<!\d)(\d+)\s+entries?\b")


class BibtexParser(BaseLogParser):
    """BibTeX 解析器：解析 .blg 日志并聚合参考文献问题。"""

    def __init__(self, root_file: str | None = None) -> None:
        """初始化 BibtexParser：调用父类并设置 bibtex 默认工具元数据。"""
        super().__init__(root_file)
        self.build_log: list[LogEntry] = []
        self._resolved_paths: dict[str, str] = {}
        self._seen_keys: set[tuple[str, int, str]] = set()
        self._entries_processed = 0
        self._warnings_count = 0
        self._crossref_errors_count = 0
        self._database_files: list[str] = []

    def parse(self, log_text: str, root_file: str | None = None) -> ParsedLog:
        """解析 BibTeX .blg 日志文本并返回 ParsedLog。"""
        if root_file:
            self.root_file = root_file
        elif not self.root_file:
            self.root_file = "main.tex"

        self.build_log.clear()
        self._resolved_paths.clear()
        self._seen_keys.clear()
        self._entries_processed = 0
        self._warnings_count = 0
        self._crossref_errors_count = 0
        self._database_files = []

        text = log_text.replace("\r\n", "\n").replace("\r", "\n")
        self._scan_multiline_patterns(text)
        self._scan_database_files(text)
        self._scan_entries_stats(text)

        lines = text.split("\n")
        # ``---line`` 错误帧由有界帧扫描统一记录，避免单行路径二次记录。
        self._scan_error_frames(lines)

        # 索引式遍历：多行 ``Warning--`` 帧已被多行扫描记录，这里看到首行且下一
        # 行是 ``--line N of file`` 续行时整帧跳过，避免单行路径二次记录。
        i = 0
        while i < len(lines):
            line = lines[i]
            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            if single_line_bibtex_warning_re.match(line.strip("\x00")) and next_line.strip().startswith("--line "):
                i += 2
                continue
            self._parse_line_with_unified_error(line)
            i += 1

        # warnings_count 口径：与去重后的 WARNING 条目数一致，不再回填日志正文
        # 声明的 ``N warnings``。
        self._warnings_count = sum(1 for e in self.build_log if e.level == LogLevel.WARNING)

        stats: dict[str, Any] = {
            "entries_processed": self._entries_processed,
            "warnings_count": self._warnings_count,
            "crossref_errors_count": self._crossref_errors_count,
            "database_files": self._database_files[:],
        }

        return ParsedLog(
            entries=self.build_log[:],
            raw_text=log_text,
            tool_name="bibtex",
            category="bibliography",
            importance="high",
            stats=stats,
        )

    def _add_entry(self, level: LogLevel, file: str, line: int, text: str) -> bool:
        """按稳定键 ``(file, line, normalized text)`` O(1) 去重后追加条目。

        文本规范化为折叠空白后的单行；重复帧返回 ``False`` 不重复入列。
        """
        normalized = " ".join(text.split())
        key = (file, int(line), normalized)
        if key in self._seen_keys:
            return False
        self._seen_keys.add(key)
        self.build_log.append(LogEntry(level=level, file=file, line=int(line), text=normalized))
        return True

    def _scan_multiline_patterns(self, log_text: str) -> None:
        for m in multi_line_bibtex_warning_re.finditer(log_text):
            filename = self._fix_bib_bib_dup(m.group(3))
            filename = self._resolve_bib_file(filename)
            self._add_entry(
                LogLevel.WARNING,
                filename,
                int(m.group(2)),
                m.group(1).strip(),
            )

        for m in bad_cross_ref_bibtex_re.finditer(log_text):
            if self._add_entry(LogLevel.ERROR, self.root_file, 1, m.group(1).strip()):
                self._crossref_errors_count += 1

        for m in error_aux_file_re.finditer(log_text):
            filename = self._resolve_aux_file(m.group(2))
            # 裸 ``---while reading file x.aux`` 的 group(1) 为空；直接入列会得到
            # 空 message，既污染 JSON/CSV/SARIF，也让去重键退化。保留原始行。
            text = m.group(1).strip() or m.group(0).strip()
            self._add_entry(LogLevel.ERROR, filename, 1, text)

    def _scan_error_frames(self, lines: list[str]) -> None:
        """按行有界扫描 ``---line N of file`` 错误帧。

        旧实现用两条全局多行正则在全文范围找各自收尾行（``... entry`` /
        ``... command``）；另一帧形的每个起始行都会匹配失败并回溯到文末，重复帧下
        呈 O(n²)。这里以错误头行为起点，帧体只读到收尾行或下一个错误头为止，
        单帧有界、整体线性。

        文本口径与原单行路径一致：优先取错误头行上 ``---line`` 之前的前缀；前缀
        为空时取帧体首行；再为空则回退到上一非空行（收尾行在前的帧形）。
        """
        n = len(lines)
        prev_nonempty = ""
        i = 0
        while i < n:
            line = lines[i].strip("\x00")
            m = re_error.search(line)
            if m and m.group("line"):
                prefix = line[: m.start()].strip()
                filename = self._fix_bib_bib_dup(m.group("file"))
                filename = self._resolve_bib_file(filename)
                line_num = int(m.group("line"))

                body: list[str] = []
                j = i + 1
                while j < n:
                    nxt = lines[j].strip()
                    if nxt.startswith("I'm skipping whatever remains of this"):
                        j += 1
                        break
                    if re_error.search(lines[j]):
                        break
                    if nxt:
                        body.append(nxt)
                    j += 1

                text = prefix or (body[0] if body else "") or prev_nonempty
                if text:
                    self._add_entry(LogLevel.ERROR, filename, line_num, text)
                prev_nonempty = body[-1] if body else prev_nonempty
                i = j
                continue

            if line.strip():
                prev_nonempty = line.strip()
            i += 1

    def _scan_database_files(self, log_text: str) -> None:
        for m in database_file_re.finditer(log_text):
            filename = self._fix_bib_bib_dup(m.group(1).strip())
            filename = self._resolve_bib_file(filename)
            if filename not in self._database_files:
                self._database_files.append(filename)

    def _scan_entries_stats(self, log_text: str) -> None:
        """提取 ``39 entries`` 统计。

        TeX Live 写 ``39 entries, 2 warnings``，MiKTeX 写 ``You've used 39 entries,``
        后跟内建函数调用计数。``warnings`` 正文声明数不再回填：
        ``warnings_count`` 以去重后的 WARNING 条目数为准（见 :meth:`parse`）。
        """
        for m in entries_processed_re.finditer(log_text):
            self._entries_processed = max(self._entries_processed, int(m.group(1)))

    def _parse_line_with_unified_error(self, line: str) -> None:
        line = line.strip("\x00")

        match = single_line_bibtex_warning_re.match(line)
        if match:
            raw_file = match.group(2)
            if raw_file:
                filename = self._fix_bib_bib_dup(raw_file)
                filename = self._resolve_bib_file(filename)
            else:
                filename = self.root_file
            self._add_entry(LogLevel.WARNING, filename, 1, match.group(1).strip())
            return

        # ``---line`` 错误帧已由 :meth:`_scan_error_frames` 有界记录；这里只兜底
        # ``---while reading file`` 这类无行号的辅助文件错误。
        m = re_error.search(line)
        if m and not m.group("line"):
            # 裸 ``---while reading file x.aux`` 已由 _scan_multiline_patterns
            # 用完整行记录；这里再用 last_line 兜底会把上一行无关文本当成
            # error，并把 file 从 .tex 改成 .aux。只有带前缀的同一行错误才
            # 需要走这段 prefix 兜底。
            if m.start() == 0:
                return
            text = line[: m.start()].strip()

            if not text:
                return

            filename = self._fix_bib_bib_dup(m.group("file"))
            filename = self._resolve_bib_file(filename)
            self._add_entry(LogLevel.ERROR, filename, 1, text)

    @staticmethod
    def _fix_bib_bib_dup(filename: str) -> str:
        if filename.endswith(".bib.bib"):
            return filename[:-4]
        return filename

    def _resolve_bib_file(self, filename: str) -> str:
        if filename in self._resolved_paths:
            return self._resolved_paths[filename]

        resolved = resolve_relative_path_from(filename, self.root_file, getattr(self, "_source_path_hint", ""))
        self._resolved_paths[filename] = resolved
        return resolved

    def _resolve_aux_file(self, filename: str) -> str:
        return self._resolve_bib_file(filename.replace(".aux", ".tex"))
