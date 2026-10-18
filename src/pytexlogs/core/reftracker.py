"""参考文献引用变更追踪：对比新旧 .aux/.bcf 检测新增/移除引用。"""

import logging
import re
from collections import Counter
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, Literal

from ..parsers.biber import BiberParser
from .state import PROJECT_STATE_FILENAME, ProjectStateStore

__all__ = [
    "RefChangeTracker",
    "citation_command_re",
    "input_re",
]

input_re = re.compile(r"\\(?:input|include)\{(.+?)\}")
citation_command_re = re.compile(
    r"\\(?:cite|upcite|citet|citep|parencite|textcite|footcite|smartcite|autocite)\{([^}]+)\}",
    re.IGNORECASE,
)

#: .aux 中三种记录引用键的写法。原实现每次提取都在函数体内重新 compile，
#: 这里提到模块级只编译一次，并把顺序固定为 citation→abx@aux@cite→bibcite。
_AUX_CITE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\\citation\{([^}]+)\}"),
    re.compile(r"\\abx@aux@cite\{[^}]*\}\{([^}]+)\}"),
    re.compile(r"\\bibcite\{([^}]+)\}"),
)

logger = logging.getLogger(__name__)


def _split_keys(group: str) -> list[str]:
    """把 ``key1,key2, key3`` 这类组内容拆成去空白、去空项的键列表。"""
    return [key for raw in group.split(",") if (key := raw.strip())]


class RefChangeTracker:
    """参考文献变更追踪器：从 aux/bcf 提取引用键并与缓存 diff。"""

    def __init__(self, auxdir: str | Path, jobname: str, translate_fn: Callable[[str], str] | None = None) -> None:
        """初始化 RefChangeTracker：缓存 auxdir、jobname 与共享状态存储句柄。"""
        self.auxdir = Path(auxdir)
        self.jobname = jobname
        self.cache_path = self.auxdir / PROJECT_STATE_FILENAME
        self._store = ProjectStateStore(self.auxdir, jobname)
        self._translate_fn: Callable[[str], str] = translate_fn or (lambda s: s)

    def extract_from_aux(self, aux_path: str | Path) -> list[str]:
        """从 LaTeX .aux 文件提取所有 cite 引用键列表。

        三个模式共用一段拆分逻辑：正则只负责抓 ``\\citation{...}`` 的花括号内容，
        键的实际拆分交给 :func:`_split_keys`（walrus + 列表推导）。
        原实现对每个模式都套一层 ``try/except Exception``，但 ``m.group(1)`` 对
        有捕获组的匹配不可能抛异常，因此这里不再捕获，只在真正可能失败的文件
        读取处（:meth:`detect_mode`）保留容错。
        """
        path = Path(aux_path)
        if not path.exists():
            return []
        text = path.read_text(encoding="utf-8", errors="ignore")

        keys: list[str] = []
        for pattern in _AUX_CITE_PATTERNS:
            for match in pattern.finditer(text):
                keys.extend(_split_keys(match.group(1)))
        return keys

    def extract_from_bcf(self, bcf_path: str | Path) -> list[str]:
        """从 Biber .bcf 文件提取所有 cite 引用键列表。"""
        return BiberParser.parse_bcf(bcf_path)

    def detect_mode(self) -> Literal["bibtex", "biber", "unknown"]:
        """检测当前参考文献模式：bibtex/biber/unknown。"""
        bcf_path = self.auxdir / f"{self.jobname}.bcf"
        if bcf_path.exists():
            return "biber"

        aux_path = self.auxdir / f"{self.jobname}.aux"
        if aux_path.exists():
            try:
                text = aux_path.read_text(encoding="utf-8", errors="ignore")
                if "\\bibdata" in text or "\\citation" in text or "\\bibcite" in text:
                    return "bibtex"
            except Exception as _e:
                logger.debug("读取 aux 文件失败，降级为 unknown 模式: %s", _e)

        return "unknown"

    def extract_current(self) -> list[str]:
        """根据检测到的模式提取当前运行的引用键列表（不去重，保留重复用于计数）。"""
        mode = self.detect_mode()
        if mode == "biber":
            return self.extract_from_bcf(self.auxdir / f"{self.jobname}.bcf")
        elif mode == "bibtex":
            return self.extract_from_aux(self.auxdir / f"{self.jobname}.aux")
        return []

    def extract_current_with_counts(self) -> tuple[list[str], dict[str, int]]:
        """提取当前引用键列表（不去重）并统计每个 key 的出现次数。"""
        raw_keys = self.extract_current()
        counts = dict(Counter(raw_keys))
        return raw_keys, counts

    def extract_current_counts(self) -> dict[str, int]:
        """提取当前引用键的计数统计（不去重统计）。"""
        return self.extract_current_with_counts()[1]

    def load_cache(self) -> list[str]:
        """从共享状态文件加载上次保存的引用键列表。"""
        keys = self._store.get_refs().get("keys", [])
        return [str(k) for k in keys] if isinstance(keys, list) else []

    def load_cache_counts(self) -> dict[str, int]:
        """从共享状态文件加载上次保存的 key_counts 统计。"""
        kc = self._store.get_refs().get("key_counts", {})
        if isinstance(kc, dict):
            return {str(k): int(v) for k, v in kc.items()}
        return {}

    def save_cache(
        self, keys: Iterable[str], key_counts: dict[str, int] | None = None
    ) -> None:
        """将引用键写入共享状态文件的 ``pytexlogs.refs`` 命名空间。

        只更新本命名空间，PyTeXMK 写在 ``pytexmk.build`` 下的构建状态原样保留。
        """
        if key_counts is None:
            key_counts = dict(Counter(keys))
        self._store.update_refs(keys=sorted(set(keys)), key_counts=key_counts)

    def diff(
        self, now_keys: Iterable[str], old_keys: Iterable[str]
    ) -> dict[str, set[str] | bool]:
        """计算新旧引用键集合差异：新增/移除/未变。"""
        now_set = set(now_keys)
        old_set = set(old_keys)
        return {
            "added": now_set - old_set,
            "removed": old_set - now_set,
            "unchanged": now_set & old_set,
            "old_was_empty": len(old_set) == 0,
        }

    def format_report(self, diff_dict: dict[str, Any], total_unique: int) -> str:
        """将引用差异结果格式化为人类可读字符串。"""
        added = len(diff_dict.get("added", set()))
        removed = len(diff_dict.get("removed", set()))
        old_was_empty = bool(diff_dict.get("old_was_empty", False))

        if added == 0 and removed == 0:
            return self._translate_fn("参考文献: {} 篇引用, 无变动").format(total_unique)

        if old_was_empty and removed == 0:
            return self._translate_fn("参考文献: {} 篇引用, 首次运行, 新增 {}").format(
                total_unique, added
            )

        return self._translate_fn("参考文献: {} 篇引用, 新增 {}, 移除 {}").format(
            total_unique, added, removed
        )

    def summarize_diff(self, old_keys: Iterable[str], now_keys: Iterable[str]) -> str:
        """便捷方法：对比新旧引用键集合并返回格式化的差异摘要字符串。"""
        diff_dict = self.diff(now_keys, old_keys)
        total_unique = len(set(now_keys))
        return self.format_report(diff_dict, total_unique)
