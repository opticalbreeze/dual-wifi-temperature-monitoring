#!/usr/bin/env python3
"""
GitHub Push Helper Script
This script initializes git, commits all files, and pushes to GitHub.
"""

import subprocess
import os
import sys
from pathlib import Path

def run_command(cmd, description=""):
    """Run a shell command and report results."""
    if description:
        print(f"\n{'=' * 50}")
        print(f"▶ {description}")
        print(f"{'=' * 50}")
    
    print(f"$ {cmd}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        if result.returncode != 0:
            print(f"⚠ Command exited with code {result.returncode}")
        else:
            print("✓ Success")
        
        return result.returncode == 0
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return False

def main():
    """Main function."""
    
    print("=" * 50)
    print("デュアル WiFi 温度監視システム")
    print("GitHub Push スクリプト")
    print("=" * 50)
    
    # Repository path
    repo_path = Path("i:/ESP32DS18/raspberry_pi/temperature_server")
    if not repo_path.exists():
        repo_path = Path("./")  # Fallback to current directory
    
    print(f"\nリポジトリパス: {repo_path.absolute()}")
    
    # Change to repository directory
    os.chdir(repo_path)
    
    # Initialize git
    if not (repo_path / ".git").exists():
        run_command("git init", "Git リポジトリを初期化")
        run_command("git config user.name 'Temperature Server Developer'", "ユーザー名を設定")
        run_command("git config user.email 'opticalbreeze@github.com'", "メールアドレスを設定")
    else:
        print("\n✓ Git リポジトリは既に初期化されています")
    
    # Check git status
    run_command("git status", "現在のステータスを確認")
    
    # Stage all files
    run_command("git add -A", "ファイルをステージング")
    
    # Create commit
    commit_message = """Initial commit: Complete dual WiFi temperature monitoring system with comprehensive documentation

- 7 comprehensive markdown documents
- Complete Raspberry Pi dual WiFi setup guide  
- RTL8821AU driver installation instructions
- Flask REST API server implementation
- SQLite database with persistent storage
- Real-time web dashboard
- ESP32 microcontroller implementation guide
- 10 lessons learned from 6+ hour development crisis
- Detailed troubleshooting guide"""
    
    run_command(f'git commit -m "{commit_message}"', "コミットを作成")
    
    # Setup remote
    run_command("git remote remove origin 2>nul || true", "既存のリモートを削除")
    run_command("git remote add origin https://github.com/opticalbreeze/dual-wifi-temperature-monitoring.git", 
                "GitHub リモートを追加")
    
    # Ensure main branch
    run_command("git branch -M main", "メインブランチを確認")
    
    # Push to GitHub
    success = run_command("git push -u origin main -v", "GitHub にプッシュ")
    
    # Final message
    print("\n" + "=" * 50)
    if success:
        print("✓ プッシュ完了！")
        print("=" * 50)
        print("\nリポジトリ URL:")
        print("https://github.com/opticalbreeze/dual-wifi-temperature-monitoring")
    else:
        print("✗ プッシュに失敗しました")
        print("=" * 50)
        print("\n以下を確認してください:")
        print("1. GitHub の認証情報が正しいか")
        print("2. リポジトリが存在するか")
        print("3. ネットワーク接続があるか")
    
    print()

if __name__ == "__main__":
    main()
