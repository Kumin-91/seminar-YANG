# SSH 키 페어 등록
resource "aws_key_pair" "hybrid_cloud" {
    key_name   = "hybrid-cloud-key-${local.node_name}"
    public_key = var.PUBLIC_KEY
}

# EC2 인스턴스 (t4g.medium)
resource "aws_instance" "node" {
    ami           = "ami-055751883cc1be227"
    instance_type = local.instance_type
    key_name      = aws_key_pair.hybrid_cloud.key_name
    vpc_security_group_ids = [aws_security_group.hybrid_cloud_sg.id]
    associate_public_ip_address = local.associate_ip

    root_block_device {
        volume_size = local.ebs_size
        volume_type = "gp3"
    }

    # 인스턴스가 패킷의 최종 목적지가 아니더라도 통과시킬 수 있게 합니다.
    source_dest_check = false

    # user_data를 외부 파일로 분리하여 호출합니다. 
    user_data = templatefile("tailscale_setup.tftpl", {
        node_name             = local.node_name
        tailscale_auth_key    = var.TAILSCALE_AUTH_KEY
    })

    tags = {
        Name = local.node_name
    }
}
