# provider 
provider "aws" {
    region = local.region
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