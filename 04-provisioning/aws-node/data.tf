# 1. Base 인프라 참조 
data "terraform_remote_state" "base" {
    backend = "local"
    config  = { path = "${path.module}/../aws-base/terraform.tfstate" }
}

locals {
    region    = data.terraform_remote_state.base.outputs.region
    vpc_id    = data.terraform_remote_state.base.outputs.vpc_id
    subnet_id = data.terraform_remote_state.base.outputs.subnet_id
    sg_id     = data.terraform_remote_state.base.outputs.sg_id
    key_name  = data.terraform_remote_state.base.outputs.key_name
}

# 2. 노드 명세 (YANG JSON) 
variable "manifest_path" {
  type        = string
  description = "Target JSON inventory file path"
}

locals {
    raw_data = jsondecode(file(var.manifest_path))
    node     = local.raw_data["hybrid-cloud:cluster"]["node"][0]

    node_name     = local.node["name"]
    arch          = local.node.compute["arch"]
    instance_type = local.node.compute["instance-type"]
    ebs_size      = local.node.compute["ebs-size"]
    associate_ip  = local.node.network["public-ip-required"]
}