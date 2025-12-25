#!/bin/bash
# システムコマンドプログレ用リンク作成スクリプト

TEMP_CLI_PATH="/home/pi/temperature_server/cli/management_cli.py"
CMD_LINK="/usr/local/bin/temp-manage"

if [ -f "$TEMP_CLI_PATH" ]; then
    sudo ln -sf "$TEMP_CLI_PATH" "$CMD_LINK"
    sudo chmod +x "$CMD_LINK"
    echo "✓ Created system command: temp-manage"
else
    echo "❌ CLI file not found: $TEMP_CLI_PATH"
    exit 1
fi
