provider "aws" {
  region = "us-east-1"  # cambia según tu región
}

resource "aws_instance" "flask_server" {
  ami           = "ami-0c02fb55956c7d316"  # ejemplo Ubuntu 22.04 en us-east-1
  instance_type = "t2.micro"
  #key_name      = "mi-key-aws"            # tu key pair en AWS

  user_data = <<-EOF
              #!/bin/bash
              apt update -y
              apt install python3-pip -y
              pip3 install Flask==2.3.2
              cat <<EOT >> /home/ubuntu/app.py
              from flask import Flask
              app = Flask(__name__)
              @app.route("/")
              def hello():
                  return "Hola Mundo desde Flask en EC2!"
              if __name__ == "__main__":
                  app.run(host="0.0.0.0", port=80)
              EOT
              nohup python3 /home/ubuntu/app.py &
              EOF

  tags = {
    Name = "FlaskServer"
  }

  # Seguridad: permitir puerto 80
  vpc_security_group_ids = [aws_security_group.flask_sg.id]
}

resource "aws_security_group" "flask_sg" {
  name        = "flask_sg"
  description = "Allow HTTP"
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
