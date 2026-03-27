# provider 
provider "aws" {
    region = "ap-northeast-2"
}

variable "PUBLIC_KEY" {
    type        = string
    description = "SSH Public Key for EC2 instance access"
}

variable "TAILSCALE_AUTH_KEY" {
    type        = string
    sensitive   = true
    description = "Tailscale Authentication Key for node connectivity"
}

variable "manifest_path" {
    type        = string
    default     = "../../02-inventory/aws-t4g-node.json"
    description = "Target JSON inventory file path"
}

# 주입된 경로의 JSON을 동적으로 로드
locals {
    manifest = jsondecode(file(var.manifest_path))["hybrid-cloud:cluster"]["node"][0]

    node_name     = local.manifest.name
    instance_type = local.manifest.compute.instance-type
    ebs_size      = local.manifest.compute.ebs-size
    associate_ip  = local.manifest.network.public-ip-required
}

output "public_ip" {
    value = aws_instance.node.public_ip
}