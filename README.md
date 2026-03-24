# One Logical Infrastructure, Many Physical Realities: A YANG-Driven Hybrid Cloud with K3s

[Phase 0. Physical Inventory & Resource Specification](#phase-0-physical-inventory)

[Phase 1. Logical Abstraction via YANG Modeling](#phase-1-logical-abstraction-via-yang-modeling)

[Phase 2. Data Integrity & Schema Validation](#phase-2-data-integrity--schema-validation)

[Phase 3. Overlay Networking & Distributed Storage](#phase-3-overlay-networking--distributed-storage)

[Phase 4. Provisioning Automation via Ansible](#phase-4-provisioning-automation-via-ansible)

[Phase 5. Hybrid Cluster Orchestration & Realization](#phase-5-hybrid-cluster-orchestration--realization)

## Working in Progress

> [Phase 3. Overlay Networking & Distributed Storage](#phase-3-overlay-networking--distributed-storage)
>> [Works 1. Node Realization: Instance Provisioning](#works-1-node-realization-instance-provisioning)  
>> [Works 2. Overlay Connectivity: Tailscale Mesh Integration](#works-2-overlay-connectivity-tailscale-mesh-integration)  
>> [Works 3. Storage Abstraction: JuiceFS Infrastructure Setup](#works-3-storage-abstraction-juicefs-infrastructure-setup)  

## Phase 0. Physical Inventory & Resource Specification

### Works 1. Strategic Role Allocation & Infrastructure Hierarchy

| Location | Access Point | Storage Node | Control Plane | Worker Node |
| --- | --- | --- | --- | --- |
| **AWS** | Primary | ❌ | Primary | Fallback |
| **Site A** | Secondary | Primary | Secondary | Primary |
| **Site B** | ❌ | ❌ | ❌ | Secondary |

### Works 2. Hardware Inventory & Compute/Storage Quotas

| Location | Network | Compute | Burstable | Storage | Cache Quota |
| --- | --- | --- | --- | --- | --- |
| AWS | 100.100.1.AWS | 2 vCPU / 4GB RAM (t3.medium) | Yes | 20GB (Root EBS) & JuiceFS Mount | 5GB EBS |
| Site A | 100.100.1.AAA | 4 vCPU / 8GB RAM (Mid-Range CPU) | Yes (Up to 8 vCPU / 16GB RAM) | S3 Backend & 1TB ZFS Pool | 100GB NVME |
| Site B | 100.100.1.BBB | 2 vCPU / 4GB RAM (Low-Power CPU) | No | JuiceFS Mount Only | 20GB SSD |

### Works 3. Network Topology & Latency Analysis

* Site A, Site B 서버는 서로 다른 네트워크에 위치해 있지만, 물리적으로 가까운 위치에 있으며 동일한 네트워크 도메인 내에 위치해 있습니다.

    * 같은 Metropolitan Area Network에 위치해 있어, Tailscale 기준 < 5ms의 Latency를 기대할 수 있습니다.

    * 매우 낮은 Latency를 가지고 있어 JuiceFS / K3s 클러스터 구축에 적합합니다.

---

## Phase 1. Logical Abstraction via YANG Modeling

### Works 1. Base Type Definitions: [common-types.yang](models/common-types.yang)

* K3s 노드 역할과 우선순위를 정의하는 공통 유형 모듈입니다.

### Works 2. Compute Resource Abstraction: [resource-compute.yang](models/resource-compute.yang)

* vCPU, Memory, Burstable 여부 등 컴퓨팅 자원 관련 속성을 정의하는 모듈입니다.

* 엄격한 검증을 적용하여 각 노드의 컴퓨팅 자원 사양이 허용된 범위 내에 있도록 합니다.

### Works 3. Network Perimeter & Policy Modeling: [resource-network.yang](models/resource-network.yang)

* 엄격하게 Tailscale IP 주소만 허용하도록 구성이 된 네트워크 자원 모델입니다.

* Cloud / On-Prem 자원을 구분할 수 있도록 구성되어 있습니다.

    * AWS: zone "cloud"

    * Site A, Site B: zone "on-prem"

### Works 4. Distributed Storage Logic Modeling: [resource-storage.yang](models/resource-storage.yang)

* JuiceFS의 메인 스토리지 노드와 마운트 전용 보조 노드를 구분하는 스토리지 자원 모델입니다.

* 캐시 할당량을 GB 단위로 명확히 정의하여, 각 노드의 스토리지 자원 사양이 허용된 범위 내에 있도록 합니다.

### Works 5. Holistic Cluster Integration: [hybrid-cloud.yang](models/hybrid-cloud.yang)

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
        |  +--rw vcpu?        uint8
        |  +--rw memory?      uint8
        |  +--rw burstable?   boolean
        +--rw network
        |  +--rw tailscale-ip    inet:ipv4-address
        |  +--rw zone?           enumeration
        +--rw storage
           +--rw type?         enumeration
           +--rw cache-size?   uint32
```

### Works 2. Data Instance Modeling: Node-specific JSON Manifests

**[Phase 0. Physical Inventory](#phase-0-physical-inventory)** 에서 정의한 리소스 사양에 따라, 각 노드에 대한 JSON 데이터를 작성하였습니다.

* **[AWS Node Example](./json/aws-node.json)**

* **[Site A Node Example](./json/site-a-node.json)**

* **[Site B Node Example](./json/site-b-node.json)**

### Works 3. Schema Compliance Verification & Data Integrity Audit

```bash
yanglint -p models -t data models/hybrid-cloud.yang json/aws-node.json
yanglint -p models -t data models/hybrid-cloud.yang json/site-a-node.json
yanglint -p models -t data models/hybrid-cloud.yang json/site-b-node.json
```

### Works 4. Exception Handling & Constraint Enforcement Scenarios

JSON 데이터에 에러가 있는 경우, `yanglint`가 상세한 오류 메시지를 제공하여 문제를 쉽게 파악할 수 있습니다.

* Tailscale IP 주소가 패턴에 맞지 않는 경우

    ```plain text
    libyang err : Unsatisfied pattern - "100.10.1.201" does not conform to "100\.(6[4-9]|[7-9][0-9]|1[0-1][0-9]|12[0-7])\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)". (Schema location /hybrid-cloud:cluster/node/network/tailscale-ip, data location /hybrid-cloud:network, line number 22.)
    YANGLINT[E]: Failed to parse input data file "json/aws-node.json".
    ```

* 필드의 값이 허용된 범위를 벗어난 경우

    ```plain text
    libyang err : Unsatisfied range - value "16" is out of the allowed range. (Schema location /hybrid-cloud:cluster/node/compute/vcpu, data location /hybrid-cloud:compute, line number 13.)
    YANGLINT[E]: Failed to parse input data file "json/site-b-node.json".
    ```

---

## Phase 3. Overlay Networking & Distributed Storage

### Works 1. Node Realization: Instance Provisioning

### Works 2. Overlay Connectivity: Tailscale Mesh Integration

> **TBD**

### Works 3. Storage Abstraction: JuiceFS Infrastructure Setup

> **TBD**

---

## Phase 4. Provisioning Automation via Ansible

> **TBD**

---

## Phase 5. Hybrid Cluster Orchestration & Realization

> **TBD**