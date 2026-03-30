# EC2 인스턴스
resource "aws_instance" "node" {
    ami                         = data.aws_ami.selected.id
    instance_type               = local.instance_type
    key_name                    = local.key_name
    vpc_security_group_ids      = [local.sg_id]
    subnet_id                   = local.subnet_id
    associate_public_ip_address = local.associate_ip

    root_block_device {
        volume_size = local.ebs_size
        volume_type = "gp3"
        delete_on_termination = true
    }

    # 인스턴스가 패킷의 최종 목적지가 아니더라도 통과시킬 수 있게 합니다.
    source_dest_check = false

    tags = {
        Name = local.node_name
        Architecture = local.arch
    }
}
