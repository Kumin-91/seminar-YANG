# 노드 명세 (YANG JSON) 
variable "manifest_path" {
  type        = string
  description = "Target JSON inventory file path"
}

variable "ssh_key_path" {
  type        = string
  description = "Path to the public key for EC2 instance access"
}

locals {
    raw_data = jsondecode(file(var.manifest_path))
    node     = local.raw_data["aws-provider:aws-config"]

    region              = local.node["region"]
    vpc_cidr            = local.node["vpc-cidr"]
    public_subnet_cidr  = local.node["public-subnet-cidr"]
    private_subnet_cidr = local.node["private-subnet-cidr"]
    public_key_path     = var.ssh_key_path
}