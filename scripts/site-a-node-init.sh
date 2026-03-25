#!/bin/bash

# =================================================================
# Project: Hybrid-Cloud (Phase 3.)
# Target: site-a-node
# Description: KVM Hypervisor 가반의 VM 환경
# =================================================================

export "$(grep -v '^#' .env | xargs)"

HOST_NAME="site-a-node"

echo "🚀 [1/4] Hostname 설정..."
sudo hostnamectl set-hostname $HOST_NAME

echo "📦 [2/4] SSH Server 설정..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y openssh-server
sudo systemctl enable --now ssh

echo "🔑 [3/4] 원격 접속을 위한 Public Key 등록..."
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "$PUBLIC_KEY" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

echo "🛰️ [4/4] Tailscale 메시 네트워크 통합..."
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up \
    --authkey $TAILSCALE_AUTH_KEY \
    --hostname $HOST_NAME \
    --accept-dns=false \
    --accept-routes=false

echo "✅ 모든 과정이 완료되었습니다!"