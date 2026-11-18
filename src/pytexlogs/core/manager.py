"""LogParserManager：按 step/suffix 调度解析器并汇总结果。"""

import logging
from pathlib import Path

from .models import (
    BaseLogParser,
    LogLevel,
    ParsedLog,
    ToolResult,
    ToolResultStats,
)
from .registry import LogParserRegistry, LogParserSpec

logger = logging.getLogger(__name__)


def _parsed_log_to_tool_result(
    parsed: ParsedLog,
    tool_name: str,
    category: str,
    importance: str,
) -> ToolResult:
    error_count = sum(1 for e in parsed.entries if e.level == LogLevel.ERROR)
    warning_count = sum(1 for e in parsed.entries if e.level == LogLevel.WARNING)
    merged_stats = dict(parsed.stats)
    merged_stats.setdefault("error", error_count)
    merged_stats.setdefault("warning", warning_count)
    return ToolResult(
        tool_name=tool_name,
        category=category,
        importance=importance,
        source_path=parsed.source_path,
        raw_text=parsed.raw_text,
        entries=parsed.entries,
        stats=ToolResultStats(
            entries_count=len(parsed.entries),
            stats=merged_stats,
        ),
    )


class LogParserManager:
    """解析器管理器：按 step/suffix 路由到对应 BaseLogParser 并汇总。"""

    def __init__(self, registry: LogParserRegistry | None = None) -> None:
        """初始化 LogParserManager：缓存 registry（默认取内置 + entry point 注册表）。"""
        self.registry: LogParserRegistry = (
            registry if registry is not None else LogParserRegistry.get_default_registry()
        )

    def register(self, step_name: str, parser_cls: type[BaseLogParser]) -> None:
        """注册自定义解析器 step_name → parser_cls（直接进 registry，不再维护第二份映射）。"""
        self.registry.register(step_name, parser_cls)

    def lookup(self, step_name: str) -> LogParserSpec | None:
        """按 step_name 查询已注册的解析器规格。"""
        return self.registry.lookup(step_name)

    def discover_log_path(
        self,
        parser_cls: type[BaseLogParser],
        jobname: str,
        auxdir: str | Path,
    ) -> Path | None:
        """按解析器后缀在 auxdir 查找日志文件路径；未注册的解析器返回 None。"""
        spec = self.registry.find_spec_by_parser_cls(parser_cls)
        if spec is None:
            return None

        if spec.discover_hook is not None:
            result = spec.discover_hook(jobname, Path(auxdir))
            if result is not None:
                return result
        return spec.default_discover(jobname, auxdir)

    def _resolve_parser(self, step_name: str) -> tuple[type[BaseLogParser] | None, LogParserSpec | None]:
        spec = self.registry.lookup(step_name)
        if spec is None:
            return None, None
        return spec.parser_cls, spec

    def run(
        self,
        jobname: str,
        auxdir: str | Path,
        steps: list[str] | None = None,
        captured_outputs: dict[str, str] | None = None,
    ) -> list[ToolResult]:
        """按 steps 顺序发现并解析日志，返回 list[ToolResult]。"""
        if steps is None:
            from .logkind import plan_default_steps

            steps = plan_default_steps(jobname, auxdir)
        captured_outputs = captured_outputs or {}
        results: list[ToolResult] = []
        seen: set[tuple[str, str]] = set()
        consumed_paths: dict[Path, str] = {}

        for step_name in steps:
            parser_cls, spec = self._resolve_parser(step_name)
            if parser_cls is None:
                logger.warning("未找到 step=%s 对应的日志 parser，跳过", step_name)
                continue

            parser = parser_cls()
            parser_cls_name = parser_cls.__name__
            parsed: ParsedLog | None = None
            key: str | None = None

            if step_name in captured_outputs:
                key = f"captured:{step_name}"
                if (parser_cls_name, key) in seen:
                    continue
                text = captured_outputs[step_name]
                parsed = parser.parse(text)
                parsed.source_path = key
            else:
                log_path = self.discover_log_path(parser_cls, jobname, auxdir)
                if log_path is None:
                    continue
                try:
                    resolved_key = str(log_path.resolve())
                except OSError:
                    resolved_key = str(log_path)
                if resolved_key in consumed_paths:
                    logger.debug(
                        "step=%s 的日志 %s 已被 step=%s 消费，跳过",
                        step_name, log_path, consumed_paths[resolved_key],
                    )
                    continue
                consumed_paths[resolved_key] = step_name
                key = str(log_path)
                if (parser_cls_name, key) in seen:
                    continue
                parsed = parser.parse_file(log_path)

            if parsed is not None and key is not None:
                seen.add((parser_cls_name, key))
                if spec is not None:
                    result_tool_name = step_name
                    result_category = spec.category
                    result_importance = spec.importance
                else:
                    result_tool_name = step_name
                    result_category = parsed.category or "custom"
                    result_importance = parsed.importance or "low"
                tool_result = _parsed_log_to_tool_result(
                    parsed,
                    tool_name=result_tool_name,
                    category=result_category,
                    importance=result_importance,
                )
                results.append(tool_result)

        return results
