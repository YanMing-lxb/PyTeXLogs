"""Biber 参考文献 .bcf 日志解析器实现。"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from ..core.models import BaseLogParser, LogEntry, LogLevel, ParsedLog
from .path_utils import resolve_relative_path_from

__all__ = [
    "BIBER_WARNING_HINTS",
    "BiberParser",
    "biber_error_re",
    "biber_generic_error_re",
    "biber_generic_warning_re",
    "biber_info_re",
    "biber_line_warning_re",
    "biber_missing_entry_re",
]


BIBER_WARNING_HINTS: dict[str, str] = {
    "I didn't find a database entry": "Biber 未找到对应参考文献键：检查 .bib 文件中 @xxx{key, 是否存在，或键名与 \\cite/\\autocite 是否一致。",
    "Duplicate entry key": "参考文献条目键重复：检查 .bib 中是否存在重复键，或同一条目同一字段重复定义。",
    "WARN -": "通用 Biber 警告：可能是数据校验问题，确认 .bib 字段格式与 biblatex 要求一致。",
}

biber_info_re = re.compile(r"^INFO - Found BibTeX data source \'(.*)\'$")
biber_error_re = re.compile(r"^ERROR - BibTeX subsystem.*, line (\d+), (.*)$")
#: 真实 .blg 行首带 ``[220] Biber.pm:132> `` 位置前缀，先剥离再匹配 WARN/ERROR。
_biber_line_prefix_re = re.compile(r"^\[\d+\]\s+[^\s>]*>\s+")
biber_missing_entry_re = re.compile(r"^WARN - (I didn\'t find a database entry for \'.*?\'.*)$")
biber_line_warning_re = re.compile(r"^WARN - (.*? entry `(.+?)\' .*)$")
biber_generic_warning_re = re.compile(r"^WARN - (.*)$")
biber_generic_error_re = re.compile(r"^ERROR - (.*)$")
#: ``Found N citekeys in bib section M``：Biber 在各段报告的引用键总数。
_biber_citekeys_re = re.compile(r"Found\s+(\d+)\s+citekeys")


class BiberParser(BaseLogParser):
    """Biber 参考文献解析器：解析 .bcf 与 .blg 日志。"""

    def __init__(self, root_file: str | None = None) -> None:
        """初始化 BiberParser：调用父类并设置 biber 默认工具元数据。"""
        super().__init__(root_file)
        self.build_log: list[LogEntry] = []
        self.bib_file_stack: list[str] = []
        self._resolved_paths: dict[str, str] = {}
        self._database_files: list[str] = []

    def parse(self, log_text: str, root_file: str | None = None) -> ParsedLog:
        """解析 Biber .blg 日志文本并返回 ParsedLog。"""
        if root_file:
            self.root_file = root_file
        elif not self.root_file:
            self.root_file = "main.tex"

        self.bib_file_stack = [self.root_file]
        self.build_log.clear()
        self._database_files = []
        self._resolved_paths.clear()
        self._total_citations = 0

        text = log_text.replace("\r\n", "\n").replace("\r", "\n")
        lines = text.split("\n")
        for line in lines:
            self._parse_line(line)

        stats: dict[str, Any] = {
            "database_files": self._database_files[:],
            "total_citations": self._total_citations,
            "unique_citations": len(set(self._collect_bcf_citekeys())),
        }

        return ParsedLog(
            entries=self.build_log[:],
            raw_text=log_text,
            tool_name="biber",
            category="bibliography",
            importance="high",
            stats=stats,
        )

    def _collect_bcf_citekeys(self) -> list[str]:
        """从同目录 .bcf 收集 citekey；找不到 bcf 时返回空列表。

        ``.blg`` 本身只报告引用键数量，不含键名；去重必须读 bcf。优先用
        ``parse_file`` 提供的日志路径找同目录 bcf，其次用 ``root_file`` 推导。
        """
        candidates: list[Path] = []
        source_hint = getattr(self, "_source_path_hint", "")
        if source_hint:
            candidates.append(Path(source_hint).with_suffix(".bcf"))
        if self.root_file:
            bcf = Path(self.root_file).with_suffix(".bcf")
            if bcf not in candidates:
                candidates.append(bcf)

        for candidate in candidates:
            if candidate.exists():
                return self.parse_bcf(candidate)
        return []

    def _parse_line(self, line: str) -> None:
        line = _biber_line_prefix_re.sub("", line.strip("\x00"))

        citekeys_match = _biber_citekeys_re.search(line)
        if citekeys_match:
            self._total_citations += int(citekeys_match.group(1))

        info_match = biber_info_re.match(line)
        if info_match:
            filename = info_match.group(1)
            resolved_file = self._resolve_bib_file(filename)
            self.bib_file_stack.append(resolved_file)
            if resolved_file not in self._database_files:
                self._database_files.append(resolved_file)
            return

        error_match = biber_error_re.match(line)
        if error_match:
            line_number = int(error_match.group(1))
            file = self.bib_file_stack[-1] if self.bib_file_stack else self.root_file
            self.build_log.append(
                LogEntry(
                    level=LogLevel.ERROR,
                    file=file,
                    line=line_number,
                    text=error_match.group(2),
                )
            )
            return

        missing_match = biber_missing_entry_re.match(line)
        if missing_match:
            file = self.bib_file_stack[-1] if self.bib_file_stack else self.root_file
            self.build_log.append(
                LogEntry(
                    level=LogLevel.WARNING,
                    file=file,
                    line=1,
                    text=missing_match.group(1),
                )
            )
            return

        warning_match = biber_line_warning_re.match(line)
        if warning_match:
            file = self.bib_file_stack[-1] if self.bib_file_stack else self.root_file
            self.build_log.append(
                LogEntry(
                    level=LogLevel.WARNING,
                    file=file,
                    line=1,
                    text=warning_match.group(1),
                )
            )
            return

        warn_generic = biber_generic_warning_re.match(line)
        if warn_generic:
            file = self.bib_file_stack[-1] if self.bib_file_stack else self.root_file
            self.build_log.append(
                LogEntry(
                    level=LogLevel.WARNING,
                    file=file,
                    line=1,
                    text=warn_generic.group(1),
                )
            )
            return

        err_generic = biber_generic_error_re.match(line)
        if err_generic:
            file = self.bib_file_stack[-1] if self.bib_file_stack else self.root_file
            self.build_log.append(
                LogEntry(
                    level=LogLevel.ERROR,
                    file=file,
                    line=1,
                    text=err_generic.group(1),
                )
            )
            return

    def _resolve_bib_file(self, filename: str) -> str:
        if filename in self._resolved_paths:
            return self._resolved_paths[filename]

        resolved = resolve_relative_path_from(filename, self.root_file, getattr(self, "_source_path_hint", ""))
        self._resolved_paths[filename] = resolved
        return resolved

    @staticmethod
    def parse_bcf(bcf_path: str | Path) -> list[str]:
        """解析 Biber .bcf XML 提取参考文献处理信息。"""
        path = Path(bcf_path)
        result: list[str] = []
        try:
            tree = ET.parse(path)
            root = tree.getroot()
            result.extend(
                elem.text
                for elem in root.iter()
                if (elem.tag.endswith("}citekey") or elem.tag == "citekey") and elem.text
            )
        except Exception:  # noqa: BLE001,S110
            pass
        return result
