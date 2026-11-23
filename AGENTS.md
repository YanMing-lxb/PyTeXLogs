# AGENTS.md

本仓库的代码修改约定集中在 [`docs/code-modification-playbook.md`](docs/code-modification-playbook.md)。

## 开始前

1. 先读 `src/pytexlogs/__init__.py` 的架构注释、`__all__` 与 `docs/code-modification-playbook.md`。
2. 先跑基线：`uv run ruff check src tests`、`uv run pytest tests -v`。
3. 确认本次是行为修复、公共 API 变更、parser 输出变更，还是纯风格清理。

## 硬约束

- PyTeXLogs 必须能作为**顶级包**独立导入；禁止跳出子包的 `from ..`，禁止 import PyTeXMK 主包模块。
- 外部使用走 `__all__` 公共 API；不要新增薄转发文件。
- `ProjectStateStore` 负责状态读写；不要直接写 JSON，也不要覆盖其它命名空间。
- 解析输出、JSON/SARIF 字段、CLI 退出码是契约；改之前先看 fixtures 与对应测试。
- `rich` 只能是可选依赖。
- 不联网、不修改系统环境变量、不提交，除非用户明确要求。

## 验证

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run pytest tests -v
make whl
```

涉及公共 API 或解析结果时，必须补定向测试；涉及打包时，安装 wheel 后验证
`import pytexlogs` 与 `pytexlogs --version` 不依赖 PyTeXMK。
