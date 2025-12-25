"""
temperature_server/cli/management_cli.py
コマンドラインインターフェース (ワンクリック操作)
"""

import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# プロジェクトルートを追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import Config
from database.queries import TemperatureQueries, SystemLogQueries
from services.wifi_manager import WiFiManager

class CLIManager:
    
    @staticmethod
    def wifi_scan():
        """利用可能なWiFiネットワークをスキャン"""
        print("📡 WiFi ネットワークをスキャン中...")
        wifi_manager = WiFiManager()
        networks = wifi_manager.scan_networks()
        
        if networks:
            print(f"\n✓ Found {len(networks)} networks:\n")
            for net in networks:
                print(f"  SSID: {net['ssid']}")
                print(f"  Signal: {net['signal']}%")
                print(f"  Security: {net['security']}\n")
        else:
            print("❌ No networks found")
    
    @staticmethod
    def wifi_connect():
        """WiFi ネットワークに接続"""
        ssid = input("SSID: ")
        password = input("Password: ")
        
        print(f"🔗 Connecting to {ssid}...")
        wifi_manager = WiFiManager()
        success = wifi_manager.connect_to_network(ssid, password)
        
        if success:
            print(f"✓ Connected to {ssid}")
        else:
            print(f"❌ Failed to connect to {ssid}")
    
    @staticmethod
    def wifi_status():
        """WiFi接続状況を表示"""
        print("🔗 WiFi ステータス:")
        wifi_manager = WiFiManager()
        
        print("\n[AP モード]")
        ap_status = wifi_manager.get_ap_status()
        print(f"  Status: {ap_status.get('status')}")
        print(f"  SSID: {ap_status.get('ssid')}")
        print(f"  IP: {ap_status.get('ip_address')}")
        print(f"  Clients: {ap_status.get('clients', 0)}")
        
        print("\n[Station モード]")
        station_status = wifi_manager.get_station_status()
        print(f"  Status: {station_status.get('status')}")
        print(f"  SSID: {station_status.get('ssid')}")
        print(f"  IP: {station_status.get('ip_address')}")
        print(f"  Signal: {station_status.get('signal_strength', 0)}%")
    
    @staticmethod
    def restart_services():
        """全サービスを再起動"""
        print("🔄 サービス再起動中...")
        services = ['hostapd', 'dnsmasq']
        for service in services:
            try:
                subprocess.run(['sudo', 'systemctl', 'restart', service], check=True)
                print(f"✓ {service} 再起動完了")
            except Exception as e:
                print(f"❌ {service} 再起動失敗: {e}")
    
    @staticmethod
    def ap_start():
        """AP を開始"""
        print("🔌 AP を開始中...")
        wifi_manager = WiFiManager()
        success = wifi_manager.start_ap()
        if success:
            print("✓ AP を開始しました")
        else:
            print("❌ AP 開始失敗")
    
    @staticmethod
    def ap_stop():
        """AP を停止"""
        print("🔌 AP を停止中...")
        wifi_manager = WiFiManager()
        success = wifi_manager.stop_ap()
        if success:
            print("✓ AP を停止しました")
        else:
            print("❌ AP 停止失敗")
    
    @staticmethod
    def ap_restart():
        """AP を再起動"""
        print("🔄 AP を再起動中...")
        wifi_manager = WiFiManager()
        success = wifi_manager.restart_ap()
        if success:
            print("✓ AP を再起動しました")
        else:
            print("❌ AP 再起動失敗")
    
    @staticmethod
    def memory_status():
        """メモリ使用状況を表示"""
        print("💾 メモリ使用状況:")
        try:
            result = subprocess.run(['free', '-h'], capture_output=True, text=True)
            print(result.stdout)
            
            # psutil を使用した詳細情報
            try:
                import psutil
                mem = psutil.virtual_memory()
                print(f"\n詳細: 使用率 {mem.percent}% (警告: {Config.MEMORY_THRESHOLD}%)")
                if mem.percent >= Config.MEMORY_THRESHOLD:
                    print("⚠️  メモリ警告: キャッシュ削除を推奨")
            except ImportError:
                pass
        except Exception as e:
            print(f"❌ 取得失敗: {e}")
    
    @staticmethod
    def disk_status():
        """ディスク使用状況を表示"""
        print("📊 ディスク使用状況:")
        try:
            result = subprocess.run(['df', '-h'], capture_output=True, text=True)
            print(result.stdout)
        except Exception as e:
            print(f"❌ 取得失敗: {e}")
    
    @staticmethod
    def system_status():
        """システム全体のステータスを表示"""
        print("=" * 50)
        print("🖥️  システム全体ステータス")
        print("=" * 50)
        CLIManager.memory_status()
        print("\n")
        CLIManager.disk_status()
        print("\n")
        CLIManager.wifi_status()
    
    @staticmethod
    def temperature_stats():
        """温度統計を表示"""
        print("\n📈 温度データ統計:")
        try:
            # 全センサーの最新データ
            readings = TemperatureQueries.get_all_latest()
            if readings:
                print(f"\n検出センサー数: {len(readings)}")
                for reading in readings:
                    stats = TemperatureQueries.get_statistics(reading['sensor_id'])
                    print(f"\n[{reading['sensor_name'] or reading['sensor_id']}]")
                    print(f"  現在: {reading['temperature']}°C")
                    print(f"  平均: {stats['avg_temp']:.1f}°C")
                    print(f"  最小: {stats['min_temp']:.1f}°C")
                    print(f"  最大: {stats['max_temp']:.1f}°C")
                    print(f"  データ数: {stats['count']}")
            else:
                print("❌ センサーデータが見つかりません")
        except Exception as e:
            print(f"❌ エラー: {e}")
    
    @staticmethod
    def clear_cache():
        """キャッシュとログをクリア"""
        print("🧹 キャッシュをクリア中...")
        try:
            # ページキャッシュをドロップ
            subprocess.run(['sudo', 'sync'], check=True)
            subprocess.run(['sudo', 'sysctl', '-w', 'vm.drop_caches=3'], check=True)
            print("✓ キャッシュをクリアしました")
        except Exception as e:
            print(f"⚠️  警告: {e}")
    
    @staticmethod
    def reboot():
        """システム再起動（確認付き）"""
        confirm = input("⚠️  本当に再起動しますか? (yes/no): ")
        if confirm.lower() == 'yes':
            print("🔄 30秒後に再起動します...")
            subprocess.run(['sudo', 'shutdown', '-r', '+1'])
        else:
            print("キャンセルしました")
    
    @staticmethod
    def init_database():
        """データベースを初期化"""
        print("🗄️  データベースを初期化中...")
        try:
            from database.models import init_database
            init_database()
            print("✓ データベースを初期化しました")
        except Exception as e:
            print(f"❌ 失敗: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="🔧 Raspberry Pi 温度サーバー管理ツール"
    )
    subparsers = parser.add_subparsers(dest='command', help='コマンド')
    
    # WiFi コマンド
    subparsers.add_parser('wifi-scan', help='WiFi ネットワークをスキャン')
    subparsers.add_parser('wifi-status', help='WiFi 接続状況を表示')
    subparsers.add_parser('wifi-connect', help='WiFi ネットワークに接続')
    
    # AP コマンド
    subparsers.add_parser('ap-start', help='WiFi AP を開始')
    subparsers.add_parser('ap-stop', help='WiFi AP を停止')
    subparsers.add_parser('ap-restart', help='WiFi AP を再起動')
    
    # サービスコマンド
    subparsers.add_parser('restart', help='全サービスを再起動')
    
    # ステータスコマンド
    subparsers.add_parser('status', help='システム全体ステータスを表示')
    subparsers.add_parser('memory', help='メモリ使用状況を表示')
    subparsers.add_parser('disk', help='ディスク使用状況を表示')
    subparsers.add_parser('temp', help='温度統計を表示')
    
    # メンテナンスコマンド
    subparsers.add_parser('clear-cache', help='キャッシュをクリア')
    subparsers.add_parser('reboot', help='システムを再起動')
    subparsers.add_parser('init-db', help='データベースを初期化')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # コマンド実行
    if args.command == 'wifi-scan':
        CLIManager.wifi_scan()
    elif args.command == 'wifi-status':
        CLIManager.wifi_status()
    elif args.command == 'wifi-connect':
        CLIManager.wifi_connect()
    elif args.command == 'ap-start':
        CLIManager.ap_start()
    elif args.command == 'ap-stop':
        CLIManager.ap_stop()
    elif args.command == 'ap-restart':
        CLIManager.ap_restart()
    elif args.command == 'restart':
        CLIManager.restart_services()
    elif args.command == 'status':
        CLIManager.system_status()
    elif args.command == 'memory':
        CLIManager.memory_status()
    elif args.command == 'disk':
        CLIManager.disk_status()
    elif args.command == 'temp':
        CLIManager.temperature_stats()
    elif args.command == 'clear-cache':
        CLIManager.clear_cache()
    elif args.command == 'reboot':
        CLIManager.reboot()
    elif args.command == 'init-db':
        CLIManager.init_database()
        CLIManager.reboot()
    elif args.command == 'init-db':
        CLIManager.init_database()

if __name__ == '__main__':
    main()
