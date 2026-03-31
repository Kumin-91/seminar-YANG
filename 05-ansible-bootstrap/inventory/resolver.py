#!/usr/bin/env python3

import sys
import json
from pathlib import Path

class InventoryResolver:
    def __init__(self):
        # 프로젝트 구조에 맞게 절대 경로 설정
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.inventory_dir = self.base_dir / "02-inventory" / "nodes"
        self.tf_state_dir = self.base_dir / "04-provisioning" / "aws-node"
        
        # Ansible 인벤토리 초기 구조
        self.inventory = {
            "_meta": {"hostvars": {}},
            "all": {"children": ["aws", "on_premise", "server", "agent"]},
            "aws": {"hosts": []},
            "on_premise": {"hosts": []},
            "server": {"hosts": []},
            "agent": {"hosts": []}
        }

    def format_url(self, endpoint, default_scheme):
        """ URL에 프로토콜이 포함되어 있지 않은 경우 기본 스킴을 추가하는 헬퍼 함수 """
        if not endpoint:
            return ""

        # URL에 프로토콜이 포함되어 있는 경우
        if "://" in endpoint:
            return endpoint
        
        # URL에 프로토콜이 포함되어 있지 않은 경우, 기본 스킴을 추가
        return f"{default_scheme}://{endpoint}"

    def load_tf_ips(self):
        """ Terraform 상태 파일에서 AWS 인스턴스의 IP 주소를 추출하여 매핑 """

        states = list(self.tf_state_dir.glob("*.tfstate"))

        if not states:
            return {}
        
        ip_map = {}
        for state_file in states:
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)

                # Terraform 상태 파일에서 AWS 인스턴스의 IP 주소를 추출하여 매핑
                print(f"🔍 Terraform 상태 파일에서 AWS 인스턴스 IP 주소 추출 중: {state_file.name}", file=sys.stderr)
                for res in state.get('resources', []):
                    if res['type'] == 'aws_instance':
                        for inst in res.get('instances', []):
                            name = inst['attributes']['tags'].get('Name')
                            ip = inst['attributes'].get('public_ip')
                            if name and ip:
                                ip_map[name] = ip
            except Exception as e:
                print(f"❌ Terraform 상태 파일 처리 중 오류 발생 ({state_file.name}): {e}", file=sys.stderr)
                continue

        return ip_map

    def resolve_inventory(self):
        """ 인벤토리 디렉토리에서 JSON 파일을 읽어 Ansible 인벤토리 구조로 변환 """
        tf_ips = self.load_tf_ips()
        manifests = list(self.inventory_dir.glob("*.json"))

        if not manifests:
            print(f"⚠️ {self.inventory_dir} 디렉토리에 JSON 파일이 없습니다.", file=sys.stderr)
            return self.inventory
        
        print(f"✅ 총 {len(manifests)}개의 노드 설계를 발견했습니다. 작업을 시작합니다.", file=sys.stderr)

        for manifest_file in manifests:
            try:
                with open(manifest_file) as f:
                    inventory = json.load(f)
                
                # YANG 계층 구조에 맞게 노드 정보 추출
                node = inventory['hybrid-cloud:cluster']['node'][0]
                name = node['name']
                role_assignment = node.get('role-assignment', [])
                platform = node['compute']['platform']
                network = node['network']
                storage = node.get('storage', {})
                secret_path = None

                print(f"\n--- [작업 대상: {name} | 플랫폼: {platform}] ---", file=sys.stderr)

                # Platform에 따라 Ansible 호스트 변수 설정
                if platform == 'aws':
                    ansible_host = tf_ips.get(name)
                    if not ansible_host:
                        print(f"⚠️ 경고: '{name}'의 IP를 테라폼 상태에서 찾을 수 없습니다. (프로비저닝 확인 필요)", file=sys.stderr)
                    self.inventory['aws']['hosts'].append(name)
                elif platform == 'on-premise':
                    ansible_host = network.get('on-premise-strategy', {}).get('bootstrap-ip') or network.get('bootstrap-ip')
                    if not ansible_host:
                        print(f"⚠️ 경고: '{name}'의 부트스트랩 IP를 매니페스트에서 찾을 수 없습니다. (네트워크 설정 확인 필요)", file=sys.stderr)
                    self.inventory['on_premise']['hosts'].append(name)

                # Roll_assignment에 따라 서버/에이전트 그룹에 호스트 추가
                for role in role_assignment:
                    role_name = role['role']
                    if role_name in self.inventory:
                        self.inventory[role_name]['hosts'].append(name)

                # Ansible 호스트 변수 설정
                self.inventory['_meta']['hostvars'][name] = {
                    "ansible_host": ansible_host,
                    "ansible_port": network.get('ssh-port', 22),
                    "ansible_user": network.get('ssh-user', 'sttb'),
                    "node_spec": node,
                    "has_storage": bool(storage),
                    "storage_info": {
                        "s3_url": self.format_url(storage.get('s3-endpoint'), 'https'),
                        "redis_url": storage.get('redis-endpoint'),
                        "cache_size": storage.get('cache-size', '1'),
                        "mount_point": storage.get('mount-point', '/jfs')
                    } if storage else None
                }
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                print(f"❌ 매니페스트 파일 처리 중 오류 발생 ({manifest_file.name}): {e}", file=sys.stderr)
                continue

        return self.inventory

if __name__ == "__main__":
    print("🚀 하이브리드 클라우드 인프라 인벤토리 리졸버 가동", file=sys.stderr)
    resolver = InventoryResolver()
    inventory = resolver.resolve_inventory()
    print(json.dumps(inventory, indent=2), file=sys.stdout)