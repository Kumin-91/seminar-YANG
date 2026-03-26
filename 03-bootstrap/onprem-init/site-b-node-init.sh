#!/bin/bash

# =================================================================
# Project: Hybrid-Cloud (Phase 3.)
# Target: site-b-node
# Description: Docker 기반 시스템 컨테이너를 활용한 VM 런타임 에뮬레이션
# =================================================================

CONTAINER_NAME="site-b-node"
KEY_PATH="node-bootstrap.env"
if [ -f $KEY_PATH ]; then
    set -a && source $KEY_PATH && set +a
else
    echo "Error: .env file not found!"
    exit 1
fi

echo "🚀 [1/4] 기존 컨테이너 정리 및 새 컨테이너 생성..."
docker rm -f $CONTAINER_NAME 2>/dev/null
docker run -d \
    --name $CONTAINER_NAME \
    --hostname $CONTAINER_NAME \
    --privileged \
    --device /dev/net/tun:/dev/net/tun \
    --cgroupns host \
    -v /sys/fs/cgroup:/sys/fs/cgroup:rw \
    jrei/systemd-debian

echo "📦 [2/4] 시스템 환경 구축 (SSH, Locales, PAM 이슈 해결)..."
docker exec -it $CONTAINER_NAME bash -c "
    apt update && 
    apt upgrade -y &&
    apt install -y openssh-server sudo curl locales && 
    sed -i '/en_US.UTF-8 UTF-8/s/^# //g' /etc/locale.gen && 
    locale-gen &&
    rm -f /etc/nologin && 
    mkdir -p /run/sshd &&
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && 
    systemctl enable --now ssh
"

echo "🔑 [3/4] 원격 접속을 위한 Public Key 등록..."
docker exec -it $CONTAINER_NAME bash -c "
    mkdir -p ~/.ssh &&
    chmod 700 ~/.ssh && 
    echo '$PUBLIC_KEY' >> ~/.ssh/authorized_keys && 
    chmod 600 ~/.ssh/authorized_keys
"

echo "🛰️ [4/4] Tailscale 메시 네트워크 통합..."
docker exec -it $CONTAINER_NAME bash -c "
    curl -fsSL https://tailscale.com/install.sh | sh &&
    sudo systemctl enable --now tailscaled &&
    tailscale up \
        --authkey $TAILSCALE_AUTH_KEY \
        --hostname $CONTAINER_NAME \
        --accept-dns=false \
        --accept-routes=false
"

echo "✅ 모든 과정이 완료되었습니다!"