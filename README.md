# One Logical Infrastructure, Many Physical Realities: A YANG-Driven Hybrid Cloud with K3s

## 🗿 Milestone

### Phase 0. Physical Inventory

| Location | Access Point | Storage Node | Control Plane | Worker Node |
| --- | --- | --- | --- | --- |
| **AWS** | Primary | ❌ | Primary | Fallback |
| **Site A** | Secondary | Primary | Secondary | Primary |
| **Site B** | ❌ | ❌ | ❌ | Secondary |

* Site A, Site B 서버는 서로 다른 네트워크에 위치해 있지만, 물리적으로 가까운 위치에 있으며 동일한 네트워크 도메인 내에 위치해 있습니다.

    * 같은 Metropolitan Area Network에 위치해 있어, Tailscale 기준 < 5ms의 Latency를 기대할 수 있습니다.

    * 매우 낮은 Latency를 가지고 있어 JuiceFS / K3s 클러스터 구축에 적합합니다.

#### 1. AWS

* **Network:** 100.100.1.AWS

* **Compute:** 2 vCPU / 4GB RAM (t3.medium)

* **Burstable:** Yes

* **Storage:** 20GB (Root EBS) / JuiceFS Mount

* **Cache Quota:** 5GB (Root EBS)

#### 2. Site A

* **Network:** 100.100.1.AAA

* **Compute:** 4 vCPU / 8GB RAM (Mid-Range CPU)

* **Burstable:** Yes (Up to 8 vCPU / 16GB RAM)

* **Storage:** S3 Backend (Or Self-Hosted S3 Compatible) + 1TB ZFS Pool

* **Cache Quota:** 100GB NVME

#### 3. Site B

* **Network:** 100.100.1.BBB

* **Compute:** 2 vCPU / 4GB RAM (Low-Power CPU)

* **Burstable:** No

* **Storage:** N/A (JuiceFS Mount Only)

* **Cache Quota:** 20GB SSD

### Phase 1. YANG Modeling

#### 1. Node Inventory



#### 2. Network Topology



#### 3. Storage Topology



### Phase 2. Virtual Network (Tailscale) & Virtual Storage (JuiceFS)

#### 1. Tailscale

* AWS와 Site A는 같은 Tailnet 네트워크에 연결되어 있음

* Site B는 별도의 Tailnet 네트워크에 속해 있으며, Shared-In 기능을 통해 같은 Tailnet에 연결되어 있음

#### 2. JuiceFS

> **TBD**

### Phase 3. K3s Cluster Deployment

## 🪧 Seminar Outline

> **TBD**