# PyTeXLogs 代码修改手册

> 来源：PyTeXMK / PyTeXLogs 多轮重构、0.6.1 发布、Python 3.15 迁移与纯风格清理。
> 适用：后续维护者与编码代理。PyTeXLogs 是**可独立复制使用的第三方库**，改代码时
> 首先考虑“作为顶级包还能不能工作”，而不是“在 PyTeXMK 里能不能跑”。

## 0. 一句话原则

**先证据，后改动；公共 API 与解析结果优先稳定；行为修复、API 迁移、风格清理分开做。**

## 1. 架构红线（不要破坏）

来自 `src/pytexlogs/__init__.py` 的现有约定：

- 本包必须能作为**顶级包** `import pytexlogs` 独立工作。
- **禁止**跳到父包的双点相对 import；禁止 `import pytexmk.language`、`pytexmk.version`、
  `pytexmk.config` 等主包模块。
- 外部依赖只能通过 `run_pipeline` 的可空参数注入（默认纯英文 / `unknown`）。
- 所有外部使用必须走 `__all__` 中的公共 API；不要新建 `log_parser.py` 之类的薄转发文件。
- `rich` 只是可选增强（`pytexlogs[rich]`），不能变成硬依赖；终端渲染必须在
  `ImportError` 时可降级。

## 2. 每次动手前的固定流程

1. 读 `src/pytexlogs/__init__.py` 的架构注释和 `__all__`，确认改动是否在公共契约内。
2. 读相关 parser / state / exporter 的测试与 fixtures；解析类改动先确认样本日志期望。
3. 建基线：`ruff` 与测试先跑一遍，记录通过数。
4. 划边界：本次是行为修复、公共 API 变更、parser 输出变更，还是纯风格。
5. 最小改动，优先保留旧字段、旧别名与旧导出格式。
6. 定向测试通过后再跑全量；涉及打包时再装 wheel 做独立导入验证。

本对话基线（2026-11，Round 9 后）：

```text
pytest: 706 passed, 6 skipped
ruff: All checks passed
```

## 3. 公共 API 稳定性

优先保持这些入口的行为与签名：

- 解析：`parse_log_file`、`parse_log_text`、`parse_auxdir`、`aggregate_stats`
- 流水线：`run_pipeline`、`LogParserManager`、`LogParserRegistry`
- 状态：`ProjectStateStore`（`PROJECT_STATE_FILENAME`、`SCHEMA_VERSION`）
- 提示：`hint_for_text`、`hint_for_entry`、`detect_missing_package`
- 导出：`to_json`、`to_csv`、`to_sarif`、`filter_by_level`
- 报告：`load_report`、`write_report`

改动 `__all__` 或别名时，至少跑：

```text
tests/test_api_aliases.py
tests/test_standalone_import.py
tests/test_easy_api.py
tests/test_export_formats.py
```

不要为了“统一命名”删除旧别名；需要弃用时先保留别名并写迁移说明。

## 4. Parser 与解析结果

- 每个 parser 的字段、等级映射、去重规则、错误/警告分类都属于**可观察输出**；改之前先看
  `tests/fixtures` 与对应 `test_log_parsers.py` / `test_parser_miktex_formats.py`。
- 新增 parser 优先走 `LogParserRegistry` + Entry Point，不要在 CLI 里加分支。
- 解析结果变化必须补 fixture 或最小样本测试；不要只改正则就宣称完成。
- `sniff_*` / `plan_default_steps` 是“日志类型嗅探”入口，改动要保持默认步骤顺序。
- 错误等级语义由 `LogLevel` / `level_from_value` 统一，不要在单个 parser 里另造等级。

## 5. `ProjectStateStore` 与命名空间

- 状态文件由 `ProjectStateStore` 统一读写；**PyTeXMK 不要自己碰 JSON**。
- 命名空间隔离：`pytexmk` 与 `pytexlogs` 各写各的键，不要互相覆盖。
- 写操作要经过 `update_namespace` / `replace_namespace`，保留锁与原子写。
- 不要改成“先读后直接覆盖整个文件”；并发下会丢另一个命名空间的键。
- 删除命名空间要明确语义：例如清理 `pytexmk` 基线时保留 `pytexlogs.refs`。

## 6. CLI、导出与国际化

- CLI 退出码、`--json` 载荷、SARIF 规则/指纹、CSV 表头都是外部契约；改格式先补
  `test_cli_report_pipeline.py`、`test_export_formats.py`。
- `--json` 失败路径也要有可解析载荷；不要让未捕获异常把 stdout 变成空。
- 国际化走现有 `lang` / `set_summary_language` 机制；英文默认回退不能破坏。
- 不引入联网检查更新；CLI 默认不发起网络请求。

## 7. Python 3.15 与风格

与 PyTeXMK 共用同一套判定：

- `ruff check --select UP` 通过 ≠ 全部现代化；PEP 758 需单独扫描无 `as` 的元组异常处理器。
- `except A, B as e` 在 3.15.2 仍非法；带 `as` 的处理器保留括号。
- `Path.copy` / `Path.move` / `Path.walk`、`hashlib.file_digest`、`StrEnum`、`typing.Self`、
  `tomllib` 按实际场景采用；`Path.info` 因缓存语义否决；`uuid7` 无场景不引入。
- `Path.replace` / `Path.open` / `Path()` 替换前确认异常类型、路径相对性与调用点类型。
- `contextlib.suppress` 只能替换**相同异常类型**的 `try/except/pass`；不要顺手扩大捕获范围。
- `extend` / 列表推导替换 `append` 循环时，必须保持元素顺序、过滤条件与求值副作用。
- `Path.symlink_to` 的方向是 `link.symlink_to(target)`；测试在 Windows 上可能因权限跳过。

## 8. 验证命令

```bash
# 在 PyTeXLogs 根目录
uv run ruff check src tests
uv run ruff format --check src tests
uv run pytest tests -v

# 打包与独立安装验证
make whl
uv pip install --force-reinstall dist/*.whl
pytexlogs --version
```

如果没有 `uv`/`make`，可用项目 venv 的 Python 直接跑：

```powershell
# Windows venv 布局
& .\.venv\Scripts\python.exe -m pytest -q tests

# POSIX venv 布局
.venv/bin/python -m pytest -q tests
```

（先看实际目录，不要假定 `.venv` 一定是 `Scripts\python.exe` 还是 `bin/python`。）

涉及打包/独立导入时，必须验证：

1. wheel 能安装；
2. `import pytexlogs` 不依赖 PyTeXMK；
3. `pytexlogs --version` 与一个最小 `parse_log_file` 调用正常；
4. 没有把 `rich` 变成必需依赖。

## 9. 文档同步

- 公共 API、退出码、JSON/SARIF 字段变化：更新 `README.md` / `README.en.md` 与 `CHANGELOG.md`。
- 架构红线、parser 扩展方式、状态命名空间：更新本手册或新增 `docs/` 说明。
- 历史结论被后续轮次推翻时，加“后续状态”注记，不要留下与源码矛盾的旧结论。

## 10. 禁止事项

- 禁止 `from ..` 跳出子包、禁止 import PyTeXMK 主包模块。
- 禁止删除公共 API/别名而不保留迁移期兼容。
- 禁止绕过 `ProjectStateStore` 直接写状态 JSON。
- 禁止把 `rich` 从可选依赖提升为硬依赖。
- 不联网、不修改系统环境变量；不提交、不改用户文件，除非用户明确要求。
- 不用“改断言/改 fixture 期望”来掩盖解析行为回归；先确认是代码错还是样本错。
