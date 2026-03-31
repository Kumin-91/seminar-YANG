#!/usr/bin/env python3

import sys
import json
import subprocess
from pathlib import Path

class ProvisionerTFRemove:
    def __init__(self):
        # 프로젝트 구조에 맞게 절대 경로 설정
        self.base_dir = Path(__file__).resolve().parent.parent
        self.inventory_node_dir = self.base_dir / "02-inventory" / "nodes"
        self.inventory_provider_dir = self.base_dir / "02-inventory" / "providers"
        self.terraform_base_dir = self.base_dir / "04-provisioning" / "aws-base"
        self.terraform_node_dir = self.base_dir / "04-provisioning" / "aws-node"
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
            print(f"❌ 명령어 실행 실패: {command}", file=sys.stderr)
            exit(1)

    def remove_aws_base(self):
        """AWS 베이스 인프라를 Terraform으로 제거합니다."""
        # 절대 경로로 변환
        manifest = list(self.inventory_provider_dir.glob("*.json"))
        if not manifest:
            print(f"❌ 에러: {self.inventory_provider_dir} 디렉토리에 JSON 파일이 없습니다. AWS 베이스 인프라 제거를 건너뜁니다.", file=sys.stderr)
            return
        abs_manifest = Path(manifest[0]).resolve()

        print("🗑️ AWS 베이스 인프라 제거 시작", file=sys.stdout)
        cmd = [
            "terraform",
            f"-chdir={str(self.terraform_base_dir)}",
            "destroy",
            "-auto-approve",
            f"-var=manifest_path={str(abs_manifest)}",
        ]
        self.run_command(cmd)

    def remove_aws_node(self, manifest_path):
        """Terraform을 호출하여 AWS 인프라를 제거합니다."""
        # 절대 경로로 변환하여 명확한 출력 제공
        abs_manifest = Path(manifest_path).resolve()

        # 노드 이름을 기반으로 상태 파일명 추출
        node_name = self.get_node_name(manifest_path)
        state_file = f"{node_name}.tfstate"

        # 상태 파일이 존재하는지 확인
        if not Path(self.terraform_node_dir / state_file).exists():
            print(f"⏩ 스킵: {state_file}이 존재하지 않아 이미 제거된 것으로 간주합니다.", file=sys.stdout)
            return

        print(f"🗑️ AWS 인프라 제거 시작: {node_name} (State: {state_file})", file=sys.stdout)
        cmd = [
            "terraform",
            f"-chdir={str(self.terraform_node_dir)}",
            "destroy",
            "-auto-approve",
            f"-state={state_file}",
            f"-var=manifest_path={str(abs_manifest)}",
        ]
        self.run_command(cmd)

    def orchestrate(self):
        """인벤토리 파일을 읽고 AWS 인프라 제거를 오케스트레이션합니다."""
        manifests = list(self.inventory_node_dir.glob("*.json"))

        if not manifests:
            print(f"⚠️ {self.inventory_node_dir} 디렉토리에 JSON 파일이 없습니다.", file=sys.stderr)
            return

        print(f"✅ 총 {len(manifests)}개의 노드 설계를 발견했습니다. 작업을 시작합니다.", file=sys.stdout)

        for manifest_file in manifests:
            try:
                with open(manifest_file) as f:
                    inventory = json.load(f)

                platform = inventory['hybrid-cloud:cluster']['node'][0]['compute']['platform']

                # Platform에 따라 프로비저닝 실행   
                if platform == 'aws':
                    self.remove_aws_node(manifest_file)
                    self.aws_base_provisioned = True

            except Exception as e:
                print(f"❌ {manifest_file.name} 처리 중 에러: {e}", file=sys.stderr)
                continue

        if self.aws_base_provisioned:
            self.remove_aws_base()
            self.aws_base_provisioned = False

if __name__ == "__main__":
    remover = ProvisionerTFRemove()
    remover.orchestrate()