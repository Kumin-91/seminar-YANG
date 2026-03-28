# provider 
provider "aws" {
    region = "ap-northeast-2"
}

variable "public_key_path" {
    type        = string
    default     = "~/.ssh/hybrid-cloud_key.pub"
    description = "Path to the SSH public key file"
}

variable "manifest_path" {
    type        = string
    default     = "../../02-inventory/aws-t4g-node.json"
    description = "Target JSON inventory file path"
}

# 주입된 경로의 JSON을 동적으로 로드
locals {
    manifest = jsondecode(file(var.manifest_path))["hybrid-cloud:cluster"]["node"][0]

    node_name     = local.manifest["name"]
    arch          = local.manifest.compute["arch"]
    instance_type = local.manifest.compute["instance-type"]
    ebs_size      = local.manifest.compute["ebs-size"]
    associate_ip  = local.manifest.network["public-ip-required"]
}

# AMI 검색
data "aws_ami" "selected" {
    most_recent = true
    owners      = ["amazon"]

    filter {
        name   = "name"
        # Amazon Linux 2023 기준: 아키텍처에 따라 x86_64 또는 arm64가 이름에 포함됨
        values = ["al2023-ami-2023*-kernel-6.1-${local.arch}"]
    }

    filter {
        name   = "architecture"
        values = [local.arch]
    }
}

output "public_ip" {
    value = aws_instance.node.public_ip
}