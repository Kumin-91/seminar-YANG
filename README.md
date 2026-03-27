# One Logical Infrastructure, Many Physical Realities: A YANG-Driven Hybrid Cloud with K3s

[Phase 0. Physical Inventory & Resource Specification](#phase-0-physical-inventory--resource-specification)

[Phase 1. Logical Abstraction via YANG Modeling](#phase-1-logical-abstraction-via-yang-modeling)

[Phase 2. Data Integrity & Schema Validation](#phase-2-data-integrity--schema-validation)

[Phase 3. Storage Abstraction: JuiceFS Infrastructure Setup](#phase-3-storage-abstraction-juicefs-infrastructure-setup)

## Phase 0. Physical Inventory & Resource Specification

### Works 1. Strategic Role Allocation & Infrastructure Hierarchy

| Location | Gateway/Ingress | Control Plane | Worker Node |
| --- | --- | --- | --- |
| **AWS** | Primary | Primary | Fallback |
| **Site A** | Secondary| Secondary | Primary |
| **Site B** | ❌ | ❌ | Secondary |

### Works 2. Hardware Inventory & Compute/Storage Quotas

| Location | IP | Port | Compute | Arch | Burstable | Cache Quota |
| --- | --- | --- | --- | --- | --- | --- |
| **AWS** | Dynamic | 22 | t4g.medium | arm64 | Yes | 5GB EBS |
| **Site A** | 192.168.1.202 | 22 | 4 vCPU / 8GB RAM | x86_64 | No | 30GB NVME |
| **Site B** | 100.100.1.253 | 30022 | 2 vCPU / 4GB RAM | x86_64 | No | 20GB SSD |

> AWS의 IP 주소는 Terraform 프로비저닝 후 동적으로 할당됩니다.

---

## Phase 1. Logical Abstraction via YANG Modeling

### Works 1. Base Type Definitions: [common-types.yang](./01-schema/common-types.yang)

* Platform (AWS/On-Premise), Arch, K3s Role 등에 대한 표준 데이터 타입을 정의합니다.

* AWS 인스턴스 타입은 정규표현식을 통해 medium 이하 규격으로 엄격히 제한됩니다.

### Works 2. Compute Resource Abstraction: [res-compute.yang](./01-schema/res-compute.yang)

* 플랫폼별 연산 자원 명세를 담당하며, Platform 값에 따라 입력 항목을 동적으로 강제합니다.

* AWS: instance-type 기반의 규격화된 자원 할당.

* On-Premise: vCPU 및 Memory 범위를 직접 지정하여 하드웨어 제약 내에서 자원을 선언합니다.

### Works 3. Network Perimeter & Policy Modeling: [res-network.yang](./01-schema/res-network.yang)

* 초기 프로비저닝 (Underlay)을 위한 접속 계정과 포트 정보를 정의합니다.

* AWS의 Late Binding 전략과 On-Premise의 Early Binding 전략을 구분하여 모델링합니다.

### Works 4. Distributed Storage Logic Modeling: [res-storage.yang](./01-schema/res-storage.yang)

* 분산 스토리지 (JuiceFS) 환경 구성을 위한 엔드포인트와 캐시 정책을 정의합니다.

* `secret-file-path`를 통해 민감한 자격 증명을 모델에서 분리하여 보안 사고를 원천 차단합니다.

### Works 5. Holistic Cluster Integration: [hybrid-cloud.yang](./01-schema/hybrid-cloud.yang)

* 개별 리소스 모델을 통합하여 하이브리드 클러스터의 단일 진실 원천 (SSoT)을 구축합니다.

* 각 노드의 기술적 역할뿐만 아니라 클러스터 내의 전략적 우선순위를 함께 관리합니다.

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
            +--rw secret-file-path    string
            +--rw cache-size          uint32
    ```

### Works 2. Data Instance Modeling: Node-specific JSON Manifests

* **[aws-t4g-node.json](./02-inventory/aws-t4g-node.json)**

* **[site-a-node.json](./02-inventory/site-a-node.json)**

* **[site-b-node.json](./02-inventory/site-b-node.json)**

### Works 3. Schema Compliance Verification & Data Integrity Audit

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

### Works 4. Exception Handling & Constraint Enforcement Scenarios

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

### Works 1. Containerized Storage Backend Deployment

* **[docker-compose.yml](./03-storage-provider/docker-compose.yml)** 을 활용하여 스토리지 백엔드를 코드화 했습니다.

* Host OS 환경에 의존하지 않고, 컨테이너 기술을 통해 엔진의 배포와 버전 관리를 단순화했습니다.

### Works 2. Storage Provider Specs & Technical Highlights

| Component | Service | Port | Backend Storage |
| --- | --- | --- | --- |
| Metadata Engine | Redis | 4279 | Docker Volume (on NVME) |
| Object Storage | MinIO | 4200 (S3 API) / 4201 (Dashboard) | ZFS Dataset |

* MinIO의 데이터 영속성을 위해 ZFS Storage Pool을 직접 매핑하여 데이터 안정성과 성능을 극대화했습니다.

* 기존 서비스 및 시스템 서비스와의 포트 간섭을 원천 차단하기 위해 전용 포트를 할당했습니다.

---

## Phase 4. Automated Node Bootstrapping

### Works 0. Shared Public Key Authentication Setup

```bash
# 로컬에서 SSH Key Pair 생성
ssh-keygen -t ed25519 -f ~/.ssh/hybrid-cloud_key -N ""

# 생성된 공개 키 확인
cat ~/.ssh/hybrid-cloud_key.pub
```

### Works 1. Data-Driven EC2 Provisioning & Auto-Configuration with Terraform

> Terraform과 JSON 인벤토리를 결합하여 인프라 선언과 설정을 완벽히 분리한 제로 터치 프로비저닝 환경을 구축하였습니다.

#### 1. Inventory-Driven Resource Declaration

* 인프라의 명세를 Terraform 코드 ([main.tf](./04-bootstrap/terraform/main.tf))와 분리하여 별도의 JSON 파일로 관리합니다. 

* `jsondecode` 함수를 사용하여 외부 JSON 인벤토리를 실시간으로 파싱하고, Terraform `locals` 변수로 변환하여 리소스에 주입합니다. 

* 노드 이름 (`name`), 인스턴스 유형 (`instance-type`), EBS 볼륨 크기(`ebs-size`), 퍼블릭 IP 할당 여부(`public-ip-required`) 등 핵심 속성을 데이터 중심으로 제어합니다.

#### 2. Terraform-Native Provisioning Logic

* AWS의 표준 리소스와 Terraform의 템플릿 기능을 활용하여 인스턴스의 생명주기를 관리합니다.

* `aws_key_pair` 리소스를 통해 사전에 정의된 공개 키를 인스턴스에 자동으로 주입하여 초기 접근 권한을 확보합니다.

* `templatefile` 함수와 [`tailscale_setup.tftpl`](./04-bootstrap/terraform/tailscale_setup.tftpl)를 사용하여 쉘 스크립트와 Terraform 변수를 결합한 설정 템플릿을 구성하였습니다. 

#### 3. Post-Provisioning Auto-Configuration

* 인스턴스 생성 직후, `user_data`를 통해 OS 레벨의 초기 설정을 자동으로 수행합니다. 

* 인벤토리에 정의된 노드 이름을 OS 호스트네임으로 즉시 반영합니다. 

* Tailscale 설치 및 자동 합류를 수행하여, 프로비저닝된 노드가 즉시 클러스터 네트워크에 통합될 수 있도록 합니다.

### Works 2. JSON-Driven On-Premise Bootstrapping with Custom Shell Scripts

> AWS의 완전 자동화 방식과 달리, 온프레미스 환경의 특수성 (비밀번호 인증 기반 초기 상태)을 고려하여 JSON Manifest와 쉘 스크립트 기반의 반자동화 브릿지를 구축하였습니다.

#### 1.JSON Manifest Injection

> **TBD**

#### 2. SSH Key Distribution & Disable Password Authentication

> **TBD**

#### 3. Tailscale Integration & Network Unification

> **TBD**

### Works 3. Custom Docker Command for Virtualized Node Simulation

* site-b-node의 경우, 호스트 시스템에 직접 접근이 불가능하기 때문에, Docker 컨테이너를 활용하여 가상화된 노드 시뮬레이터를 구축합니다.

    ```bash
    export CONTAINER_NAME=hybrid-cloud-node-simulator
    docker rm -f $CONTAINER_NAME 2>/dev/null
    docker run -d \
        -p 30022:22 \
        --name $CONTAINER_NAME \
        --hostname $CONTAINER_NAME \
        --privileged \
        --device /dev/net/tun:/dev/net/tun \
        --cgroupns host \
        -v /sys/fs/cgroup:/sys/fs/cgroup:rw \
        jrei/systemd-debian
    ```

---

## Phase 5. Provisioning Automation via Ansible

> **TBD**

---

## Phase 6. Hybrid Cluster Orchestration & Realization

> **TBD**