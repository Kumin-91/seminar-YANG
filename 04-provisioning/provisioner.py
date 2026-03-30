#!/usr/bin/env python3

import sys
import json
import subprocess
from pathlib import Path

class Provisioner:
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent
        self.inventory_node_dir = self.base_dir / "02-inventory" / "nodes"
        self.inventory_provider_dir = self.base_dir / "02-inventory" / "providers"
        self.terraform_base_dir = self.base_dir / "04-provisioning" / "aws-base"
        self.terraform_node_dir = self.base_dir / "04-provisioning" / "aws-node"
        self.on_premise_script = self.base_dir / "04-provisioning" / "on-premise" / "public_key.sh"
        self.ssh_key_path = self.base_dir / "00-key" / "hybrid-cloud.pub"
        self.aws_base_provisioned = False

    def get_node_name(self, manifest_path):
        """ 매니페스트 파일에서 노드 이름을 추출합니다. YANG 계층 구조에 맞게 조정되어 있습니다. """
        with open(manifest_path) as f:
            data = json.load(f)
        return data['hybrid-cloud:cluster']['node'][0]['name']

    def run_command(self, command):
        """명령어를 실행하고 에러 발생 시 상세 메시지와 함께 즉시 중단합니다."""
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            print(f"\n❌ 명령어 실행 실패: {command}", file=sys.stderr)
            exit(1)

    def provision_aws_base(self):
        """AWS 베이스 인프라를 Terraform으로 프로비저닝합니다."""
        # 절대 경로로 변환
        manifest = list(self.inventory_provider_dir.glob("*.json"))
        if not manifest:
            print(f"❌ 에러: {self.inventory_provider_dir} 디렉토리에 JSON 파일이 없습니다. AWS 베이스 인프라 프로비저닝을 건너뜁니다.", file=sys.stderr)
            return
        abs_manifest = Path(manifest[0]).resolve()

        # 프로비저닝
        print(f"🛠️ AWS 베이스 인프라 프로비저닝 시작", file=sys.stderr)
        cmd = [
            "terraform",
            f"-chdir={str(self.terraform_base_dir)}",
            "apply",
            "-auto-approve",
            f"-var=manifest_path={str(abs_manifest)}",
        ]
        self.run_command(cmd)

    def provision_aws_node(self, manifest_path):
        """Terraform을 호출하여 AWS 인프라를 생성합니다."""
        # 절대 경로로 변환하여 명확한 출력 제공
        abs_manifest = Path(manifest_path).resolve()

        # 노드 이름을 기반으로 상태 파일명 추출
        node_name = self.get_node_name(manifest_path)
        state_file = f"{node_name}.tfstate"

        # 프로비저닝
        print(f"🛰️ AWS 프로비저닝 시작: {node_name} (State: {state_file})", file=sys.stderr)
        cmd = [
            "terraform",
            f"-chdir={str(self.terraform_node_dir)}",
            "apply",
            "-auto-approve",
            f"-state={state_file}",
            f"-var=manifest_path={str(abs_manifest)}",
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
        manifests = list(self.inventory_node_dir.glob("*.json"))

        if not manifests:
            print(f"⚠️ {self.inventory_node_dir} 디렉토리에 JSON 파일이 없습니다.", file=sys.stderr)
            return
        
        print(f"✅ 총 {len(manifests)}개의 노드 설계를 발견했습니다. 작업을 시작합니다.", file=sys.stderr)

        for manifest_file in manifests:
            try:
                with open(manifest_file) as f:
                    inventory = json.load(f)
                
                # YANG 계층 구조에 맞게 노드 정보 추출
                name = self.get_node_name(manifest_file)
                node = inventory['hybrid-cloud:cluster']['node'][0]
                platform = node['compute']['platform']

                print(f"\n--- [프로비저닝 대상: {name} | 플랫폼: {platform}] ---", file=sys.stderr)

                # AWS 베이스 인프라 프로비저닝 (한 번만 실행)
                if platform == 'aws' and not self.aws_base_provisioned:
                    self.provision_aws_base()
                    self.aws_base_provisioned = True

                # Platform에 따라 프로비저닝 실행
                if platform == 'aws':
                    self.provision_aws_node(manifest_file)
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