output "region"    { value = local.region }
output "vpc_id"    { value = aws_vpc.main.id }
output "sg_id"     { value = aws_security_group.common-sg.id }
output "key_name"  { value = aws_key_pair.shared_key.key_name }
output "subnet_id" { value = aws_subnet.public.id }