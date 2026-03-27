# 보안 그룹 설정 (SSH & Tailscale)
resource "aws_security_group" "hybrid_cloud_sg" {
    name        = "hybrid-cloud-sg-${local.node_name}"
    description = "Allow SSH and Tailscale traffic" 

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