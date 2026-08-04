"""SARIF 导出模块：将报告/条目导出为 SARIF v2.1.0 格式。"""

import hashlib
import os
from pathlib import Path
from typing import Any

from ..core.models import LogEntry, LogLevel
from ..version import __version__
from .json_exporter import _flatten_to_entries


def to_sarif(obj: Any) -> dict[str, Any]:
    """将三种输入导出为 SARIF v2.1.0 最小子集 dict。"""
    flat = _flatten_to_entries(obj)
    cwd = Path.cwd()

    sarif_results: list[dict[str, Any]] = []

    for entry, _category, _tool, _sp in flat:
        if not isinstance(entry, LogEntry):
            continue

        rule_id = f"{entry.level.value}-{hashlib.sha1((entry.text or '').encode('utf-8')).hexdigest()[:8]}"

        if entry.level == LogLevel.ERROR:
            sarif_level = "error"
        elif entry.level == LogLevel.WARNING:
            sarif_level = "warning"
        elif entry.level == LogLevel.INFO:
            sarif_level = "note"
        else:
            sarif_level = "none"

        file_uri = entry.file or "unknown.tex"
        if file_uri and Path(file_uri).is_absolute():
            try:
                file_uri = os.path.relpath(file_uri, str(cwd))
            except ValueError:
                pass

        start_line = max(1, entry.line or 1)

        sarif_results.append({
            "ruleId": rule_id,
            "level": sarif_level,
            "message": {"text": entry.text or "(empty)"},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": file_uri or "unknown.tex"},
                        "region": {"startLine": start_line},
                    }
                }
            ],
        })

    return {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "pytexlogs",
                        "version": __version__,
                        "informationUri": "https://pypi.org/project/pytexlogs",
                    }
                },
                "results": sarif_results,
            }
        ],
    }