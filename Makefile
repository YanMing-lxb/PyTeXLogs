# ==============================================================================
# PyTeXLogs Makefile - 项目构建与开发自动化脚本
# ==============================================================================
# 使用方法：make <目标>
# 示例：
#   make test    - 运行 pytest 测试套件
#   make lint    - 运行 ruff 代码风格检查
#   make whl     - 先清理再构建 wheel + sdist 分发包
#   make help    - 显示所有可用目标及说明
# ==============================================================================

# 默认目标：显示帮助
.DEFAULT_GOAL := help

# Windows 下使用 cmd 作为 shell（确保 echo 等内置命令可用）
ifeq ($(OS),Windows_NT)
SHELL := cmd.exe
endif

# ------------------------------------------------------------------------------
# 帮助信息
# ------------------------------------------------------------------------------
help:
	@echo PyTeXLogs - Available targets:
	@echo   help     Show this help message
	@echo   test     Run pytest test suite (uv run pytest tests -v)
	@echo   lint     Run ruff code style check (uv run ruff check src)
	@echo   whl      Clean then build Python distribution (wheel + sdist)
	@echo   inswhl   Build whl then force-reinstall locally (pip install --force-reinstall)
	@echo   clean    Remove all build artifacts (dist, build, __pycache__, *.pyc, .pytest_cache)
	@echo   upload   Create and push git tag for release (PyPI publishing via CI Release.yml)

# ------------------------------------------------------------------------------
# 开发相关目标
# ------------------------------------------------------------------------------

test:
	uv run pytest tests -v

lint:
	uv run ruff check src

# ------------------------------------------------------------------------------
# 构建 / 清理 / 安装 / 发布（全部委托给 ./tools/make.py，与 PyTeXMK UX 对齐）
# ------------------------------------------------------------------------------

whl:
	@uv run python ./tools/make.py whl

inswhl:
	@uv run python ./tools/make.py inswhl

clean:
	@uv run python ./tools/make.py clean

upload:
	@uv run python ./tools/make.py upload
