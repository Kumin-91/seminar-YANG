#!/bin/bash
# mdi-yang-lab: refactor/streamline
# YANG Model을 통과한 SSoT JSON 파일을 기반으로 AWS와 On-premises 인프라를 프로비저닝하는 스크립트
set -e

# 0.1 프로젝트 디렉토리 경로 설정
BASE_DIR=$(realpath "$(dirname "$0")/..")
INVENTORY_DIR="$BASE_DIR/02-inventory"
PROVISION_DIR="$BASE_DIR/04-provisioning"

# 0.2 SSH 키 파일 찾기
SSH_KEY=$(find "$BASE_DIR/00-key" -name "*.pub" -type f | head -n 1)
if [[ -z "$SSH_KEY" ]]; then
    echo "❌ Error: No SSH public key found in $BASE_DIR/00-key"
    exit 1
fi

# 1.1 AWS Base 매니페스트 파일 찾기
AWS_MANIFEST=$(find "$INVENTORY_DIR/providers" -name "*.json" -type f | head -n 1)
if [[ -z "$AWS_MANIFEST" ]]; then
    echo "❌ Error: No provider manifest found in $INVENTORY_DIR/providers"
    exit 1
fi

# 1.2 AWS Base 프로비저닝
terraform -chdir="$PROVISION_DIR/aws-base" \
    apply -auto-approve \
    -var=manifest_path="$(realpath "$AWS_MANIFEST")" \
    -var=ssh_key_path="$(realpath "$SSH_KEY")"

# 2. 노드 매니페스트 파일 찾기 및 프로비저닝
for manifest in "$INVENTORY_DIR/nodes"/*.json; do
    # 2.1 노드 매니페스트 파일이 존재하는지 확인
    if [[ ! -f "$manifest" ]]; then continue; fi

    # 2.2 노드의 플랫폼과 이름 추출
    NODE_DATA=$(jq -r '."hybrid-cloud:cluster".node[0] | [.name, .compute.platform] | @tsv' "$manifest")
    read -r NAME PLATFORM <<< "$NODE_DATA"
    
    # 2.3 플랫폼에 따라 프로비저닝 수행
    case "$PLATFORM" in
        "aws")
            terraform -chdir="$PROVISION_DIR/aws-node" \
                apply -auto-approve \
                -state="$NAME.tfstate" \
                -var=manifest_path="$(realpath "$manifest")"
        ;;
        "on-premise")
            # SSH 접속 정보 추출
            SSH_INFO=$(jq -r '."hybrid-cloud:cluster".node[0].network | 
                [(."on-premise-strategy"."bootstrap-ip" // ."bootstrap-ip"), 
                 (."ssh-port" // 22), 
                 (."ssh-user" // "sttb")] | @tsv' "$manifest")
            read -r IP PORT USER <<< "$SSH_INFO"
        
            # SSH 키를 대상 호스트에 복사하여 Ansible이 SSH로 접속할 수 있도록 설정
            ssh-copy-id -o StrictHostKeyChecking=no -i "$SSH_KEY" -p "$PORT" "$USER@$IP"
        ;;
        *)
            echo "⚠️ Warning: Unsupported platform: $PLATFORM for node $NAME, skipping..."
        ;;
    esac
done