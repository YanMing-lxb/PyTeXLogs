import importlib
import warnings

import pytest

V010_ALL = [
    "BIBER_WARNING_HINTS",
    "BIBTEX_ERROR_HINTS",
    "CATEGORY_LABEL",
    "CATEGORY_ORDER",
    "IMPORTANCE_LABEL",
    "LATEX_LOG_HINTS",
    "AsymptoteParser",
    "BaseLogParser",
    "BiberParser",
    "BibtexParser",
    "GlossariesParser",
    "LatexLogParser",
    "LogEntry",
    "LogLevel",
    "LogParserManager",
    "LogParserRegistry",
    "LogParserSpec",
    "MakeindexParser",
    "MintedParser",
    "NomenclParser",
    "ParsedLog",
    "ParsedPipelineReport",
    "PythontexParser",
    "RefChangeTracker",
    "XindyParser",
    "format_editor_jumps",
    "load_report",
    "log_editor_jumps",
    "print_summary",
    "run_demo",
    "run_log_pipeline",
    "show_log_entries",
    "write_report",
]


def test_b1_run_pipeline_is_wrapped():
    import pytexlogs as pkg

    if hasattr(pkg.run_log_pipeline, "__wrapped__"):
        assert pkg.run_pipeline is pkg.run_log_pipeline.__wrapped__
    else:
        cap1 = pkg.run_pipeline(
            quiet=True, print_terminal=False, pytexmk_version="0.2.0", ref_tracker_translate_fn=None
        )
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            cap2 = pkg.run_log_pipeline(
                quiet=True, print_terminal=False, pytexmk_version="0.2.0", ref_tracker_translate_fn=None
            )
        assert cap1.pipeline.total_steps == cap2.pipeline.total_steps
        assert cap1.jobname == cap2.jobname


def test_b2_class_aliases_identical():
    import pytexlogs as pkg

    assert pkg.Manager is pkg.LogParserManager
    assert pkg.Registry is pkg.LogParserRegistry
    assert pkg.Report is pkg.ParsedPipelineReport


@pytest.mark.parametrize("name", V010_ALL)
def test_b3_v010_symbols_exist(name):
    pkg = importlib.import_module("pytexlogs")
    val = getattr(pkg, name, None)
    assert val is not None, f"Symbol \'{name}\' is None / missing from pytexlogs public API"


def test_b4_deprecation_warning_on_run_log_pipeline():
    import pytexlogs as pkg

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        pkg.run_log_pipeline(
            quiet=True, print_terminal=False, pytexmk_version="0.2.0", ref_tracker_translate_fn=None
        )

    deprecation_count = len([w for w in caught if issubclass(w.category, DeprecationWarning)])
    assert deprecation_count >= 1, f"Expected >=1 DeprecationWarning, got {deprecation_count}"
