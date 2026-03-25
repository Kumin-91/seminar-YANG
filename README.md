# One Logical Infrastructure, Many Physical Realities: A YANG-Driven Hybrid Cloud with K3s

[Phase 0. Physical Inventory & Resource Specification](#phase-0-physical-inventory)

[Phase 1. Logical Abstraction via YANG Modeling](#phase-1-logical-abstraction-via-yang-modeling)

[Phase 2. Data Integrity & Schema Validation](#phase-2-data-integrity--schema-validation)

[Phase 3. Overlay Networking & Distributed Storage](#phase-3-overlay-networking--distributed-storage)

[Phase 4. Provisioning Automation via Ansible](#phase-4-provisioning-automation-via-ansible)

[Phase 5. Hybrid Cluster Orchestration & Realization](#phase-5-hybrid-cluster-orchestration--realization)

## Working in Progress

> [Phase 3. Overlay Networking & Distributed Storage](#phase-3-overlay-networking--distributed-storage)
>> [Works 3. Storage Abstraction: JuiceFS Infrastructure Setup](#works-3-storage-abstraction-juicefs-infrastructure-setup)  

## Phase 0. Physical Inventory & Resource Specification

### Works 1. Strategic Role Allocation & Infrastructure Hierarchy

| Location | Access Point | Control Plane | Worker Node |
| --- | --- | --- | --- |
| **AWS** | Primary | Primary | Fallback |
| **Site A** | Secondary| Secondary | Primary |
| **Site B** | ❌ | ❌ | Secondary |

### Works 2. Hardware Inventory & Compute/Storage Quotas

| Location | Network | Compute | Arch | Burstable | Cache Quota |
| --- | --- | --- | --- | --- | --- 
| AWS | 100.100.2.101 | 2 vCPU / 4GB RAM (t4g.medium) | arm64 | Yes | 5GB EBS |
| Site A | 100.100.2.201 | 4 vCPU / 8GB RAM (Mid-Range CPU) | x86_64 | No | 30GB NVME |
| Site B | 100.100.2.202 | 2 vCPU / 4GB RAM (Low-Power CPU) | x86_64 | No | 20GB SSD |

### Works 3. Network Topology & Latency Analysis

* Site A, Site B 서버는 서로 다른 네트워크에 위치해 있지만, 물리적으로 가까운 위치에 있으며 동일한 네트워크 도메인 내에 위치해 있습니다.

    * 같은 Metropolitan Area Network에 위치해 있어, Tailscale 기준 < 5ms의 Latency를 기대할 수 있습니다.

    * 매우 낮은 Latency를 가지고 있어 JuiceFS / K3s 클러스터 구축에 적합합니다.

---

## Phase 1. Logical Abstraction via YANG Modeling

### Works 1. Base Type Definitions: [common-types.yang](./compute-model/common-types.yang)

* K3s 노드 역할과 우선순위를 정의하는 공통 유형 모듈입니다.

### Works 2. Compute Resource Abstraction: [resource-compute.yang](./compute-model/resource-compute.yang)

* vCPU, Memory, Burstable 여부 등 컴퓨팅 자원 관련 속성을 정의하는 모듈입니다.

* 엄격한 검증을 적용하여 각 노드의 컴퓨팅 자원 사양이 허용된 범위 내에 있도록 합니다.

### Works 3. Network Perimeter & Policy Modeling: [resource-network.yang](./compute-model/resource-network.yang)

* 엄격하게 Tailscale IP 주소만 허용하도록 구성이 된 네트워크 자원 모델입니다.

* Cloud / On-Prem 자원을 구분할 수 있도록 구성되어 있습니다.

    * AWS: zone "cloud"

    * Site A, Site B: zone "on-prem"

### Works 4. Distributed Storage Logic Modeling: [resource-storage.yang](./compute-model/resource-storage.yang)

* JuiceFS의 메인 스토리지 노드와 마운트 전용 보조 노드를 구분하는 스토리지 자원 모델입니다.

* 캐시 할당량을 GB 단위로 명확히 정의하여, 각 노드의 스토리지 자원 사양이 허용된 범위 내에 있도록 합니다.

### Works 5. Holistic Cluster Integration: [hybrid-cloud.yang](./compute-model/hybrid-cloud.yang)

* 클러스터 전체를 포괄하는 최상위 모델로, 각 노드의 역할과 자원 사양을 통합적으로 표현합니다.

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
yanglint -f tree ./models/hybrid-cloud.yang
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

* **[aws-t4g-node Example](./compute-json/aws-t4g-node.json)**

* **[site-a-node Example](./compute-json/site-a-node.json)**

* **[site-b-node Example](./compute-json/site-b-node.json)**

### Works 3. Schema Compliance Verification & Data Integrity Audit

```bash
yanglint -p models -t data compute-models/hybrid-cloud.yang compute-json/aws-t4g-node.json
yanglint -p models -t data compute-models/hybrid-cloud.yang compute-json/site-a-node.json
yanglint -p models -t data compute-models/hybrid-cloud.yang compute-json/site-b-node.json
```

### Works 4. Exception Handling & Constraint Enforcement Scenarios

JSON 데이터에 에러가 있는 경우, `yanglint`가 상세한 오류 메시지를 제공하여 문제를 쉽게 파악할 수 있습니다.

* Tailscale IP 주소가 패턴에 맞지 않는 경우

    ```plain text
    libyang err : Unsatisfied pattern - "100.10.1.201" does not conform to "100\.(6[4-9]|[7-9][0-9]|1[0-1][0-9]|12[0-7])\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)". (Schema location /hybrid-cloud:cluster/node/network/tailscale-ip, data location /hybrid-cloud:network, line number 22.)
    YANGLINT[E]: Failed to parse input data file "compute-json/aws-t4g-node.json".
    ```

* 필드의 값이 허용된 범위를 벗어난 경우

    ```plain text
    libyang err : Unsatisfied range - value "16" is out of the allowed range. (Schema location /hybrid-cloud:cluster/node/compute/vcpu, data location /hybrid-cloud:compute, line number 13.)
    YANGLINT[E]: Failed to parse input data file "compute-json/site-b-node.json".
    ```

---

## Phase 3. Overlay Networking & Distributed Storage

`Works 1.` - `Works 2. (~1. Tailscale)` 과정까지의 자동화 스크립트가 존재합니다.

* **[Terraform: aws-t4g-node.tf](./terraform-cloud/aws-t4g-node.tf)**

* **[Shell Script: site-a-node-init.sh](./script-onprem/site-a-node-init.sh)**

* **[Shell Script: site-b-node-init.sh](./script-onprem/site-b-node-init.sh)**

### Works 1. Node Realization: Instance Provisioning

#### 0. Shared Public Key Authentication Setup

```bash
# 로컬에서 SSH Key Pair 생성
ssh-keygen -t ed25519 -f ~/.ssh/hybrid-cloud_key -N ""

# 생성된 공개 키 확인
cat ~/.ssh/hybrid-cloud_key.pub
```

#### 1. aws-t4g-node

> Terraform으로 프로비저닝 및 초기 설정이 완료된 AWS EC2 인스턴스 환경

```bash
# 호스트 이름 변경
sudo hostnamectl set-hostname aws-t4g-node

# OpenSSH Server 설치 및 서비스 시작
sudo dnf update -y
sudo dnf install -y openssh-server
sudo systemctl enable --now sshd
```

#### 2. site-a-node

> KVM Hypervisor 가반의 VM 환경

```bash
# 호스트 이름 변경
sudo hostnamectl set-hostname site-a-node

# OpenSSH Server 설치 및 서비스 시작
sudo apt update && sudo apt upgrade -y
sudo apt install -y openssh-server
sudo systemctl enable --now ssh

# Public Key 등록
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "<PUBLIC_KEY>" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

#### 3. site-b-node

> Docker 기반 시스템 컨테이너를 활용한 VM 런타임 에뮬레이션

```bash
# Debian 13 Container 생성
docker run -d --name site-b-node --hostname site-b-node \
    --privileged --device /dev/net/tun:/dev/net/tun \
    -v /sys/fs/cgroup:/sys/fs/cgroup:rw --cgroupns host \
    jrei/systemd-debian

# 컨테이너 내부 환경 구축 - 필요 패키지 설치, SSH 접속 설정
docker exec -it site-b-node bash -c "
    apt update && apt upgrade -y && apt install -y openssh-server sudo curl locales && 
    sed -i '/en_US.UTF-8 UTF-8/s/^# //g' /etc/locale.gen && locale-gen &&
    rm -f /etc/nologin && mkdir -p /run/sshd &&
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && 
    systemctl enable --now ssh
"

# Public Key 등록
docker exec -it site-b-node bash -c "
    mkdir -p ~/.ssh && chmod 700 ~/.ssh && 
    echo '<PUBLIC_KEY>' >> ~/.ssh/authorized_keys && 
    chmod 600 ~/.ssh/authorized_keys
"
```

### Works 2. Overlay Connectivity: Tailscale Mesh Integration

#### 1. Tailscale

* aws-t4g-node & site-a-node

    ```bash
    # Tailscale 설치
    curl -fsSL https://tailscale.com/install.sh | sh

    # Tailscale Login & Up
    sudo tailscale up --authkey <TAILSCALE_AUTH_KEY> --hostname $(hostname) --accept-dns=false --accept-routes=false
    ```

* site-b-node

    ```bash
    # 컨테이너 내부에서 Tailscale 설치 및 연결
    docker exec -it site-b-node bash -c "
        curl -fsSL https://tailscale.com/install.sh | sh &&
        sudo systemctl enable --now tailscaled &&
        tailscale up --authkey <TAILSCALE_AUTH_KEY> --hostname site-b-node --accept-dns=false --accept-routes=false
    "
    ```

#### 2. Admin Console에서 IP 주소 할당

* aws-t4g-node: `100.100.2.101`

* site-a-node: `100.100.2.201`

* site-b-node: `100.100.2.202`

#### 3. Management Laptop (neptune-mbp)

```ini
# ~/.ssh/config 파일에 다음 내용 추가
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

### Works 3. Storage Abstraction: JuiceFS Infrastructure Setup

> Node들과 분리된 스토리지 인프라가 S3-Compatable API 및 Redis 캐시를 제공합니다. 이를 통해 스토리지 인프라도 추상회된 자원으로 관리할 수 있습니다.

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