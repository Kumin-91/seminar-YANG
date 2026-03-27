import json
import subprocess
import glob
import os

# 파이썬 절대 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 설정 파일 경로
INVENTORY_DIR = os.path.join(BASE_DIR, '../02-inventory')
TERRAFORM_DIR = os.path.join(BASE_DIR, 'aws')
ONPREMISE_SCRIPT = os.path.join(BASE_DIR, 'on-premise/public_key.sh')
SSH_KEY_PATH = os.path.expanduser('~/.ssh/hybrid-cloud_key.pub')

def run_command(command):
    try:
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.stdout:
            print(result.stdout.decode())
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e.stderr.decode()}")
        exit(1)

def provision_aws(abs_manifest_path):
    cmd = (f"terraform -chdir={TERRAFORM_DIR} apply -auto-approve "
           f"-var=manifest_path={abs_manifest_path} "
           f"-var=public_key_path={SSH_KEY_PATH}")
    run_command(cmd)

def provision_on_premise(ssh_host, ssh_port, ssh_user):
    run_command(f"bash {ONPREMISE_SCRIPT} {ssh_host} {ssh_port} {ssh_user} {SSH_KEY_PATH}")

def orchestrate():
    manifests= glob.glob(os.path.join(INVENTORY_DIR, '*.json'))

    if not manifests:
        print("No inventory files found in the directory.")
        return
    
    print(f"Found {len(manifests)} inventory files. Starting provisioning...")

    for manifest_file in manifests:
        abs_manifest_path = os.path.abspath(manifest_file)
        with open(abs_manifest_path) as f:
            inventory = json.load(f)
        
        node = inventory['hybrid-cloud:cluster']['node'][0]
        platform = node['compute']['platform']
        name = node['name']

        print(f"\n--- Node '{name}' on Platform '{platform}'...")

        if platform == 'aws':
            provision_aws(abs_manifest_path)

        elif platform == 'on-premise':
            network = node.get('network', {})

            ssh_host = network.get('on-premise-strategy', {}).get('bootstrap-ip') or network.get('bootstrap-ip')
            ssh_port = network.get('ssh-port', 22)
            ssh_user = network.get('ssh-user', 'root')

            if ssh_host:
                provision_on_premise(ssh_host, ssh_port, ssh_user)
            else:
                print(f"Error: No bootstrap IP found for on-premise node '{name}'. Skipping...")

if __name__ == "__main__":
    orchestrate()