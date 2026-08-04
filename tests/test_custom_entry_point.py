import sys
import unittest.mock
from importlib.metadata import EntryPoint
from pathlib import Path

from pytexlogs import LogParserManager, LogParserRegistry

_tests_dir = Path(__file__).parent
if str(_tests_dir.parent) not in sys.path:
    sys.path.insert(0, str(_tests_dir.parent))


def _fake_entry_points(group=None, **kwargs):
    if group == "pytexlogs.parsers":
        ep = EntryPoint(
            name="chktex",
            value="tests._fake_chktex:ChktexParser",
            group="pytexlogs.parsers",
        )
        return [ep]
    return []


def test_tr71_lookup_after_load_entry_points():
    with unittest.mock.patch(
        "pytexlogs.core.registry.importlib.metadata.entry_points",
        side_effect=_fake_entry_points,
    ):
        registry = LogParserRegistry()
        LogParserRegistry.load_entry_points(registry)
        spec = registry.lookup("chktex")
        assert spec is not None
        assert spec.parser_cls.__name__ == "ChktexParser"


def test_tr72_manager_run_with_chktex_step():
    with unittest.mock.patch(
        "pytexlogs.core.registry.importlib.metadata.entry_points",
        side_effect=_fake_entry_points,
    ):
        mgr = LogParserManager()
        LogParserRegistry.load_entry_points(mgr.registry)
        results = mgr.run(
            "main",
            ".",
            steps=["chktex"],
            captured_outputs={
                "chktex": "ChkTeX warning: 1:14:Command terminated with space.\nother line\nWarning 2:3:Another ChkTeX warning."
            },
        )
        assert len(results) == 1
        r = results[0]
        assert r.tool_name == "chktex"
        assert len(r.entries) >= 1
        assert r.entries[0].level.value == "warning"
