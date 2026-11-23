"""LogParserManager：按 step/suffix 调度解析器并汇总结果。"""

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from .models import (
    BaseLogParser,
    ParsedLog,
    ToolResult,
    ToolResultStats,
)
from .registry import LogParserRegistry, LogParserSpec
from .stats import recompute_stats

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class StepOutcome:
    """单个 step 的执行结果；run 与 run_pipeline 共用这一层。

    ``skipped_reason`` 非空表示该 step 没有产生解析结果；``error`` 非空表示
    解析器抛出异常。两种状态都保留原因，由调用方决定记录 warning、计入
    ``skipped_steps`` 还是生成带 ``parse_exception`` 的空报告。
    """

    step: str
    spec: LogParserSpec | None
    parsed: ParsedLog | None = None
    log_path: Path | None = None
    source_path: str | None = None
    error: Exception | None = None
    skipped_reason: str | None = None

    @property
    def skipped(self) -> bool:
        """是否被跳过（没有可用的解析结果）。"""
        return self.skipped_reason is not None


def _parsed_log_to_tool_result(
    parsed: ParsedLog,
    tool_name: str,
    category: str,
    importance: str,
) -> ToolResult:
    """把 ParsedLog 转成 ToolResult，并用统一口径重算等级统计。"""
    merged_stats = dict(parsed.stats)
    recompute_stats(parsed.entries, merged_stats)
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

    def iter_steps(
        self,
        jobname: str,
        auxdir: str | Path,
        steps: list[str] | None = None,
        captured_outputs: dict[str, str] | None = None,
        *,
        root_file: str | None = None,
        dedupe_by_parser: bool = True,
        captured_source_prefix: str | None = None,
    ) -> Iterator[StepOutcome]:
        """按 steps 顺序执行发现与解析，逐步产出 StepOutcome。

        - ``dedupe_by_parser=True``：同一解析器 + 同一来源只执行一次；
        - ``captured_source_prefix``：为 captured 文本生成的 ParsedLog 改写
          ``source_path``（manager 兼容旧行为用 ``"captured:"``）。
        """
        if steps is None:
            from .logkind import _append_captured_steps, plan_default_steps

            steps = _append_captured_steps(plan_default_steps(jobname, auxdir), captured_outputs)
        captured_outputs = captured_outputs or {}

        seen: set[tuple[str, str]] = set()
        consumed_paths: dict[Path, str] = {}

        for step_name in steps:
            spec = self.registry.lookup(step_name)
            if spec is None:
                logger.warning("未找到 step=%s 对应的日志 parser，跳过", step_name)
                yield StepOutcome(step=step_name, spec=None, skipped_reason="unregistered")
                continue

            parser = spec.parser_cls(root_file=root_file)
            parser_cls_name = spec.parser_cls.__name__

            if step_name in captured_outputs:
                key = f"captured:{step_name}"
                if dedupe_by_parser and (parser_cls_name, key) in seen:
                    yield StepOutcome(step=step_name, spec=spec, skipped_reason="duplicate")
                    continue
                text = captured_outputs[step_name]
                try:
                    parsed = parser.parse(text, root_file=root_file)
                except Exception as exc:  # noqa: BLE001 — 单步失败不能中断整个目录
                    logger.warning("step=%s 解析失败: %s", step_name, exc, exc_info=True)
                    yield StepOutcome(step=step_name, spec=spec, error=exc, skipped_reason="error")
                    continue
                if parsed is None:
                    yield StepOutcome(step=step_name, spec=spec, skipped_reason="no_result")
                    continue
                if captured_source_prefix is not None:
                    parsed.source_path = f"{captured_source_prefix}{step_name}"
                if dedupe_by_parser:
                    seen.add((parser_cls_name, key))
                yield StepOutcome(
                    step=step_name,
                    spec=spec,
                    parsed=parsed,
                    source_path=parsed.source_path or None,
                )
                continue

            if spec.discover_hook is not None:
                log_path = spec.discover_hook(jobname, Path(auxdir))
            else:
                log_path = spec.default_discover(jobname, auxdir)
            if log_path is None:
                yield StepOutcome(step=step_name, spec=spec, skipped_reason="no_log")
                continue

            try:
                resolved = log_path.resolve()
            except OSError:
                resolved = log_path
            if resolved in consumed_paths:
                logger.debug(
                    "step=%s 的日志 %s 已被 step=%s 消费，跳过",
                    step_name,
                    log_path,
                    consumed_paths[resolved],
                )
                yield StepOutcome(step=step_name, spec=spec, skipped_reason="consumed")
                continue
            consumed_paths[resolved] = step_name

            key = str(log_path)
            if dedupe_by_parser and (parser_cls_name, key) in seen:
                yield StepOutcome(step=step_name, spec=spec, skipped_reason="duplicate")
                continue

            try:
                parsed = parser.parse_file(log_path, root_file=root_file)
            except OSError as exc:
                logger.warning("step=%s 读取日志失败: %s", step_name, exc, exc_info=True)
                yield StepOutcome(step=step_name, spec=spec, skipped_reason="read_error")
                continue
            except Exception as exc:  # noqa: BLE001 — 与 run_pipeline 保持一致
                logger.warning("step=%s 解析失败: %s", step_name, exc, exc_info=True)
                yield StepOutcome(step=step_name, spec=spec, error=exc, skipped_reason="error")
                continue

            if parsed is None:
                yield StepOutcome(step=step_name, spec=spec, skipped_reason="no_result")
                continue
            if dedupe_by_parser:
                seen.add((parser_cls_name, key))
            yield StepOutcome(
                step=step_name,
                spec=spec,
                parsed=parsed,
                log_path=log_path,
                source_path=parsed.source_path or str(log_path),
            )

    def run(
        self,
        jobname: str,
        auxdir: str | Path,
        steps: list[str] | None = None,
        captured_outputs: dict[str, str] | None = None,
        *,
        root_file: str | None = None,
    ) -> list[ToolResult]:
        """按 steps 顺序发现并解析日志，返回 list[ToolResult]。"""
        results: list[ToolResult] = []
        for outcome in self.iter_steps(
            jobname,
            auxdir,
            steps,
            captured_outputs,
            root_file=root_file,
            dedupe_by_parser=True,
            captured_source_prefix="captured:",
        ):
            if outcome.spec is None or outcome.parsed is None:
                continue
            tool_result = _parsed_log_to_tool_result(
                outcome.parsed,
                tool_name=outcome.step,
                category=outcome.spec.category,
                importance=outcome.spec.importance,
            )
            results.append(tool_result)
        return results
