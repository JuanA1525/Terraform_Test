provider "aws" {
  region = "us-east-1"  # cambia según tu región
}

resource "aws_instance" "flask_server" {
  ami           = "ami-0c398cb65a93047f2"  # ejemplo Ubuntu 22.04 en us-east-1
  instance_type = "t2.micro"
  key_name = "IoT_Key"

  associate_public_ip_address = true

  user_data = <<-EOF
              #!/bin/bash
              set -e

              # Variables
              REPO_URL="https://github.com/JuanA1525/Terraform_Test"
              APP_DIR="/home/ubuntu/Terraform_Test"

              apt update -y
              apt install -y python3-pip git

              # Clonar el repo (si ya existe, hacer pull)
              if [ ! -d "$APP_DIR" ]; then
                git clone "$REPO_URL" "$APP_DIR"
                chown -R ubuntu:ubuntu "$APP_DIR"
              else
                cd "$APP_DIR"
                git pull
              fi

              cd "$APP_DIR"

              # Instalar requirements si existe requirements.txt
              if [ -f "requirements.txt" ]; then
                pip3 install -r requirements.txt
              else
                # fallback: asegurar Flask disponible
                pip3 install Flask==2.3.2
              fi

              # Ejecutar la app (suponer app.py en la raíz del repo)
              # Ejecutar como usuario ubuntu y redirigir logs
              nohup sudo -u ubuntu python3 "$APP_DIR/app.py" > /var/log/flask_app.log 2>&1 &
              EOF

  tags = {
    Name = "FlaskServer"
  }

  vpc_security_group_ids = [aws_security_group.flask_sg.id]
}

resource "aws_security_group" "flask_sg" {
  name        = "flask_sg"
  description = "Allow HTTP and SSH"

  # HTTP de tu app (5000)
  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # SSH (22) — idealmente restrínge a tu IP pública con /32
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # reemplaza por tu IP/32 para mayor seguridad
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Salida conveniente con la IP pública
output "ec2_public_ip" {
  value = aws_instance.flask_server.public_ip
}
