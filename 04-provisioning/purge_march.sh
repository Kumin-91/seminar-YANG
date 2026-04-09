#!/bin/bash
# mdi-yang-lab: refactor/streamline
# AWS에 프로비저닝된 Base/Node 인프라를 제거하는 스크립트
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

# 1. 노드 매니페스트 파일 찾기 및 프로비저닝 제거
for manifest in "$INVENTORY_DIR/nodes"/*.json; do
    # 1.1 노드 매니페스트 파일이 존재하는지 확인
    if [[ ! -f "$manifest" ]]; then continue; fi

    # 1.2 노드의 플랫폼과 이름 추출
    NODE_DATA=$(jq -r '."hybrid-cloud:cluster".node[0] | [.name, .compute.platform] | @tsv' "$manifest")
    read -r NAME PLATFORM <<< "$NODE_DATA"
    
    # 1.3 플랫폼에 따라 프로비저닝 수행
    case "$PLATFORM" in
        "aws")
            if [[ -f "$PROVISION_DIR/aws-node/$NAME.tfstate" ]]; then
                terraform -chdir="$PROVISION_DIR/aws-node" \
                    destroy -auto-approve \
                    -state="$NAME.tfstate" \
                    -var=manifest_path="$(realpath "$manifest")"
            else
                echo "⚠️ Warning: No Terraform state file found for node $NAME, skipping..."
            fi
        ;;
        "on-premise")
            continue
        ;;
        *)
            continue
        ;;
    esac
done

# 2.1 AWS Base 매니페스트 파일 찾기
AWS_MANIFEST=$(find "$INVENTORY_DIR/providers" -name "*.json" -type f | head -n 1)
if [[ -z "$AWS_MANIFEST" ]]; then
    echo "❌ Error: No provider manifest found in $INVENTORY_DIR/providers"
    exit 1
fi

# 2.2 AWS Base 프로비저닝 제거
if [[ -f "$PROVISION_DIR/aws-base/terraform.tfstate" ]]; then
    terraform -chdir="$PROVISION_DIR/aws-base" \
        destroy -auto-approve \
        -var=manifest_path="$(realpath "$AWS_MANIFEST")" \
        -var=ssh_key_path="$(realpath "$SSH_KEY")"
else
    echo "⚠️ Warning: No Terraform state file found for AWS Base, skipping..."
fi

## 3. 생성된 Terraform 상태 파일 및 기타 캐시 정리
find "$PROVISION_DIR" -name "*.tfstate*" -type f -print -delete