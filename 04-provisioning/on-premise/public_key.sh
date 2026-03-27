#!/bin/bash
# 이 스크립트는 Ansible 실행 전 딱 한 번만 실행
set -e

SSH_HOST=$1
SSH_PORT=$2
SSH_USER=$3
PUB_KEY_PATH=${4:-"~/.ssh/hybrid-cloud_key.pub"}

if [ -z "$SSH_HOST" ]; then
    echo "Usage: $0 <ssh_host> [ssh_port] [ssh_user] [pub_key_path]"
    exit 1
fi

echo "🔓 Injecting SSH Public Key to $SSH_HOST..."
# SSH 키를 대상 호스트에 복사하여 Ansible이 SSH로 접속할 수 있도록 설정
ssh-copy-id -o StrictHostKeyChecking=no \
    -i $PUB_KEY_PATH -p $SSH_PORT $SSH_USER@$SSH_HOST

echo "✅ Ready for Ansible!"