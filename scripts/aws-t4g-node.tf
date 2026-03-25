# 변수 정의
variable "public_key" { type = string }
variable "tailscale_auth_key" { type = string}

# 0. provider 설정
provider "aws" {
    region = "ap-northeast-2"
}

# 1. SSH 키 페어 등록
resource "aws_key_pair" "hybrid_cloud" {
    key_name   = "hybrid-cloud-key"
    public_key = var.public_key
}

# 2. 보안 그룹 설정 (SSH & Tailscale)
resource "aws_security_group" "hybrid_cloud_sg" {
    name        = "hybrid-cloud-sg"
    description = "Allow SSH and Tailscale traffic" 

    # SSH
    ingress {
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
    }   

    # Tailscale
    ingress {
      from_port   = 41641
      to_port     = 41641
      protocol    = "udp"
      cidr_blocks = ["0.0.0.0/0"]
    }

    # Internet Access
    egress {
      from_port   = 0
      to_port     = 0
      protocol    = "-1"
      cidr_blocks = ["0.0.0.0/0"]
    }
}

# 3. EC2 인스턴스 (t4g.medium)
resource "aws_instance" "aws_t4g_node" {
    ami           = "ami-055751883cc1be227"
    instance_type = "t4g.medium"
    key_name      = aws_key_pair.hybrid_cloud.key_name
    vpc_security_group_ids = [aws_security_group.hybrid_cloud_sg.id]

    # 인스턴스가 패킷의 최종 목적지가 아니더라도 통과시킬 수 있게 합니다.
    source_dest_check = false

    # 초기화 자동화 (User Data)
    user_data = <<-EOF
                #!/bin/bash
                hostnamectl set-hostname aws-t4g-node
                dnf update -y
                curl -fsSL https://tailscale.com/install.sh | sh
                tailscale up --authkey ${var.tailscale_auth_key} --hostname aws-t4g-node --accept-dns=false --accept-routes=false
                EOF

    tags = {
        Name = "aws-t4g-node"
    }
}

# 최종 출력
output "public_ip" {
    value = aws_instance.aws_t4g_node.public_ip
}