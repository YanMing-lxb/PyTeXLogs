# Changelog

## v0.4.0 - 2026-10-18

### 破坏性变更
- **最低 Python 版本提升到 3.15**：`requires-python` 从 `>=3.14` 改为 `>=3.15`；CI 矩阵由 `3.10–3.14` 收敛为 `3.15`（原矩阵与 `requires-python` 本就矛盾，3.10–3.13 的 job 无法安装本包）
- **状态文件格式升级到 schema v3，不兼容旧版**：`.pytexmk_refcache.json` 由"扁平结构"改为"命名空间结构"。旧版 PyTeXLogs 读写新文件、或新版读旧文件，都会得到空的引用缓存（表现为"首次运行，新增 N 篇"）。此取舍是为了让文件结构只有一种形态，避免长期维护双写逻辑

### 新增
- **`ProjectStateStore`：单文件多命名空间状态存储**（`pytexlogs.core.state`，已加入公共 API）
  - 解决的问题：多个工具共用一个状态文件时，"整文件覆写"会导致后写者抹掉先写者。改造前 `RefChangeTracker.save_cache()` 就是整文件覆写，PyTeXMK 想持久化任何构建状态都会被冲掉
  - 做法：每个写入者只拥有自己的顶层键（`pytexlogs` / `pytexmk` / 第三方），写入时**读-改-写**，只替换自己命名空间内的键
  - **原子写**：同目录临时文件 + `os.replace`，Ctrl+C 中断不会留下半截 JSON
  - **轻量文件锁**：`O_CREAT | O_EXCL` 哨兵 + 超时降级（拿不到锁就跳过本次写入，最多退化为下次多编一轮，绝不阻塞或报错）；30 秒以上的陈旧锁会被自动清理
  - **容错**：文件缺失 / JSON 损坏 / 顶层非对象 / schema 版本不符，一律降级为空骨架，不删除文件、不中断主流程
  - 公共方法：`load` / `get_namespace` / `update_namespace` / `replace_namespace` / `get_build` / `update_build` / `get_refs` / `update_refs` / `clear`

### 变更
- **`RefChangeTracker` 改用 `ProjectStateStore`**：`load_cache()` / `load_cache_counts()` / `save_cache()` 读写 `pytexlogs.refs` 命名空间，不再整文件覆写。`self.cache_path` 保留以兼容外部读取路径
- `pytexlogs.__init__` 新增导出：`ProjectStateStore`、`PROJECT_STATE_FILENAME`、`SCHEMA_VERSION`、`StateFileCorrupted`
- `pyproject.toml`：`tool.ruff` 增加 `target-version = "py315"`；`tool.mypy.python_version` 改为 `"3.15"`；classifier 改为 `Python :: 3.15`

### 新增文件
- 状态文件结构（schema v3）：
  ```jsonc
  {
    "schema_version": 3,
    "timestamp": "2026-10-18T13:59:04+08:00",
    "pytexlogs": { "refs": { "keys": [...], "key_counts": {...} } },
    "pytexmk":   { "build": { "fingerprint": "...", "artifacts": {...}, "sources": {...} } },
    "jobs":      { "main": { "updated_at": "..." } }
  }
  ```

### 测试
- 新增 `tests/test_state_store.py`（19 例）：命名空间隔离、v2 丢弃、v3 自动升级、原子写无残留、锁释放、并发交替写、坏 JSON 降级、`clear()` 幂等
- 全量：**100 passed, 1 skipped**（Python 3.15.0）
- 端到端验证：`run_pipeline()` 写入 `pytexlogs.refs` 后，预先放在 `pytexmk.build` 里的数据原样保留

---

## v0.3.0 - 2026-08-04

### 架构重构
- 按功能模块重新组织代码：core/、parsers/、cli/、display/、exporters/、utils/
- 消除薄层转发层，简化调用链
- formatter 与 printer 分离为独立模块，支持 GUI/Web 输出

### Python 3.14 兼容性
- 移除所有 `from __future__` 兼容性残留
- 全面采用现代类型注解（`|` 联合类型）
- 使用 `datetime.UTC`、`slots=True` 等新特性
- requires-python 更新为 `>=3.14`

### 功能改进
- 10 种日志解析器功能完善（LaTeX、BibTeX、Biber、Makeindex、Xindy、Glossaries、Nomencl、PythonTeX、Minted、Asymptote）
- SARIF 导出符合 v2.1.0 规范
- Minted 解析器添加高亮计数检测
- Nomencl 解析器支持 Warning-- 格式
- LaTeX 解析器修复 assert 语句安全问题
- 参考文献追踪修复首次运行判断逻辑
- 报告加载添加异常处理
- 解析器注册冲突添加警告日志

### 代码质量
- ruff 检查通过，无 E/F 级别错误
- 类型注解完整
- 文档字符串清晰

## v0.2.0 - 2026-08-01

### FR-1: Public API 命名分层 + 兼容别名
新增 run_pipeline / Manager / Registry / Report 四个高频短别名；run_log_pipeline 等旧名通过 DeprecationWarning 向后兼容；__all__ 按「便捷 API / 解析器 / 数据结构 / 常量 / 解析器类 / 演示」六段注释清晰分层。

### FR-2: 类型注解完整补齐 + mypy --strict 通关
所有公共函数、私有变量、11 个 *Parser 子类签名严格对齐 BaseLogParser；pyproject.toml [tool.mypy] 配置 strict=true、python_version="3.10"，mypy --strict src/pytexlogs 零错误。

### FR-3: 高阶便捷函数组（一行搞定常见场景）
新增 easy.py 五个顶层函数：parse_log_file（按后缀自猜 parser）、parse_log_text（captured_outputs 场景）、parse_auxdir（整辅助目录扫描）、filter_severity（按严重度裁剪条目）、aggregate_stats（category/level/parser 分组统计）。

### FR-4: 统计聚合 API
aggregate_stats(obj, group_by="category" | "level" | "parser") 接受 ParsedPipelineReport | list[ToolResult]，返回直方图 dict，可直接用于 CLI 打印或可视化。

### FR-5: 三种结构化导出（JSON / CSV / SARIF）
在 _report.py 新增 to_json / to_csv / to_sarif 三个公共函数；SARIF 为 v2.1.0 最小子集，可直接喂 GitHub Code Scanning；CSV 严格表头 file,line,level,category,tool,text,hint,source_path。

### FR-6: Entry Point 插件化机制
LogParserRegistry.get_default_registry() 首次构造时自动扫描 pytexlogs.parsers Entry Point 组；外部包可在自己 pyproject.toml 中注册自定义解析器，无需改动 pytexlogs 源码。

### FR-7: CLI（argparse）开箱即用
新增 pytexlogs = "pytexlogs.cli:main" 入口脚本，支持全局 --version / --lang / --format / --output / --severity / --root-file / --open / --editor 参数；退出码 0=无 error，1=有 error，2=参数/IO 错。

### FR-8: 编辑器跳转打开能力
--open + --editor auto|code|subl|nvim|gvim|custom:<template>，自动按 VISUAL > EDITOR > code > subl > nvim > gvim 优先级选编辑器，失败仅 warning 不中断；支持 %f:%l 模板替换。

### FR-9: i18n 可插拔翻译（中英文摘要）
set_summary_language(lang, translate_fn=None) 全局切换；CLI --lang zh/en 直接生效；translate_fn 参数允许注入任意自定义翻译逻辑，无 gettext 依赖。

### FR-10: summary 子命令
pytexlogs summary [LOG ...] 等价 check 但专注摘要输出，忽略退出码；检测到 rich 时用 rich.table 彩色表格，无 rich 退化为纯文本对齐。

### FR-11: export 子命令
pytexlogs export --format=json|csv|sarif LOG/DIR --output PATH 一步生成结构化报告；--output 缺省则打印到 stdout，方便 shell 管道。

### FR-12: filter_severity 便捷过滤
filter_severity(entries, min_level=WARNING) 利用 LogLevel.__lt__ 比较，一行保留 min_level 以上条目，常用于 CI 告警筛选。

本次共实现 49 条公共 API；新增 check / summary / export / demo 四类 CLI 子命令；wheel 体积控制在 <= 70KB；requires-python>=3.10 提高 PyPI 覆盖率。

## v0.1.0 - 2026-07-30

- 新增：从 PyTeXMK v1.1.0 抽离日志解析子包为独立 PyPI 库 pytexlogs
- 改进：移除对 pytexmk.* 的反向依赖，成为纯标准库可运行的包；独立库 logger 名改为 pytexlogs
- 测试：独立命名空间 B 验证（NFR-3）4 PASS，可单独解析 LaTeX/BibTeX 等日志
