#!/usr/bin/env python3
import sys
import json
from pathlib import Path

# ==========================================
# 1. Configure paths based on project structure
# ==========================================
BASE_DIR = Path(__file__).resolve().parent.parent.parent
INVENTORY_DIR = BASE_DIR / "02-inventory" / "nodes"
TF_STATE_DIR = BASE_DIR / "04-provisioning" / "aws-node"

# ==========================================
# 2. Initialize Ansible inventory structure
# ==========================================

def get_base_inventory():
    """Ansible Dynamic Inventory의 기본 구조를 반환합니다."""
    return {
        "_meta": {"hostvars": {}},
        "all": {
            "children": [
                "control_plane",
                "worker",
                "k8s_init",
                "k8s_join",
                "storage_nodes",
                "unassigned"
            ]
        },
        "control_plane": {"hosts": []},
        "worker": {"hosts": []},
        "k8s_init": {"hosts": []},
        "k8s_join": {"hosts": []},
        "storage_nodes": {"hosts": []},
        "unassigned": {"hosts": []}
    }

# ==========================================
# 3. Helper function to format URLs
# ==========================================

def format_url(endpoint, default_scheme = "https"):
    """URL 헬퍼 함수: URL에 프로토콜이 포함되어 있지 않은 경우 기본 스킴을 추가합니다."""
    if not endpoint: return ""
    return endpoint if "://" in endpoint else f"{default_scheme}://{endpoint}"

# ==========================================
# 4. Extract AWS instance IPs from Terraform state files
# ==========================================

def extract_tf_ips(tf_state_dir):
    """Terraform 상태 파일에서 AWS 인스턴스의 IP 주소를 추출하여 매핑합니다."""
    ip_map = {}
    for state_file in tf_state_dir.glob("*.tfstate"):
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            # aws_instance 리소스에서 IP 주소 추출
            instances = [
                inst for res in state.get('resources', []) 
                if res['type'] == 'aws_instance' 
                for inst in res.get('instances', [])
            ]

            # IP 주소 매핑 생성
            for inst in instances:
                name = inst.get('attributes', {}).get('tags', {}).get('Name')
                ip = inst.get('attributes', {}).get('public_ip')
                if name and ip:
                    ip_map[name] = ip

        except Exception as e:
            print(f"⚠️ Warning: Unable to parse {state_file}: {e}", file=sys.stderr)
            continue
            
    return ip_map

# ==========================================
# 5. Core Main function to build inventory
# ==========================================

def build_inventory():
    """Ansible 인벤토리를 구축하는 메인 함수입니다."""
    inventory = get_base_inventory()
    tf_ips = extract_tf_ips(TF_STATE_DIR)

    # JSON 매니페스트 검색
    manifests = list(INVENTORY_DIR.glob("*.json"))
    if not manifests:
        print(f"⚠️ Warning: No JSON files found in {INVENTORY_DIR}", file=sys.stderr)
        return inventory
    
    for manifest_file in manifests:
        try:
            with open(manifest_file) as f:
                data = json.load(f)
            
            # YANG 계층 구조에 맞게 노드 정보 추출
            node_data = data.get('hybrid-cloud:cluster', {}).get('node', [{}])[0]

            # 노드 데이터가 없는 경우 경고 메시지 출력
            if not node_data:
                print(f"⚠️ Warning: No node data found in {manifest_file}", file=sys.stderr)
                continue

            # 노드 정보 추출
            name = node_data['name']
            compute = node_data.get('compute', {})
            network = node_data.get('network', {})
            storage = node_data.get('storage', {})
            k8s_role = node_data.get('k8s-role-assignment', {})
            platform = compute.get('platform')
            arch = compute.get('arch', 'unknown')

            # K8s 동적 노드 레이블 설정
            k8s_node_labels = [
                f"topology.kubernetes.io/region={platform}",
                f"kubernetes.io/arch={arch}",
            ]

            # IP 주소 매핑
            if platform == 'aws':
                ansible_host = tf_ips.get(name)
            else:
                ansible_host = network.get('on-premise-strategy', {}).get('bootstrap-ip') or network.get('bootstrap-ip')

            # IP 주소가 없는 경우 경고 메시지 출력
            if not ansible_host:
                print(f"⚠️ Warning: No IP found for '{name}'", file=sys.stderr)

            # HostVars 설정
            inventory['_meta']['hostvars'][name] = {
                "node_spec": compute,
                "ansible_host": ansible_host,
                "ansible_port": network.get('ssh-port', 22),
                "ansible_user": network.get('ssh-user', 'sttb'),
                "storage_info": {
                    "s3_url": format_url(storage.get('s3-endpoint')),
                    "redis_url": storage.get('redis-endpoint'),
                    "cache_size": storage.get('cache-size', 5),
                    "mount_point": storage.get('mount-point', '/jfs')
                } if storage else None,
                "k8s_node_labels": k8s_node_labels
            }

            # Group 할당
            if platform:
                # on-premise -> on_premise으로 그룹 이름 변경
                platform_group = platform.replace('-', '_')
                # 인벤토리에 플랫폼 그룹이 없는 경우 생성
                if platform_group not in inventory:
                    inventory[platform_group] = {"hosts": []}
                    if platform_group not in inventory['all']['children']:
                        inventory['all']['children'].append(platform_group)
                # 플랫폼 그룹에 호스트 추가
                inventory[platform_group]['hosts'].append(name)

            # Storage 노드 그룹 할당
            if storage:
                inventory['storage_nodes']['hosts'].append(name)

            # Kubernetes 역할에 따른 그룹 할당
            if k8s_role:
                role, strategy = k8s_role.get('node-role'), k8s_role.get('bootstrap-role')
                # control-plane -> control_plane으로 그룹 이름 변경
                role_group = role.replace('-', '_')
                if role: inventory[role_group]['hosts'].append(name)
                if strategy: inventory[f"k8s_{strategy}"]['hosts'].append(name)
            else:
                inventory['unassigned']['hosts'].append(name)

        except Exception as e:
            print(f"⚠️ Warning: Failed to parse {manifest_file}: {e}", file=sys.stderr)
            continue

    return inventory

# ==========================================
# 6. Main execution block
# ==========================================
if __name__ == "__main__":
    inventory = build_inventory()
    print(json.dumps(inventory, indent=2), file=sys.stdout)