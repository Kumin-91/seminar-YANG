#!/usr/bin/env python3

import sys
import json
import subprocess
from pathlib import Path

class Provisioner:
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent
        self.inventory_dir = self.base_dir / "02-inventory"
        self.terraform_dir = self.base_dir / "04-provisioning" / "aws"
        self.on_premise_script = self.base_dir / "04-provisioning" / "on-premise" / "public_key.sh"
        self.ssh_key_path = Path.home() / ".ssh" / "hybrid-cloud_key.pub"

        if not self.ssh_key_path.exists():
            print(f"❌ 에러: SSH 공개키를 찾을 수 없습니다: {self.ssh_key_path}", file=sys.stderr)
            exit(1)

    def run_command(self, command):
        """명령어를 실행하고 에러 발생 시 상세 메시지와 함께 즉시 중단합니다."""
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            print(f"\n❌ 명령어 실행 실패: {command}", file=sys.stderr)
            exit(1)

    def provision_aws(self, manifest_path):
        """Terraform을 호출하여 AWS 인프라를 생성합니다."""
        # 절대 경로로 변환하여 명확한 출력 제공
        abs_manifest = Path(manifest_path).resolve()
        abs_key = self.ssh_key_path.resolve()

        # 노드 이름을 기반으로 상태 파일명 추출
        node_name = abs_manifest.stem
        state_file = f"{node_name}.tfstate"

        # 프로비저닝
        print(f"🛰️ AWS 프로비저닝 시작: {abs_manifest.name} (State: {state_file})", file=sys.stderr)
        cmd = [
            "terraform",
            f"-chdir={str(self.terraform_dir)}",
            "apply",
            "-auto-approve",
            f"-state={state_file}",
            f"-var=manifest_path={str(abs_manifest)}",
            f"-var=public_key_path={str(abs_key)}"
        ]
        self.run_command(cmd)

    def provision_on_premise(self, ssh_host, ssh_port, ssh_user):
        """온프레미스 노드에 SSH 마스터 키를 주입합니다."""
        ssh_key = self.ssh_key_path.resolve()

        print(f"🔑 SSH 키 주입 중: {ssh_user}@{ssh_host}:{ssh_port}", file=sys.stderr)
        cmd = [
            "bash",
            str(self.on_premise_script),
            str(ssh_host),
            str(ssh_port),
            str(ssh_user),
            str(ssh_key)
        ]
        self.run_command(cmd)

    def orchestrate(self):
        """인벤토리의 모든 노드를 순회하며 프로비저닝을 오케스트레이션합니다."""
        manifests = list(self.inventory_dir.glob("*.json"))

        if not manifests:
            print(f"⚠️ {self.inventory_dir} 디렉토리에 JSON 파일이 없습니다.", file=sys.stderr)
            return
        
        print(f"✅ 총 {len(manifests)}개의 노드 설계를 발견했습니다. 작업을 시작합니다.", file=sys.stderr)

        for manifest_file in manifests:
            try:
                with open(manifest_file) as f:
                    inventory = json.load(f)
                
                # YANG 계층 구조에 맞게 노드 정보 추출
                node = inventory['hybrid-cloud:cluster']['node'][0]
                name = node['name']
                platform = node['compute']['platform']

                print(f"\n--- [프로비저닝 대상: {name} | 플랫폼: {platform}] ---", file=sys.stderr)

                # Platform에 따라 프로비저닝 실행
                if platform == 'aws':
                    self.provision_aws(manifest_file)
                elif platform == 'on-premise':
                    network = node.get('network', {})
                    ssh_host = network.get('on-premise-strategy', {}).get('bootstrap-ip') or network.get('bootstrap-ip')
                    ssh_port = network.get('ssh-port', 22)
                    ssh_user = network.get('ssh-user', 'sttb')

                    if ssh_host:
                        self.provision_on_premise(ssh_host, ssh_port, ssh_user)
                    else:
                        print(f"❌ 에러: 노드 '{name}'의 접속 IP를 찾을 수 없습니다. 건너뜁니다.", file=sys.stderr)

            except (KeyError, IndexError, json.JSONDecodeError) as e:
                print(f"❌ 매니페스트 파일 처리 중 오류 발생 ({manifest_file.name}): {e}", file=sys.stderr)
                continue

if __name__ == "__main__":
    print("🚀 하이브리드 클라우드 인프라 프로비저닝 프로세스 가동", file=sys.stderr)
    provisioner = Provisioner()
    provisioner.orchestrate()