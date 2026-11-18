"""解析器注册中心：定义 LogParserSpec 与 LogParserRegistry。

用于按 step 名称或日志文件后缀匹配对应的 BaseLogParser 实现。
"""

import importlib.metadata
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ..parsers.asymptote import AsymptoteParser
from ..parsers.biber import BiberParser
from ..parsers.bibtex import BibtexParser
from ..parsers.glossaries import GlossariesParser
from ..parsers.latex import LatexLogParser
from ..parsers.makeindex import MakeindexParser
from ..parsers.minted import MintedParser
from ..parsers.nomencl import NomenclParser
from ..parsers.pythontex import PythontexParser
from ..parsers.xindy import XindyParser
from .models import BaseLogParser

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class LogParserSpec:
    step_names: list[str]
    log_suffixes: list[str]
    category: str
    importance: Literal["high", "medium", "low"]
    parser_cls: type[BaseLogParser]
    discover_hook: Callable[[str, Path], Path | None] | None = None

    def default_discover(self, jobname: str, auxdir: str | Path) -> Path | None:
        aux = Path(auxdir)
        for suffix in self.log_suffixes:
            p = aux / f"{jobname}{suffix}"
            if p.exists():
                return p
        return None


class LogParserRegistry:
    _default_instance: LogParserRegistry | None = None

    def __init__(self) -> None:
        self._step_to_spec: dict[str, LogParserSpec] = {}
        self._suffix_to_specs: dict[str, list[LogParserSpec]] = {}

    @classmethod
    def get_instance(cls) -> LogParserRegistry:
        """返回全局默认注册表（含内置解析器与第三方 entry point）。

        0.6.1 起本方法与 :meth:`get_default_registry` 等价：0.5 的 ``get_instance``
        返回过一个"什么都没注册"的空表，调用方 ``lookup()`` 全部落空却不会报错，
        属于静默失效的陷阱 API，故合并为单一入口。
        """
        return cls.get_default_registry()

    @classmethod
    def get_default_registry(cls) -> LogParserRegistry:
        if cls._default_instance is None:
            cls._default_instance = cls()
            cls._default_instance._register_defaults()
            cls._default_instance.load_entry_points()
        return cls._default_instance

    @classmethod
    def load_entry_points(cls, registry: LogParserRegistry | None = None) -> LogParserRegistry:
        if registry is None:
            registry = cls()
        eps: list[importlib.metadata.EntryPoint] = []
        try:
            eps = list(importlib.metadata.entry_points(group="pytexlogs.parsers"))
        except TypeError:
            try:
                selected = importlib.metadata.entry_points().select(group="pytexlogs.parsers")
                eps = list(selected)
            except Exception as exc:
                logger.warning("无法获取 pytexlogs.parsers entry_points: %s", exc)
                return registry
        except Exception as exc:
            logger.warning("无法获取 pytexlogs.parsers entry_points: %s", exc)
            return registry
        for ep in eps:
            step_name = ep.name
            try:
                parser_cls = ep.load()
            except Exception as exc:
                logger.warning(
                    "pytexlogs.parsers entry_point %r 加载失败: %s",
                    step_name,
                    exc,
                )
                continue
            registry.register(step_name, parser_cls)
        return registry

    def _register_defaults(self) -> None:
        specs: list[LogParserSpec] = [
            LogParserSpec(
                step_names=["pdflatex", "xelatex", "lualatex", "latex"],
                log_suffixes=[".log"],
                category="compile",
                importance="high",
                parser_cls=LatexLogParser,
            ),
            LogParserSpec(
                step_names=["bibtex"],
                # 0.6.1：移除 .bcf —— 那是 biber 的构建控制文件（XML），bibtex 从不产出，
                # 挂在 bibtex 上会让 .bcf 成为"两个解析器争用的后缀"。
                log_suffixes=[".blg"],
                category="bibliography",
                importance="high",
                parser_cls=BibtexParser,
            ),
            LogParserSpec(
                step_names=["biber"],
                log_suffixes=[".blg", ".bcf"],
                category="bibliography",
                importance="high",
                parser_cls=BiberParser,
            ),
            LogParserSpec(
                step_names=["makeindex", "upmendex", "mendex"],
                log_suffixes=[".ilg"],
                category="index",
                importance="medium",
                parser_cls=MakeindexParser,
            ),
            LogParserSpec(
                step_names=["xindy", "texindy"],
                log_suffixes=[".glg", ".alg", ".slg", ".ilg"],
                category="index",
                importance="medium",
                parser_cls=XindyParser,
            ),
            LogParserSpec(
                step_names=["makeglossaries", "glossaries"],
                log_suffixes=[".glg", ".alg", ".slg"],
                category="glossary",
                importance="medium",
                parser_cls=GlossariesParser,
            ),
            LogParserSpec(
                step_names=["nomencl"],
                log_suffixes=[".nlg"],
                category="glossary",
                importance="medium",
                parser_cls=NomenclParser,
            ),
            LogParserSpec(
                step_names=["pythontex"],
                log_suffixes=[".pytxcode"],
                category="code",
                importance="low",
                parser_cls=PythontexParser,
            ),
            LogParserSpec(
                step_names=["asy", "asymptote"],
                log_suffixes=[".asy", ".log"],
                category="external",
                importance="low",
                parser_cls=AsymptoteParser,
            ),
            LogParserSpec(
                step_names=["minted"],
                log_suffixes=[".pygmented"],
                category="code",
                importance="low",
                parser_cls=MintedParser,
            ),
        ]
        for spec in specs:
            self.register_spec(spec)

    def register_spec(self, spec: LogParserSpec) -> None:
        for step_name in spec.step_names:
            if step_name in self._step_to_spec:
                existing = self._step_to_spec[step_name]
                logger.warning(
                    "步骤 %r 已注册到 %s，将被 %s 覆盖",
                    step_name,
                    existing.parser_cls.__name__,
                    spec.parser_cls.__name__,
                )
            self._step_to_spec[step_name] = spec
        for suffix in spec.log_suffixes:
            if suffix not in self._suffix_to_specs:
                self._suffix_to_specs[suffix] = []
            self._suffix_to_specs[suffix].append(spec)

    def register(
        self,
        step_name: str,
        parser_cls: type[BaseLogParser],
        log_suffixes: list[str] | None = None,
        category: str = "custom",
        importance: Literal["high", "medium", "low"] = "low",
    ) -> None:
        spec = LogParserSpec(
            step_names=[step_name],
            log_suffixes=log_suffixes or [],
            category=category,
            importance=importance,
            parser_cls=parser_cls,
        )
        self.register_spec(spec)

    def lookup(self, step_name: str) -> LogParserSpec | None:
        return self._step_to_spec.get(step_name)

    def lookup_by_suffix(self, suffix: str) -> list[LogParserSpec]:
        return list(self._suffix_to_specs.get(suffix, []))

    def iter_specs(self) -> tuple[LogParserSpec, ...]:
        """返回去重后的全部 spec（按注册顺序）。

        ``easy.py`` 等调用方据此推导"后缀 → 解析器"，不再自建第二份映射表。
        """
        seen: set[int] = set()
        result: list[LogParserSpec] = []
        for specs in self._suffix_to_specs.values():
            for spec in specs:
                if id(spec) in seen:
                    continue
                seen.add(id(spec))
                result.append(spec)
        return tuple(result)

    def all_suffixes(self) -> tuple[str, ...]:
        """返回全部已注册日志后缀，按长度倒序（便于最长后缀优先匹配）。"""
        return tuple(sorted(self._suffix_to_specs, key=len, reverse=True))

    def all_step_names(self) -> tuple[str, ...]:
        """返回全部已注册 step 名称（用于报错时列出可选值）。"""
        return tuple(self._step_to_spec)

    def find_spec_by_parser_cls(self, parser_cls: type[BaseLogParser]) -> LogParserSpec | None:
        """根据解析器类查找对应的 spec。"""
        for spec in self._step_to_spec.values():
            if spec.parser_cls is parser_cls:
                return spec
        return None


def load_entry_points(registry: LogParserRegistry | None = None) -> LogParserRegistry:
    return LogParserRegistry.load_entry_points(registry)
