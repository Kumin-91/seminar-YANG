# One Logical Infrastructure, Many Physical Realities: A YANG-Driven Hybrid Cloud with K3s

## 🗿 Milestone

### Phase 0. Physical Inventory

#### 1. Resource Role Assignment

| Location | Access Point | Storage Node | Control Plane | Worker Node |
| --- | --- | --- | --- | --- |
| **AWS** | Primary | ❌ | Primary | Fallback |
| **Site A** | Secondary | Primary | Secondary | Primary |
| **Site B** | ❌ | ❌ | ❌ | Secondary |

#### 2. Resource Specification

| Location | Network | Compute | Burstable | Storage | Cache Quota |
| --- | --- | --- | --- | --- | --- |
| AWS | 100.100.1.AWS | 2 vCPU / 4GB RAM (t3.medium) | Yes | 20GB (Root EBS) & JuiceFS Mount | 5GB EBS |
| Site A | 100.100.1.AAA | 4 vCPU / 8GB RAM (Mid-Range CPU) | Yes (Up to 8 vCPU / 16GB RAM) | S3 Backend & 1TB ZFS Pool | 100GB NVME |
| Site B | 100.100.1.BBB | 2 vCPU / 4GB RAM (Low-Power CPU) | No | JuiceFS Mount Only | 20GB SSD |

#### 3. Thoughts on Network Latency

* Site A, Site B 서버는 서로 다른 네트워크에 위치해 있지만, 물리적으로 가까운 위치에 있으며 동일한 네트워크 도메인 내에 위치해 있습니다.

    * 같은 Metropolitan Area Network에 위치해 있어, Tailscale 기준 < 5ms의 Latency를 기대할 수 있습니다.

    * 매우 낮은 Latency를 가지고 있어 JuiceFS / K3s 클러스터 구축에 적합합니다.

---

### Phase 1. YANG Modeling

#### 1. Common Types: [common-types.yang](models/common-types.yang)

* K3s 노드 역할과 우선순위를 정의하는 공통 유형 모듈입니다.

#### 2. Resource Compute: [resource-compute.yang](models/resource-compute.yang)

* vCPU, Memory, Burstable 여부 등 컴퓨팅 자원 관련 속성을 정의하는 모듈입니다.

* 엄격한 검증을 적용하여 각 노드의 컴퓨팅 자원 사양이 허용된 범위 내에 있도록 합니다.

#### 3. Resource Network: [resource-network.yang](models/resource-network.yang)

* 엄격하게 Tailscale IP 주소만 허용하도록 구성이 된 네트워크 자원 모델입니다.

* Cloud / On-Prem 자원을 구분할 수 있도록 구성되어 있습니다.

    * AWS: zone "cloud"

    * Site A, Site B: zone "on-prem"

#### 4. Resource Storage: [resource-storage.yang](models/resource-storage.yang)

* JuiceFS의 메인 스토리지 노드와 마운트 전용 보조 노드를 구분하는 스토리지 자원 모델입니다.

* 캐시 할당량을 GB 단위로 명확히 정의하여, 각 노드의 스토리지 자원 사양이 허용된 범위 내에 있도록 합니다.

#### 5. Hybrid Cloud: [hybrid-cloud.yang](models/hybrid-cloud.yang)

* 클러스터 전체를 포괄하는 최상위 모델로, 각 노드의 역할과 자원 사양을 통합적으로 표현합니다.

#### 6. Tree Schema Visualization

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

---

### Phase 2. JSON Schema Generation & Validation

#### 0. Configure YANG Tools

macOS 환경이 아닌, Rocky Linux 9.x 환경에서 진행하였습니다.

```bash
# libyang 설치
sudo dnf install libyang

# yanglint 설치 확인
yanglint --version
# yanglint 2.0.7
```

#### 1. JSON Schema Generation

**[Phase 0. Physical Inventory](#phase-0-physical-inventory)** 에서 정의한 리소스 사양에 따라, 각 노드에 대한 JSON 데이터를 작성하였습니다.

* **[AWS Node Example](./json/aws-node.json)**

* **[Site A Node Example](./json/site-a-node.json)**

* **[Site B Node Example](./json/site-b-node.json)**

#### 2. JSON Schema Validation

```bash
yanglint -p models -t data models/hybrid-cloud.yang json/aws-node.json
yanglint -p models -t data models/hybrid-cloud.yang json/site-a-node.json
yanglint -p models -t data models/hybrid-cloud.yang json/site-b-node.json
```

#### 3. JSON Schema Validation Error Examples

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

### Phase 3. Virtual Network (Tailscale) & Virtual Storage (JuiceFS)

#### 1. Tailscale

* AWS와 Site A는 같은 Tailnet 네트워크에 연결되어 있음

* Site B는 별도의 Tailnet 네트워크에 속해 있으며, Shared-In 기능을 통해 같은 Tailnet에 연결되어 있음

#### 2. JuiceFS

> **TBD**

---

### Phase 4. K3s Cluster Deployment

> **TBD**