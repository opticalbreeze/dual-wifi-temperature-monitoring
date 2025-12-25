"""
temperature_server/services/wifi_manager.py
WiFi ネットワーク管理 (AP + Station)
"""

import subprocess
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)

@dataclass
class NetworkInfo:
    """ネットワーク情報"""
    interface: str
    ssid: str
    ip_address: str
    signal_strength: int  # %
    status: str  # 'connected', 'disconnected', 'connecting'
    last_update: str

class WiFiManager:
    """WiFi ネットワーク管理クラス"""
    
    def __init__(self):
        self.ap_interface = Config.AP_INTERFACE  # wlan1
        self.station_interface = Config.STATION_INTERFACE  # wlan0
        self.ap_ssid = Config.AP_SSID
        self.ap_password = Config.AP_PASSWORD
        self.ap_ip = Config.AP_IP
    
    # ========== AP モード管理 ==========
    
    def setup_ap(self) -> bool:
        """AP モードをセットアップ"""
        try:
            logger.info(f"Setting up AP mode on {self.ap_interface}...")
            
            # 1. インターフェースを UP
            self._run_command(['sudo', 'ip', 'link', 'set', self.ap_interface, 'up'])
            
            # 2. 静的IP アドレスを設定
            self._run_command([
                'sudo', 'ip', 'addr', 'add',
                f'{self.ap_ip}/24',
                'dev', self.ap_interface
            ])
            
            # 3. dhcpcd を設定
            self._configure_dhcpcd_ap()
            
            # 4. hostapd を設定
            self._configure_hostapd()
            
            # 5. dnsmasq を設定
            self._configure_dnsmasq()
            
            # 6. iptables を設定（AP が UFW に遮られないように）
            self._setup_iptables()
            
            logger.info("✓ AP setup completed")
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to setup AP: {e}")
            return False
    
    def start_ap(self) -> bool:
        """AP サービスを開始"""
        try:
            logger.info("Starting AP services...")
            
            # hostapd と dnsmasq を開始
            self._run_command(['sudo', 'systemctl', 'start', 'hostapd'])
            self._run_command(['sudo', 'systemctl', 'start', 'dnsmasq'])
            
            logger.info("✓ AP services started")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to start AP: {e}")
            return False
    
    def stop_ap(self) -> bool:
        """AP サービスを停止"""
        try:
            logger.info("Stopping AP services...")
            self._run_command(['sudo', 'systemctl', 'stop', 'hostapd'])
            self._run_command(['sudo', 'systemctl', 'stop', 'dnsmasq'])
            logger.info("✓ AP services stopped")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to stop AP: {e}")
            return False
    
    def restart_ap(self) -> bool:
        """AP サービスを再起動"""
        return self.stop_ap() and self.start_ap()
    
    # ========== Station モード管理 ==========
    
    def scan_networks(self) -> List[Dict[str, any]]:
        """利用可能な WiFi ネットワークをスキャン"""
        try:
            logger.info(f"Scanning WiFi networks on {self.station_interface}...")
            
            # nmcli でスキャン
            result = subprocess.run(
                ['sudo', 'nmcli', 'dev', 'wifi', 'list'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            networks = []
            for line in result.stdout.split('\n')[1:]:  # ヘッダーをスキップ
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 3:
                    networks.append({
                        'ssid': parts[1],
                        'signal': int(parts[2].rstrip('%')),
                        'security': ' '.join(parts[3:]) if len(parts) > 3 else 'Open'
                    })
            
            logger.info(f"Found {len(networks)} networks")
            return networks
            
        except Exception as e:
            logger.error(f"Failed to scan networks: {e}")
            return []
    
    def connect_to_network(self, ssid: str, password: str, timeout: int = 30) -> bool:
        """WiFi ネットワークに接続"""
        try:
            logger.info(f"Connecting to {ssid}...")
            
            # nmcli で接続
            cmd = [
                'sudo', 'nmcli', 'device', 'wifi', 'connect',
                ssid, 'password', password, 'ifname', self.station_interface
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            
            if result.returncode == 0:
                logger.info(f"✓ Connected to {ssid}")
                return True
            else:
                logger.error(f"✗ Failed to connect to {ssid}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def disconnect_network(self) -> bool:
        """WiFi ネットワークから切断"""
        try:
            logger.info("Disconnecting from WiFi...")
            self._run_command(['sudo', 'nmcli', 'device', 'disconnect', self.station_interface])
            logger.info("✓ Disconnected")
            return True
        except Exception as e:
            logger.error(f"Failed to disconnect: {e}")
            return False
    
    # ========== ステータス確認 ==========
    
    def get_network_info(self, interface: str) -> Optional[NetworkInfo]:
        """ネットワーク情報を取得"""
        try:
            # IP アドレスを取得
            result = subprocess.run(
                ['ip', 'addr', 'show', interface],
                capture_output=True,
                text=True
            )
            
            ip_match = re.search(r'inet\s+([0-9.]+)', result.stdout)
            ip_address = ip_match.group(1) if ip_match else 'N/A'
            
            # SSID を取得（Station の場合）
            if interface == self.station_interface:
                result = subprocess.run(
                    ['/usr/sbin/iw', interface, 'link'],
                    capture_output=True,
                    text=True
                )
                ssid_match = re.search(r'SSID:\s+(\S+)', result.stdout)
                ssid = ssid_match.group(1) if ssid_match else 'Not connected'
            else:
                ssid = self.ap_ssid if interface == self.ap_interface else 'N/A'
            
            # シグナル強度を取得
            result = subprocess.run(
                ['/usr/sbin/iw', interface, 'link'],
                capture_output=True,
                text=True
            )
            signal_match = re.search(r'signal:\s+(-?\d+)\s+dBm', result.stdout)
            # dBm を % に変換 (-30dBm=100%, -90dBm=0%)
            if signal_match:
                dbm = int(signal_match.group(1))
                signal_strength = min(100, max(0, (dbm + 90) * 2))
            else:
                signal_strength = 0
            
            # ステータスを判定
            status = 'connected' if ip_address != 'N/A' else 'disconnected'
            
            return NetworkInfo(
                interface=interface,
                ssid=ssid,
                ip_address=ip_address,
                signal_strength=signal_strength,
                status=status,
                last_update=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Failed to get network info: {e}")
            return None
    
    def get_ap_status(self) -> Dict:
        """AP ステータスを取得"""
        try:
            info = self.get_network_info(self.ap_interface)
            if info:
                return {
                    'status': 'running',
                    'interface': info.interface,
                    'ssid': info.ssid,
                    'ip_address': info.ip_address,
                    'clients': self._count_connected_clients()
                }
            return {'status': 'stopped'}
        except Exception as e:
            logger.error(f"Failed to get AP status: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def get_station_status(self) -> Dict:
        """Station ステータスを取得"""
        try:
            info = self.get_network_info(self.station_interface)
            if info:
                return {
                    'status': info.status,
                    'interface': info.interface,
                    'ssid': info.ssid,
                    'ip_address': info.ip_address,
                    'signal_strength': info.signal_strength
                }
            return {'status': 'unknown'}
        except Exception as e:
            logger.error(f"Failed to get station status: {e}")
            return {'status': 'error', 'message': str(e)}
    
    # ========== ヘルスチェック ==========
    
    def health_check(self) -> Dict:
        """WiFi システムのヘルスチェック"""
        try:
            ap_status = self.get_ap_status()
            station_status = self.get_station_status()
            
            health = {
                'timestamp': datetime.now().isoformat(),
                'ap': ap_status,
                'station': station_status,
                'overall': 'healthy'
            }
            
            # AP が停止している場合
            if ap_status.get('status') != 'running':
                logger.warning("AP is not running, attempting to restart...")
                self.restart_ap()
                health['overall'] = 'warning'
            
            # Station が接続されていない場合
            if station_status.get('status') == 'disconnected':
                logger.warning("Station is disconnected")
                health['overall'] = 'warning'
            
            return health
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'overall': 'error',
                'message': str(e)
            }
    
    # ========== プライベートメソッド ==========
    
    def _run_command(self, cmd: List[str], timeout: int = 10) -> str:
        """コマンドを実行"""
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            raise RuntimeError(f"Command failed: {result.stderr}")
        return result.stdout
    
    def _configure_dhcpcd_ap(self):
        """dhcpcd を AP 用に設定"""
        dhcpcd_config = f"""
interface {self.ap_interface}
static ip_address={self.ap_ip}/24
nohook wpa_supplicant
"""
        config_file = Path('/etc/dhcpcd.conf')
        if config_file.exists():
            content = config_file.read_text()
            # 既存の設定を削除
            content = re.sub(
                rf'interface {self.ap_interface}.*?nohook wpa_supplicant\n',
                '',
                content,
                flags=re.DOTALL
            )
            content += '\n' + dhcpcd_config
            config_file.write_text(content)
            logger.info("✓ dhcpcd configured for AP")
    
    def _configure_hostapd(self):
        """hostapd を AP 用に設定"""
        hostapd_config = f"""
interface={self.ap_interface}
driver=nl80211
ssid={self.ap_ssid}
hw_mode=g
channel=6
wmm_enabled=1
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase={self.ap_password}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=CCMP
wpa_group_rekey=86400
"""
        config_file = Path('/etc/hostapd/hostapd.conf')
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(hostapd_config)
        logger.info("✓ hostapd configured")
    
    def _configure_dnsmasq(self):
        """dnsmasq を DHCP サーバー用に設定"""
        dnsmasq_config = f"""
interface={self.ap_interface}
dhcp-range={Config.AP_DHCP_START},{Config.AP_DHCP_END},255.255.255.0,24h
server=8.8.8.8
server=8.8.4.4
"""
        config_file = Path('/etc/dnsmasq.conf')
        if config_file.exists():
            content = config_file.read_text()
            # AP 関連の設定を削除
            content = re.sub(rf'interface={self.ap_interface}.*?(?=\n[a-z]|\Z)', '', content, flags=re.DOTALL)
            content = re.sub(rf'dhcp-range=.*?\n', '', content)
            content += '\n' + dnsmasq_config
            config_file.write_text(content)
            logger.info("✓ dnsmasq configured")
    
    def _setup_iptables(self):
        """IP テーブルを設定（NAT）"""
        try:
            # AP (wlan1) から Station (wlan0) へのフォワード（ESP32 → インターネット）
            self._run_command([
                'sudo', 'iptables', '-A', 'FORWARD',
                '-i', self.ap_interface,
                '-o', self.station_interface,
                '-j', 'ACCEPT'
            ])
            
            # Station (wlan0) から AP (wlan1) へのフォワード（応答パケット）
            self._run_command([
                'sudo', 'iptables', '-A', 'FORWARD',
                '-i', self.station_interface,
                '-o', self.ap_interface,
                '-m', 'state', '--state', 'RELATED,ESTABLISHED',
                '-j', 'ACCEPT'
            ])
            
            # NAT 設定（Station インターフェース経由でインターネットへ）
            self._run_command([
                'sudo', 'iptables', '-t', 'nat',
                '-A', 'POSTROUTING',
                '-o', self.station_interface,
                '-j', 'MASQUERADE'
            ])
            
            logger.info("✓ iptables configured")
        except Exception as e:
            logger.warning(f"iptables setup: {e}")
    
    def _count_connected_clients(self) -> int:
        """接続中のクライアント数をカウント"""
        try:
            result = subprocess.run(
                ['sudo', '/usr/sbin/iw', self.ap_interface, 'station', 'dump'],
                capture_output=True,
                text=True,
                timeout=5
            )
            # MAC アドレス行の数 = クライアント数
            return len([line for line in result.stdout.split('\n') if line.startswith('Station')])
        except:
            return 0
