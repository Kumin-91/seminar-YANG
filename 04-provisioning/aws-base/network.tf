# 1. VPC & Gateway
resource "aws_vpc" "main" {
  cidr_block = local.vpc_cidr
  tags       = { Name = "hybrid-cloud-vpc" }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "hybrid-cloud-igw" }
}

# 2. Subnet
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = local.public_subnet_cidr
  map_public_ip_on_launch = true
  tags                    = { Name = "hybrid-cloud-public-subnet" }
}

# 3. Routing
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
  tags = { Name = "hybrid-cloud-public-rt" }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id # [cite: 75]
}

# 4. Security
resource "aws_security_group" "common-sg" {
    name        = "hybrid-cloud-sg"
    description = "Allow SSH and Tailscale traffic" 
    vpc_id      = aws_vpc.main.id

    # SSH Access
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

    tags = { Name = "hybrid-cloud-sg" }
}