#!/usr/bin/env python3

import sys
import json
import subprocess
from pathlib import Path

class ProvisionerTFRemove:
    def __init__(self):
        # 프로젝트 구조에 맞게 절대 경로 설정
        self.base_dir = Path(__file__).resolve().parent.parent
        self.inventory_dir = self.base_dir / "02-inventory"
        self.terraform_dir = self.base_dir / "04-provisioning" / "aws"
        self.ssh_key_path = Path.home() / ".ssh" / "hybrid-cloud_key.pub"

    def run_command(self, command):
        """명령어를 실행하고 에러 발생 시 상세 메시지와 함께 즉시 중단합니다."""
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            print(f"\n❌ 명령어 실행 실패: {command}", file=sys.stderr)
            exit(1)

    def remove_aws(self, manifest_path):
        """Terraform을 호출하여 AWS 인프라를 제거합니다."""
        # 절대 경로로 변환하여 명확한 출력 제공
        abs_manifest = Path(manifest_path).resolve()
        abs_key = self.ssh_key_path.resolve()

        # 노드 이름을 기반으로 상태 파일명 추출
        node_name = abs_manifest.stem
        state_file = f"{node_name}.tfstate"

        # 상태 파일이 존재하는지 확인
        if not Path(self.terraform_dir / state_file).exists():
            print(f"⏩ 스킵: {state_file}이 존재하지 않아 이미 제거된 것으로 간주합니다.", file=sys.stderr)
            return

        print(f"🗑️ AWS 인프라 제거 시작: {abs_manifest.name} (State: {state_file})", file=sys.stderr)
        cmd = [
            "terraform",
            f"-chdir={str(self.terraform_dir)}",
            "destroy",
            "-auto-approve",
            f"-state={state_file}",
            f"-var=manifest_path={str(abs_manifest)}",
            f"-var=public_key_path={str(abs_key)}"
        ]
        self.run_command(cmd)

    def orchestrate(self):
        """인벤토리 파일을 읽고 AWS 인프라 제거를 오케스트레이션합니다."""
        manifests = list(self.inventory_dir.glob("*.json"))

        if not manifests:
            print(f"⚠️ {self.inventory_dir} 디렉토리에 JSON 파일이 없습니다.", file=sys.stderr)
            return

        print(f"✅ 총 {len(manifests)}개의 노드 설계를 발견했습니다. 작업을 시작합니다.", file=sys.stderr)

        for manifest_file in manifests:
            try:
                with open(manifest_file) as f:
                    inventory = json.load(f)

                platform = inventory['hybrid-cloud:cluster']['node'][0]['compute']['platform']

                # Platform에 따라 프로비저닝 실행   
                if platform == 'aws':
                    self.remove_aws(manifest_file)

            except Exception as e:
                print(f"❌ {manifest_file.name} 처리 중 에러: {e}", file=sys.stderr)
                continue

if __name__ == "__main__":
    print("❌ AWS 인프라 제거 스크립트입니다. 이 스크립트는 Terraform을 사용하여 AWS 인프라를 제거합니다.", file=sys.stderr)
    remover = ProvisionerTFRemove()
    remover.orchestrate()