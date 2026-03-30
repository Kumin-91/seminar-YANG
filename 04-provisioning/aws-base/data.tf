# 노드 명세 (YANG JSON) 
variable "manifest_path" {
  type        = string
  description = "Target JSON inventory file path"
}

locals {
    raw_data = jsondecode(file(var.manifest_path))
    node     = local.raw_data["aws-provider:aws-config"]

    region              = local.node["region"]
    vpc_cidr            = local.node["vpc-cidr"]
    public_subnet_cidr  = local.node["public-subnet-cidr"]
    private_subnet_cidr = local.node["private-subnet-cidr"]
    public_key_path     = local.node["public-key-dir"]
}