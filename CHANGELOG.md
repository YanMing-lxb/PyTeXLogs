# Changelog

## v0.1.0 - 2026-07-30

- 🎉 新增：从 PyTeXMK v1.1.0 抽离日志解析子包为独立 PyPI 库 `pytexlogs`
- 🚀 改进：移除对 `pytexmk.*` 的反向依赖，成为纯标准库可运行的包；独立库 logger 名改为 `pytexlogs`（见 spec Q1）
- 🧪 测试：独立命名空间 B 验证（NFR-3）4 PASS，可单独解析 LaTeX/BibTeX 等日志
