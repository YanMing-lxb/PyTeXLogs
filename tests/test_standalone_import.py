def test_import_pytexlogs_package():
    import pytexlogs
    assert hasattr(pytexlogs, '__all__')
    assert len(pytexlogs.__all__) >= 33


def test_all_required_symbols_present():
    import pytexlogs
    symbols = [
        "LatexLogParser", "BibtexParser", "BiberParser", "AsymptoteParser",
        "MintedParser", "PythontexParser", "GlossariesParser", "MakeindexParser",
        "NomenclParser", "XindyParser", "LogParserManager", "LogLevel",
        "LogEntry", "ParsedLog", "ParsedPipelineReport", "RefChangeTracker",
        "BaseLogParser", "LogParserRegistry", "LogParserSpec", "print_summary",
        "format_editor_jumps", "log_editor_jumps", "show_log_entries",
        "run_log_pipeline", "LATEX_LOG_HINTS", "BIBTEX_ERROR_HINTS",
        "BIBER_WARNING_HINTS", "CATEGORY_LABEL", "CATEGORY_ORDER",
        "IMPORTANCE_LABEL", "load_report", "write_report", "run_demo",
    ]
    for sym in symbols:
        assert hasattr(pytexlogs, sym), f"Missing symbol: {sym}"


def test_latex_parser_basic_functional():
    from pytexlogs import LatexLogParser, LogLevel
    lines = [r"main.tex:42: Undefined control sequence \foo"]
    parsed = LatexLogParser(quiet=True).parse_lines(lines)
    assert len(parsed.entries) >= 1
    assert parsed.entries[0].line == 42
    assert parsed.entries[0].level == LogLevel.ERROR


def test_format_editor_jumps_smoke():
    from pytexlogs import LatexLogParser, format_editor_jumps
    parsed = LatexLogParser(quiet=True).parse_lines([
        r"chapters/intro.tex:7: LaTeX Error: Something's wrong--perhaps a missing \item."
    ])
    jumps = format_editor_jumps(parsed.entries)
    assert isinstance(jumps, list)
    assert len(jumps) >= 1
    found = False
    for j in jumps:
        if "chapters/intro.tex:7" in j or "intro.tex:7" in j:
            found = True
            break
    assert found, f"Expected 'chapters/intro.tex:7' in jumps, got: {jumps}"


def test_run_log_pipeline_smoke():
    from pytexlogs import print_summary, run_log_pipeline
    report = run_log_pipeline(
        quiet=True,
        print_terminal=False,
        pytexmk_version="0.1.0",
        ref_tracker_translate_fn=None,
    )
    assert report is not None
    print_summary([], use_logger=False, non_quiet=False)
