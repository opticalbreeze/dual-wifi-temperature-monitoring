#!/bin/bash
# ラズパイ WiFi AP セットアップ自動スクリプト
# 使用方法: bash setup_ap.sh
# 注意: フリーWiFiへの接続スクリプトは別途実行済みであることを前提とします

set -e

echo "================================"
echo "ラズパイ WiFi AP セットアップ"
echo "================================"
echo ""

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# チェック関数
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}❌ このスクリプトは sudo で実行してください${NC}"
        echo "使用方法: sudo bash setup_ap.sh"
        exit 1
    fi
}

# ステップ1: root確認
check_root

echo -e "${GREEN}✅ root で実行中${NC}"
echo ""

# ステップ2: パッケージ更新
echo -e "${YELLOW}📦 パッケージをインストール中...${NC}"
apt-get update -qq
apt-get install -y -qq dnsmasq hostapd

echo -e "${GREEN}✅ パッケージインストール完了${NC}"
echo ""

# ステップ3: hostapd 設定
echo -e "${YELLOW}⚙️ hostapd を設定中...${NC}"

cat > /etc/hostapd/hostapd.conf << 'EOF'
# WiFi インターフェース設定
interface=wlan1
driver=nl80211

# SSID と パスワード設定
ssid=RaspberryPi_Temperature
hw_mode=g
channel=6
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0

# WiFi セキュリティ設定
wpa=2
wpa_passphrase=RaspberryPi2025
wpa_key_mgmt=WPA-PSK
wpa_pairwise=CCMP
wpa_ptk_rekey=600
EOF

echo -e "${GREEN}✅ hostapd 設定完了${NC}"
echo ""

# ステップ4: dnsmasq 設定
echo -e "${YELLOW}⚙️ dnsmasq を設定中...${NC}"

# dnsmasq.conf をバックアップ
cp /etc/dnsmasq.conf /etc/dnsmasq.conf.bak

# AP用設定を追加
cat >> /etc/dnsmasq.conf << 'EOF'

# AP インターフェース設定
interface=wlan1
dhcp-range=192.168.4.2,192.168.4.254,255.255.255.0,24h
dhcp-option=option:router,192.168.4.1
dhcp-option=option:dns-server,8.8.8.8,8.8.4.4
EOF

echo -e "${GREEN}✅ dnsmasq 設定完了${NC}"
echo ""

# ステップ5: dhcpcd 設定
echo -e "${YELLOW}⚙️ dhcpcd を設定中...${NC}"

cat >> /etc/dhcpcd.conf << 'EOF'

# wlan1 (AP インターフェース) の設定
interface wlan1
static ip_address=192.168.4.1/24
nohook wpa_supplicant
EOF

echo -e "${GREEN}✅ dhcpcd 設定完了${NC}"
echo ""

# ステップ6: IP フォワーディング有効化
echo -e "${YELLOW}⚙️ IP フォワーディングを有効化中...${NC}"

sed -i 's/^#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/' /etc/sysctl.conf
sysctl -p > /dev/null 2>&1

echo -e "${GREEN}✅ IP フォワーディング有効化完了${NC}"
echo ""

# ステップ7: iptables ルール設定
echo -e "${YELLOW}⚙️ iptables ルールを設定中...${NC}"

iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE 2>/dev/null || true
iptables -A FORWARD -i wlan1 -o wlan0 -j ACCEPT 2>/dev/null || true
iptables -A FORWARD -i wlan0 -o wlan1 -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true

iptables-save > /etc/iptables.ipv4.nat

echo -e "${GREEN}✅ iptables ルール設定完了${NC}"
echo ""

# ステップ8: rc.local にiptables ルール復元を追加
echo -e "${YELLOW}⚙️ rc.local を設定中...${NC}"

if ! grep -q "iptables-restore" /etc/rc.local; then
    sed -i '/exit 0/i iptables-restore < /etc/iptables.ipv4.nat' /etc/rc.local
fi

echo -e "${GREEN}✅ rc.local 設定完了${NC}"
echo ""

# ステップ9: サービス自動起動を有効化
echo -e "${YELLOW}🔧 サービスを設定中...${NC}"

systemctl unmask hostapd 2>/dev/null || true
systemctl enable hostapd 2>/dev/null || true
systemctl enable dnsmasq 2>/dev/null || true

echo -e "${GREEN}✅ サービス設定完了${NC}"
echo ""

# ステップ10: WiFi インターフェース確認
echo -e "${YELLOW}🔍 WiFi インターフェースを確認中...${NC}"
echo ""

WLAN1_EXISTS=$(ifconfig wlan1 2>/dev/null || echo "")

if [ -z "$WLAN1_EXISTS" ]; then
    echo -e "${YELLOW}⚠️  wlan1 が見つかりません。以下を確認してください：${NC}"
    echo ""
    echo "1. USB WiFi ドングルが接続されているか確認："
    echo "   lsusb"
    echo ""
    echo "2. 接続可能なインターフェース一覧："
    ifconfig -a | grep "wlan" || echo "   (WiFi インターフェースが見つかりません)"
    echo ""
    echo "3. 見つかった場合は、setup_ap.sh 内の interface=wlan1 を"
    echo "   見つかったインターフェース名に変更してください"
    echo ""
else
    echo -e "${GREEN}✅ wlan1 が確認できました${NC}"
fi

echo ""
echo "================================"
echo -e "${GREEN}✅ セットアップ完了！${NC}"
echo "================================"
echo ""
echo "📋 次のステップ："
echo ""
echo "1️⃣ ラズパイを再起動："
echo "   sudo reboot"
echo ""
echo "2️⃣ 再起動後、WiFi AP が起動しているか確認："
echo "   sudo systemctl status hostapd"
echo "   sudo systemctl status dnsmasq"
echo ""
echo "3️⃣ WiFi インターフェース確認："
echo "   ifconfig wlan1"
echo ""
echo "4️⃣ Flask サーバーを起動："
echo "   python3 /home/pi/temperature_server/server.py"
echo ""
echo "================================"
echo ""
