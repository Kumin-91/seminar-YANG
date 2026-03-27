# One Logical Infrastructure, Many Physical Realities: A YANG-Driven Hybrid Cloud with K3s

[Phase 0. Physical Inventory & Resource Specification](#phase-0-physical-inventory--resource-specification)

[Phase 1. Logical Abstraction via YANG Modeling](#phase-1-logical-abstraction-via-yang-modeling)

[Phase 2. Data Integrity & Schema Validation](#phase-2-data-integrity--schema-validation)

[Phase 3. Storage Abstraction: JuiceFS Infrastructure Setup](#phase-3-storage-abstraction-juicefs-infrastructure-setup)

[Phase 4. Automating Node Provisioning with Terraform & Shell Scripting](#phase-4-automating-node-provisioning-with-terraform--shell-scripting)

## Phase 0. Physical Inventory & Resource Specification

### Step 1. Strategic Role Allocation & Infrastructure Hierarchy

| Location | Gateway/Ingress | Control Plane | Worker Node |
| --- | --- | --- | --- |
| **AWS** | Primary | Primary | Fallback |
| **Site A** | Secondary| Secondary | Primary |
| **Site B** | ❌ | ❌ | Secondary |

### Step 2. Hardware Inventory & Compute/Storage Quotas

| Location | IP | Port | Compute | Arch | Burstable | Cache Quota |
| --- | --- | --- | --- | --- | --- | --- |
| **AWS** | Dynamic | 22 | t4g.medium | arm64 | Yes | 5GB EBS |
| **Site A** | 192.168.1.202 | 22 | 4 vCPU / 8GB RAM | x86_64 | No | 30GB NVME |
| **Site B** | 100.100.1.253 | 30022 | 2 vCPU / 4GB RAM | x86_64 | No | 20GB SSD |

> AWS의 IP 주소는 Terraform 프로비저닝 후 동적으로 할당됩니다.

---

## Phase 1. Logical Abstraction via YANG Modeling

### Step 1. Base Type Definitions: [common-types.yang](./01-schema/common-types.yang)

* Platform (AWS/On-Premise), Arch, K3s Role 등에 대한 표준 데이터 타입을 정의합니다.

* AWS 인스턴스 타입은 정규표현식을 통해 medium 이하 규격으로 엄격히 제한됩니다.

### Step 2. Compute Resource Abstraction: [res-compute.yang](./01-schema/res-compute.yang)

* 플랫폼별 연산 자원 명세를 담당하며, Platform 값에 따라 입력 항목을 동적으로 강제합니다.

* AWS: instance-type 기반의 규격화된 자원 할당.

* On-Premise: vCPU 및 Memory 범위를 직접 지정하여 하드웨어 제약 내에서 자원을 선언합니다.

### Step 3. Network Perimeter & Policy Modeling: [res-network.yang](./01-schema/res-network.yang)

* 초기 프로비저닝 (Underlay)을 위한 접속 계정과 포트 정보를 정의합니다.

* AWS의 Late Binding 전략과 On-Premise의 Early Binding 전략을 구분하여 모델링합니다.

### Step 4. Distributed Storage Logic Modeling: [res-storage.yang](./01-schema/res-storage.yang)

* 분산 스토리지 (JuiceFS) 환경 구성을 위한 엔드포인트와 캐시 정책을 정의합니다.

* 자격 증명과 같은 민감 데이터를 YANG 명세에서 배제하고 앤서블의 동적 주입 방식으로 전환하여, 설계도의 범용성을 높이고 보안 사고를 원천 차단합니다.

### Step 5. Holistic Cluster Integration: [hybrid-cloud.yang](./01-schema/hybrid-cloud.yang)

* 개별 리소스 모델을 통합하여 하이브리드 클러스터의 단일 진실 원천 (SSoT)을 구축합니다.

* 각 노드의 기술적 역할뿐만 아니라 클러스터 내의 전략적 우선순위를 함께 관리합니다.

---

## Phase 2. Data Integrity & Schema Validation

### Step 0. Environment Setup: libyang & yanglint (Rocky Linux 9)

```bash
# libyang 설치
sudo dnf install libyang

# yanglint 설치 확인
yanglint --version
# yanglint 2.0.7
```

### Step 1. Hierarchical Schema Visualization & Structural Audit

* YANG 모델의 계층적 구조와 논리적 일관성을 검증하기 위해 `yanglint`의 트리 출력 기능을 활용합니다.

    ```bash
    yanglint -f tree ./01-schema/hybrid-cloud.yang
    ```

* YANG 모델에 에러가 있는 경우, `yanglint`가 상세한 오류 메시지를 제공하여 문제를 쉽게 파악할 수 있습니다.

    ```plain text
    libyang err : Invalid keyword ";" as a child of "leaf". (Line number 37.)
    libyang err : Importing "res-compute" module failed.
    YANGLINT[E]: Processing schema module from ./01-schema/hybrid-cloud.yang failed.
    ```

* YANG 모델의 계층적 구조는 다음과 같이 시각적으로 표현됩니다.

    ```plain text
    module: hybrid-cloud
    +--rw cluster
        +--rw node* [name]
            +--rw name               string
            +--rw role-assignment* [role]
            |  +--rw role        ct:k3s-role
            |  +--rw priority    ct:node-role
            +--rw compute
            |  +--rw platform           ct:node-platform
            |  +--rw arch               ct:cpu-arch
            |  +--rw (platform-spec)
            |     +--:(aws)
            |     |  +--rw instance-type    ct:aws-instance-type
            |     |  +--rw ebs-size?        uint16
            |     +--:(on-premise)
            |        +--rw vcpu      uint8
            |        +--rw memory    uint8
            +--rw network
            |  +--rw ssh-user                string
            |  +--rw ssh-port?               inet:port-number
            |  +--rw (bootstrap-strategy)
            |     +--:(aws-strategy)
            |     |  +--rw public-ip-required?   boolean
            |     |  +--rw use-eip?              boolean
            |     +--:(on-premise-strategy)
            |        +--rw bootstrap-ip    inet:ip-address
            +--rw storage
            +--rw s3-endpoint         string
            +--rw redis-endpoint      string
            +--rw cache-size          uint32
    ```

### Step 2. Data Instance Modeling: Node-specific JSON Manifests

* **[aws-t4g-node.json](./02-inventory/aws-t4g-node.json)**

* **[site-a-node.json](./02-inventory/site-a-node.json)**

* **[site-b-node.json](./02-inventory/site-b-node.json)**

### Step 3. Schema Compliance Verification & Data Integrity Audit

```bash
for f in 02-inventory/*.json; do 
    yanglint -p 01-schema -t data 01-schema/hybrid-cloud.yang "$f" && echo "YANG Lint Pass: $f"
done
```

```bash
# Expected Output
YANG Lint Pass: 02-inventory/aws-t4g-node.json
YANG Lint Pass: 02-inventory/site-a-node.json
YANG Lint Pass: 02-inventory/site-b-node.json
```

### Step 4. Exception Handling & Constraint Enforcement Scenarios

JSON 데이터에 에러가 있는 경우, `yanglint`가 상세한 오류 메시지를 제공하여 문제를 쉽게 파악할 수 있습니다.

* 예시: `instance-type`이 `t4g.medium`을 초과하는 경우

    ```plain text
    libyang err : Unsatisfied pattern - "t4g.large" does not conform to "[tcrm][1-8][a-z]*\.(nano|micro|small|medium)". (Schema location /hybrid-cloud:cluster/node/compute/platform-spec/aws/instance-type, data location /hybrid-cloud:compute, line number 19.)
    YANGLINT[E]: Failed to parse input data file "02-inventory/aws-t4g-node.json".
    ```

* 예시: On-Premise 노드에 `public-ip-required`가 `true`로 설정된 경우

    ```plain text
    libyang err : Data for both cases "aws-strategy" and "on-premise-strategy" exist. (Schema location /hybrid-cloud:cluster/node/network/bootstrap-strategy, data location /hybrid-cloud:network, line number 27.)
    YANGLINT[E]: Failed to parse input data file "02-inventory/site-a-node.json".
    ```

---

## Phase 3. Storage Abstraction: JuiceFS Infrastructure Setup

> 컴퓨트 노드와 완전히 격리된 독립형 스토리지 엔진을 구축합니다. S3 호환 API (MinIO)와 고성능 메타데이터 엔진 (Redis)을 추상화된 자원으로 제공하여 하이브리드 클러스터의 데이터 일관성을 보장합니다.

### Step 1. Containerized Storage Backend Deployment

* **[docker-compose.yml](./03-storage-provider/docker-compose.yml)** 을 활용하여 스토리지 백엔드 구성을 코드화합니다.

* Host OS 환경에 의존하지 않고, 컨테이너 기술을 통해 엔진의 배포와 버전 관리를 단순화합니다.

### Step 2. Storage Provider Specs & Technical Highlights

| Component | Service | Port | Backend Storage |
| --- | --- | --- | --- |
| Metadata Engine | Redis | 4279 | Docker Volume (on NVME) |
| Object Storage | MinIO | 4200 (S3 API) / 4201 (Dashboard) | ZFS Dataset |

* MinIO의 데이터 영속성을 위해 ZFS Storage Pool을 직접 매핑하여 데이터 안정성과 성능을 극대화했습니다.

* 기존 서비스 및 시스템 서비스와의 포트 간섭을 원천 차단하기 위해 전용 포트를 할당했습니다.

---

## Phase 4. Automating Node Provisioning with Terraform & Shell Scripting

### Step 0. Shared Public Key Authentication Setup

> 모든 노드 (AWS & On-Premise)의 통합 관리를 위해 공통 SSH Key Pair를 생성합니다. 이는 Phase 5의 Ansible이 비밀번호 없이 전 노드에 진입할 수 있는 신뢰의 기반이 됩니다.

```bash
# 로컬에서 SSH Key Pair 생성
ssh-keygen -t ed25519 -f ~/.ssh/hybrid-cloud_key -N ""

# 생성된 공개 키 확인
cat ~/.ssh/hybrid-cloud_key.pub
```

### Step 1. Terraform for AWS Node Provisioning

> AWS 자원 생성에만 집중하며, `user_data` 스크립트를 완전히 배제하여 인프라 프로비저닝과 노드 부트스트래핑의 경계를 명확히 분리합니다. 이는 가장 순수한 형태의 IaC로서, 플랫폼에 종속되지 않는 하이브리드 클라우드 구축의 기반이 됩니다.

#### 1. [`main.tf`](./04-provisioning/aws/main.tf)

* AWS 리전 (`ap-northeast-2`)을 설정하고, SSH 공개 키 및 YANG 기반 JSON 인벤토리 파일의 경로를 변수로 관리하여 유연성을 확보합니다.

* `jsondecode` 함수를 사용하여 주입된 JSON 인벤토리로부터 노드 이름, 인스턴스 유형, 디스크 크기, 공인 IP 필요 여부 등의 자원 명세를 동적으로 읽어옵니다.

* 프로비저닝 완료 후 Ansible이 즉시 접속할 수 있도록 생성된 인스턴스의 공인 IP를 출력합니다.

#### 2. [`network.tf`](./04-provisioning/aws/network.tf)

* Ansible 접속을 위한 SSH (TCP 22) 포트와 하이브리드 메시 네트워크 구성을 위한 Tailscale (UDP 41641) 포트만을 정밀하게 개방합니다.

* 패키지 업데이트 및 외부 서비스 연결을 위해 모든 아웃바운드 트래픽 (Egress)을 허용합니다.

#### 3. [`compute.tf`](./04-provisioning/aws/compute.tf)

* JSON에서 추출한 `instance_type`과 `ebs_size` 등의 명세에 따라 EC2 인스턴스를 생성합니다. 

* 하이브리드 클라우드의 오버레이 네트워킹을 원활하게 지원하기 위해 인스턴스의 `source_dest_check` 옵션을 `false`로 설정합니다. 

* 변수로 지정된 경로의 공개 키 파일을 읽어 (`file()` 함수 사용) 인스턴스에 주입함으로써, 별도의 비밀번호 없이 Ansible이 즉시 진입할 수 있는 통로를 확보합니다.

### Step 2. Shell Scripting for On-Premise Access Bridge

> 전용 API 등 별도의 프로비저닝 수단이 부재한 On-Premise 환경의 한계를 극복하기 위해, SSH 도구를 활용합니다. 이는 Ansible이 대상 노드에 진입하여 구성 관리를 수행하기 위한 사전 준비 단계입니다.

#### 1. [`public_key.sh`](./04-provisioning/on-premise/public_key.sh)

* 리눅스 표준 유틸리티인 `ssh-copy-id`를 사용하여 로컬 머신의 공개 키를 원격 On-Premise 노드에 안전하게 복사합니다.

* 대상 노드의 IP 주소, SSH 포트, 사용자 계정을 변수로 받아 다양한 On-Premise 환경 (Proxmox VM, Bare-metal 등)에 유연하게 대응합니다.

* `ssh-copy-id` 고유의 기능을 통해 중복 키 등록을 방지하고, 원격지의 `.ssh` 디렉토리 및 `authorized_keys` 파일 권한을 보안 정책에 맞게 자동 조정합니다.

#### 2. Orchestration-Ready Design

* 스크립트는 복잡한 노드 설정 기능을 배제하고 오직 SSH 신뢰 관계 구축이라는 단일 목적에만 집중합니다.

* 개별 노드에 대한 수동 실행을 넘어, 외부 오케스트레이터 (Make 또는 Python)가 여러 JSON 인벤토리를 순회하며 본 스크립트를 루프 형태로 호출할 수 있도록 설계되었습니다.

### Step 3. Unified Orchestration with Python

> 하이브리드 클라우드 구축의 전 과정을 조율하는 중앙 통제 레이어입니다. 플랫폼마다 파편화된 프로비저닝 도구들을 단일 인터페이스로 통합하여, 설계와 실제 인프라 사이의 간극을 자동화로 메웁니다.

#### 1. [provisioner.py](./04-provisioning/provisioner.py)

* Data-Driven Execution

    * `02-inventory/` 폴더 내의 모든 JSON 매니페스트를 순회하며 platform 타입을 동적으로 분석합니다.

    * **`aws`** 타입일 경우 Terraform을, **`on-premise`** 타입일 경우 전용 Shell 스크립트를 선택적으로 호출하여 각 환경에 최적화된 프로비저닝을 수행합니다.

* Path Independence

    * `os.path.abspath(__file__)`를 활용하여 스크립트의 절대 경로를 계산합니다.

    * 이로 인해 프로젝트 루트나 하위 디렉토리 등 어느 위치에서 실행하더라도 인벤토리 파일과 Terraform 코드를 정확하게 탐색할 수 있는 견고함을 갖췄습니다.

* Hybrid Data Model Support

    * YANG 모델의 중첩 구조와 사용자가 작성한 평면 구조를 동시에 지원하도록 설계되었습니다.

    * `.get()` 메서드를 활용한 방어적 코딩을 통해 데이터 누락 시에도 기본값을 할당하거나 안전하게 실행을 중단하여 인프라 오염을 방지합니다.

#### 2. Orchestration Flow

* **Inventory Parsing:** `02-inventory/`의 JSON 데이터를 로드하여 노드별 명세를 파악합니다.

* **Tool Selection:** Platform 타입 (`aws` vs `on-premise`)에 따라 적절한 하위 모듈을 트리거합니다.

* **Credential Injection:** 공통 SSH 공개 키를 AWS 키 페어로 등록하거나, On-Premise 노드의 `authorized_keys`에 주입합니다.

---