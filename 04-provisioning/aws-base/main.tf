provider "aws" {
    region = local.region
}

resource "aws_key_pair" "shared_key" {
    key_name   = "hybrid-cloud-shared-key"
    public_key = file("${local.public_key_path}")
}