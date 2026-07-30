# ==============================================================================
# PyTeXLogs Makefile - 项目构建与开发自动化脚本
# ==============================================================================
# 使用方法：make <目标>
# 示例：
#   make test    - 运行测试套件
#   make lint    - 代码风格检查
#   make whl     - 构建 wheel 分发包
#   make help    - 显示所有可用目标及说明
# ==============================================================================

.DEFAULT_GOAL := help

ifeq ($(OS),Windows_NT)
SHELL := cmd.exe
endif

help:
	@echo PyTeXLogs - Available targets:
	@echo   help     Show this help message
	@echo   test     Run pytest test suite (uv run pytest tests -v)
	@echo   lint     Run ruff code style check (uv run ruff check src)
	@echo   whl      Clean then build Python wheel distribution (uv build)
	@echo   inswhl   Build whl then force-reinstall locally (pip install --force-reinstall)
	@echo   clean    Remove all build artifacts (dist, build, __pycache__, *.pyc, .pytest_cache)
	@echo   upload   Upload dist/* to PyPI via twine (twine upload dist/*)

test:
	uv run pytest tests -v

lint:
	uv run ruff check src

whl: clean
	uv build

inswhl: whl
	pip install --force-reinstall dist/pytexlogs-0.1.0-py3-none-any.whl

clean:
	-@if exist dist rmdir /s /q dist
	-@if exist build rmdir /s /q build
	-@if exist srcpyd rmdir /s /q srcpyd
	-@if exist .pytest_cache rmdir /s /q .pytest_cache
	-@if exist ruff_cache rmdir /s /q ruff_cache
	-@for /d /r %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
	-@del /s /q *.pyc 2>nul
	-@del /s /q *.pyo 2>nul
	-@del /s /q *.pyd 2>nul

# NOTE: 需要用户自行安装 twine: pip install twine
upload:
	twine upload dist/*
