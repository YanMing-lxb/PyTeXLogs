"""SARIF 导出模块：将报告/条目导出为 SARIF v2.1.0 格式。

与 0.4.x 的差异：
- 支持 ``min_level``（与 ``--severity`` 对齐）；
- ``artifactLocation.uri`` 使用相对路径 + 正斜杠 + 百分号编码（原实现直接塞入
  Windows 反斜杠路径，不是合法 URI）；
- 补齐 ``tool.driver.rules``、``partialFingerprints``，让 GitHub Code Scanning
  能稳定去重；
- 非 error/warning 的条目降级为 ``note``（``none`` 会被部分平台直接丢弃）。
"""

import hashlib
import os
from contextlib import suppress
from pathlib import Path
from typing import Any
from urllib.parse import quote

from ..core.models import LogEntry, LogLevel, ParsedPipelineReport
from ..version import __version__
from .json_exporter import _flatten_to_entries, _hint_payload, filter_by_level

_LEVEL_TO_SARIF = {
    LogLevel.ERROR: "error",
    LogLevel.WARNING: "warning",
    LogLevel.INFO: "note",
    LogLevel.TYPESET: "note",
    LogLevel.FONT: "note",
    LogLevel.GRAPHIC: "note",
    LogLevel.PAGE: "note",
}


def _as_uri(path_str: str, cwd: Path) -> str:
    """把文件路径转成 SARIF 可接受的 URI（相对、正斜杠、已编码）。"""
    if not path_str:
        return "unknown.tex"
    p = Path(path_str)
    if p.is_absolute():
        with suppress(ValueError):
            p = Path(os.path.relpath(p, cwd))
    return quote(p.as_posix(), safe="/:._~-")


def to_sarif(
    obj: Any,
    *,
    min_level: LogLevel | None = None,
    include_hints: bool = True,
    language: str | None = None,
) -> dict[str, Any]:
    """将三种输入导出为 SARIF v2.1.0 子集 dict。

    ``include_hints=True`` 时，有可执行建议的结果会在 ``properties`` 中增加
    ``pytexlogs/hint``；没有匹配的结果保持原样，便于旧消费者忽略该扩展。

    ``language`` 为可选提示语言：``"en"`` 时 hint 的 ``text`` 取英文说明
    （缺失回退中文），``None``/其他值保持默认中文；``text_en`` 仍保留。
    """
    obj = filter_by_level(obj, min_level)
    flat = _flatten_to_entries(obj)
    cwd = Path.cwd()
    hint_jobname = obj.jobname or None if isinstance(obj, ParsedPipelineReport) else None
    hint_root_file = obj.root_file or None if isinstance(obj, ParsedPipelineReport) else None

    sarif_results: list[dict[str, Any]] = []
    rules: dict[str, dict[str, Any]] = {}

    for entry, _category, _tool, _sp in flat:
        if not isinstance(entry, LogEntry):
            continue

        rule_id = f"pytexlogs/{entry.level.value}"
        text = entry.text or "(empty)"
        if rule_id not in rules:
            rules[rule_id] = {
                "id": rule_id,
                "name": entry.level.value,
                "shortDescription": {"text": f"PyTeXLogs {entry.level.value} entry"},
                "defaultConfiguration": {"level": _LEVEL_TO_SARIF.get(entry.level, "note")},
            }

        file_uri = _as_uri(entry.file or "", cwd)
        start_line = max(1, entry.line or 1)
        # 指纹不含行号：同一文件、同一条消息在正文插入几行后仍应被平台
        # 视为同一个问题，而不是新增告警。行号只放在 region.startLine。
        fingerprint = hashlib.sha1(f"{file_uri}|{' '.join(text.split())}".encode()).hexdigest()

        result = {
            "ruleId": rule_id,
            "level": _LEVEL_TO_SARIF.get(entry.level, "note"),
            "message": {"text": text},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": file_uri},
                        "region": {"startLine": start_line},
                    }
                }
            ],
            "partialFingerprints": {"pytexlogs/v1": fingerprint},
        }
        if include_hints:
            payload = _hint_payload(
                entry,
                _category,
                _tool,
                _sp,
                jobname=hint_jobname,
                root_file=hint_root_file,
                language=language,
            )
            if payload is not None:
                result["properties"] = {"pytexlogs/hint": payload["hint"]}
        sarif_results.append(result)

    return {
        "$schema": ("https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json"),
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "pytexlogs",
                        "version": __version__,
                        "informationUri": "https://pypi.org/project/pytexlogs",
                        "rules": list(rules.values()),
                    }
                },
                "results": sarif_results,
            }
        ],
    }
