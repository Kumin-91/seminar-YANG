# One Logical Infrastructure, Many Physical Realities: A YANG-Driven Hybrid Cloud with K3s

[Phase 0. Physical Inventory & Resource Specification](#phase-0-physical-inventory)

[Phase 1. Logical Abstraction via YANG Modeling](#phase-1-logical-abstraction-via-yang-modeling)

[Phase 2. Data Integrity & Schema Validation](#phase-2-data-integrity--schema-validation)

[Phase 3. Overlay Networking & Distributed Storage](#phase-3-overlay-networking--distributed-storage)

[Phase 4. Provisioning Automation via Ansible](#phase-4-provisioning-automation-via-ansible)

[Phase 5. Hybrid Cluster Orchestration & Realization](#phase-5-hybrid-cluster-orchestration--realization)

## Project Overview

```plain text
.
├── 01-schema/                   # [Rule] YANG 기반 인프라 추상화 모델
│   ├── common-types.yang        # K3s 역할 및 아키텍처 공통 타입 정의
│   ├── hybrid-cloud.yang        # 클러스터 통합 관리 최상위 모델
│   ├── res-compute.yang         # vCPU/Memory 연산 자원 모델
│   ├── res-network.yang         # Tailscale 기반 네트워크 모델
│   └── res-storage.yang         # JuiceFS 스토리지 연결 모델
│
├── 02-inventory/                # [Manifest] 노드별 자원 할당 명세
│   ├── aws-t4g-node.json        # AWS 노드 선언문
│   ├── site-a-node.json         # Site-A 노드 선언문
│   ├── site-b-node.json         # Site-B 노드 선언문
│   ├── storage-client.env       # JuiceFS 클라이언트 마운트용 비밀번호
│   └── storage-client.example
│
├── 03-bootstrap/                # [Provisioning] 인프라 생존 및 초기화
│   ├── cloud-aws/               # Terraform 기반 AWS 인프라 구축
│   │   ├── aws-t4g-node.tf      # AWS EC2 리소스 정의
│   │   ├── terraform.tfvars     # 클라우드 프로비저닝용 인증 정보
│   │   └── terraform.tfvars.example
│   └── onprem-init/             # 온프레미스 노드 OS 환경 초기화
│       ├── node-bootstrap.env   # Tailscale 및 SSH 초기 키
│       ├── node-bootstrap.env.example
│       ├── site-a-node-init.sh  # Site-A VM 인스턴스 초기화
│       └── site-b-node-init.sh  # Site-B Docker 시스템 컨테이너 구축
│
├── 04-storage-provider/         # [Backend] JuiceFS 데이터 엔진
│   ├── docker-compose.yml       # Redis (Metadata) 및 MinIO (Object) 정의
│   ├── storage-provider.env     # 백엔드 엔진 전용 자격 증명
│   └── storage-provider.env.example
│
├── .gitignore                   # 모든 *.env 및 *.tfvars 유출 방지
└── README.md                    # 프로젝트 아키텍처 및 로드맵 가이드
```

## Phase 0. Physical Inventory & Resource Specification

### Works 1. Strategic Role Allocation & Infrastructure Hierarchy

| Location | Gateway/Ingress | Control Plane | Worker Node |
| --- | --- | --- | --- |
| **AWS** | Primary | Primary | Fallback |
| **Site A** | Secondary| Secondary | Primary |
| **Site B** | ❌ | ❌ | Secondary |

### Works 2. Hardware Inventory & Compute/Storage Quotas

| Location | Network | Compute | Arch | Burstable | Cache Quota |
| --- | --- | --- | --- | --- | --- |
| **AWS** | 100.100.2.101 | 2 vCPU / 4GB RAM (t4g.medium) | arm64 | Yes | 5GB EBS |
| **Site A** | 100.100.2.201 | 4 vCPU / 8GB RAM (Mid-Range CPU) | x86_64 | No | 30GB NVME |
| **Site B** | 100.100.2.202 | 2 vCPU / 4GB RAM (Low-Power CPU) | x86_64 | No | 20GB SSD |

### Works 3. Network Topology & Latency Analysis

* Site A, Site B 서버는 서로 다른 네트워크에 위치해 있지만, 물리적으로 가까운 위치에 있으며 동일한 네트워크 도메인 내에 위치해 있습니다.

    * 같은 Metropolitan Area Network에 위치해 있어, Tailscale 기준 < 5ms의 Latency를 기대할 수 있습니다.

    * 매우 낮은 Latency를 가지고 있어 JuiceFS / K3s 클러스터 구축에 적합합니다.

---

## Phase 1. Logical Abstraction via YANG Modeling

### Works 1. Base Type Definitions: [common-types.yang](./01-schema/common-types.yang)

* K3s 노드 역할과 우선순위를 정의하는 공통 유형 모듈입니다.

### Works 2. Compute Resource Abstraction: [res-compute.yang](./01-schema/res-compute.yang)

* vCPU, Memory, Burstable 여부 등 컴퓨팅 자원 관련 속성을 정의하는 모듈입니다.

* 엄격한 검증을 적용하여 각 노드의 컴퓨팅 자원 사양이 허용된 범위 내에 있도록 합니다.

### Works 3. Network Perimeter & Policy Modeling: [res-network.yang](./01-schema/res-network.yang)

* 엄격하게 Tailscale IP 주소만 허용하도록 구성이 된 네트워크 자원 모델입니다.

* Cloud / On-Prem 자원을 구분할 수 있도록 구성되어 있습니다.

    * AWS: zone "cloud"

    * Site A, Site B: zone "on-prem"

### Works 4. Distributed Storage Logic Modeling: [res-storage.yang](./01-schema/res-storage.yang)

* 컴퓨트 노드가 외부 스토리지 엔진 (MinIO, Redis)에 접근하기 위한 논리적 엔드포인트를 정의합니다.

* 민감한 자격 증명을 직접 모델링하지 않고, secret-file-path 리프를 통해 실질적인 비밀번호가 담긴 `storage-client.env` 파일의 경로만 선언하도록 설계했습니다.

* 캐시 할당량을 GB 단위로 명확히 정의하여, 각 노드의 스토리지 자원 사양이 허용된 범위 내에 있도록 합니다.

### Works 5. Holistic Cluster Integration: [hybrid-cloud.yang](./01-schema/hybrid-cloud.yang)

* 클러스터 전체를 포괄하는 최상위 모델로, 각 노드의 역할과 자원 사양을 통합적으로 표현합니다.

* 각 리소스 모듈을 컴포지션 구조로 통합하여 단일 엔드포인트를 제공합니다.

---

## Phase 2. Data Integrity & Schema Validation

### Works 0. Environment Setup: libyang & yanglint (Rocky Linux 9)

```bash
# libyang 설치
sudo dnf install libyang

# yanglint 설치 확인
yanglint --version
# yanglint 2.0.7
```

### Works 1. Hierarchical Schema Visualization & Structural Audit

```bash
yanglint -f tree ./01-schema/hybrid-cloud.yang
```

```plain text
module: hybrid-cloud
  +--rw cluster
     +--rw node* [name]
        +--rw name               string
        +--rw role-assignment* [role]
        |  +--rw role        ct:k3s-role
        |  +--rw priority    ct:node-role
        +--rw compute
        |  +--rw arch         ct:cpu-arch
        |  +--rw vcpu?        uint8
        |  +--rw memory?      uint8
        |  +--rw burstable?   boolean
        +--rw network
        |  +--rw tailscale-ip    inet:ipv4-address
        |  +--rw zone?           enumeration
        +--rw storage
           +--rw s3-endpoint       string
           +--rw redis-endpoint    string
           +--rw secret-file-path  string
           +--rw cache-size        uint32
```

### Works 2. Data Instance Modeling: Node-specific JSON Manifests

**[Phase 0. Physical Inventory](#phase-0-physical-inventory)** 에서 정의한 리소스 사양에 따라, 각 노드에 대한 JSON 데이터를 작성하였습니다.

* **[aws-t4g-node Example](./02-inventory/aws-t4g-node.json)**

* **[site-a-node Example](./02-inventory/site-a-node.json)**

* **[site-b-node Example](./02-inventory/site-b-node.json)**

### Works 3. Schema Compliance Verification & Data Integrity Audit

```bash
yanglint -p 01-schema -t data 01-schema/hybrid-cloud.yang 02-inventory/aws-t4g-node.json
yanglint -p 01-schema -t data 01-schema/hybrid-cloud.yang 02-inventory/site-a-node.json
yanglint -p 01-schema -t data 01-schema/hybrid-cloud.yang 02-inventory/site-b-node.json
```

### Works 4. Exception Handling & Constraint Enforcement Scenarios

JSON 데이터에 에러가 있는 경우, `yanglint`가 상세한 오류 메시지를 제공하여 문제를 쉽게 파악할 수 있습니다.

* Tailscale IP 주소가 패턴에 맞지 않는 경우

    ```plain text
    libyang err : Unsatisfied pattern - "100.10.1.201" does not conform to "100\.(6[4-9]|[7-9][0-9]|1[0-1][0-9]|12[0-7])\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)". (Schema location /hybrid-cloud:cluster/node/network/tailscale-ip, data location /hybrid-cloud:network, line number 22.)
    YANGLINT[E]: Failed to parse input data file "02-inventory/aws-t4g-node.json".
    ```

* 필드의 값이 허용된 범위를 벗어난 경우

    ```plain text
    libyang err : Unsatisfied range - value "16" is out of the allowed range. (Schema location /hybrid-cloud:cluster/node/compute/vcpu, data location /hybrid-cloud:compute, line number 13.)
    YANGLINT[E]: Failed to parse input data file "02-inventory/site-b-node.json".
    ```

---

## Phase 3. Overlay Networking & Distributed Storage

### Works 0. Shared Public Key Authentication Setup

```bash
# 로컬에서 SSH Key Pair 생성
ssh-keygen -t ed25519 -f ~/.ssh/hybrid-cloud_key -N ""

# 생성된 공개 키 확인
cat ~/.ssh/hybrid-cloud_key.pub
```

### Works 1. EC2 Instance Provisioning: [aws-t4g-node.tf](./03-bootstrap/cloud-aws/aws-t4g-node.tf)

> Terraform으로 프로비저닝 및 초기 설정이 완료된 AWS EC2 인스턴스 환경

```Terraform
# 초기화 자동화 (User Data)
user_data = <<-EOF
            #!/bin/bash
            set -xe
            exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
            hostnamectl set-hostname aws-t4g-node
            dnf update -y
            curl -fsSL https://tailscale.com/install.sh | sh
            tailscale up --authkey ${var.tailscale_auth_key} --hostname aws-t4g-node --accept-dns=false --accept-routes=false
            EOF
```

* Hostname 설정, Tailscale 설치 및 연결을 포함한 초기화 스크립트를 User Data로 자동화하여, 인스턴스가 시작될 때 필요한 설정이 자동으로 적용되도록 했습니다.

### Works 2. On-Prem VM Setup: [site-a-node-init.sh](./03-bootstrap/onprem-init/site-a-node-init.sh)

> KVM Hypervisor 가반의 VM 환경

```bash
# 호스트 이름 변경
sudo hostnamectl set-hostname $HOST_NAME

# OpenSSH Server 설치 및 서비스 시작
sudo apt update && sudo apt upgrade -y
sudo apt install -y openssh-server
sudo systemctl enable --now ssh

# Public Key 등록
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "<PUBLIC_KEY>" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# Tailscale 설치
curl -fsSL https://tailscale.com/install.sh | sh

# Tailscale 연결
sudo tailscale up --authkey $TAILSCALE_AUTH_KEY --hostname $HOST_NAME --accept-dns=false --accept-routes=false
```

### Works 3. On-Prem Container Setup: [site-b-node-init.sh](./03-bootstrap/onprem-init/site-b-node-init.sh)

> Docker 기반 시스템 컨테이너를 활용한 VM 런타임 에뮬레이션

```bash
# Debian 13 Container 생성
docker run -d --name $CONTAINER_NAME --hostname $CONTAINER_NAME \
    --privileged --device /dev/net/tun:/dev/net/tun \
    -v /sys/fs/cgroup:/sys/fs/cgroup:rw --cgroupns host \
    jrei/systemd-debian

# 컨테이너 내부 환경 구축 - 필요 패키지 설치, SSH 접속 설정
docker exec -it $CONTAINER_NAME bash -c "
    apt update && apt upgrade -y && apt install -y openssh-server sudo curl locales && 
    sed -i '/en_US.UTF-8 UTF-8/s/^# //g' /etc/locale.gen && locale-gen &&
    rm -f /etc/nologin && mkdir -p /run/sshd &&
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && 
    systemctl enable --now ssh
"

# Public Key 등록
docker exec -it $CONTAINER_NAME bash -c "
    mkdir -p ~/.ssh && chmod 700 ~/.ssh && 
    echo '<PUBLIC_KEY>' >> ~/.ssh/authorized_keys && 
    chmod 600 ~/.ssh/authorized_keys
"

# Tailscale 설치 및 연결
docker exec -it $CONTAINER_NAME bash -c "
    curl -fsSL https://tailscale.com/install.sh | sh &&
    sudo systemctl enable --now tailscaled &&
    tailscale up --authkey $TAILSCALE_AUTH_KEY --hostname $CONTAINER_NAME --accept-dns=false --accept-routes=false
"
```

### Works 4. IP Configuration & Management Laptop Configuration

#### 1. Tailscale Admin Console에서 IP 주소 할당

* aws-t4g-node: `100.100.2.101`

* site-a-node: `100.100.2.201`

* site-b-node: `100.100.2.202`

#### 2. `~/.ssh/config`

```ini
Host aws-t4g-node
    HostName 100.100.2.101
    User ec2-user
    IdentityFile ~/.ssh/hybrid-cloud_key

Host site-a-node
    HostName 100.100.2.201
    User debian
    IdentityFile ~/.ssh/hybrid-cloud_key

Host site-b-node
    HostName 100.100.2.202
    User root
    IdentityFile ~/.ssh/hybrid-cloud_key
```

### Works 5. Storage Abstraction: JuiceFS Infrastructure Setup

> 컴퓨트 노드와 완전히 격리된 독립형 스토리지 엔진을 구축합니다. S3 호환 API (MinIO)와 고성능 메타데이터 엔진 (Redis)을 추상화된 자원으로 제공하여 하이브리드 클러스터의 데이터 일관성을 보장합니다.

#### 1. Containerized Storage Backend Deployment

* **[docker-compose.yml](./04-storage-provider/docker-compose.yml)** 을 활용하여 스토리지 백엔드를 코드화 했습니다.

* Host OS의 환경에 의존하지 않고, 컨테이너 기술을 통해 엔진의 배포와 버전 관리를 단순화했습니다.

#### 2. Technical Highlights

* MinIO의 데이터 영속성을 위해 ZFS Storage Pool을 직접 매핑하여 데이터 안정성과 성능을 극대화했습니다.

* 기존 서비스 및 시스템 서비스와의 포트 간섭을 원천 차단하기 위해 전용 포트를 할당했습니다.

#### 3. Storage Provider Specs

| Component | Service | Port | Backend Storage |
| --- | --- | --- | --- |
| Metadata Engine | Redis | 4279 | Docker Volume (on NVME) |
| Object Storage | MinIO | 4200 (S3 API) / 4201 (Dashboard) | ZFS Dataset |

---

## Phase 4. Provisioning Automation via Ansible

### Works 1. Data-to-Code: JSON-to-Ansible Manifest Transformation

> **TBD**

### Works 2. Role-based Playbook Logic & Jinja2 Templating

> **TBD**

### Works 3. Idempotent Infrastructure Provisioning

> **TBD**

---

## Phase 5. Hybrid Cluster Orchestration & Realization

> **TBD**