#!/usr/bin/env bash
# PyTeXLogs 场景 3：本地 CLI 诊断。
# uv tool install --python 3.10 pytexlogs
# pytexlogs check ./build/main.log                  # 一行看 summary，ERROR 退出码=1
# pytexlogs summary ./main.log --lang en            # 英文摘要
# pytexlogs export --format csv ./logs -o report.csv # 批量 CSV 导出
# pytexlogs export --format sarif ./build -o out.sarif && gh upload-sarif out.sarif
# pytexlogs demo
echo "PASS: examples/cli_usage.sh (纯文档脚本)"
