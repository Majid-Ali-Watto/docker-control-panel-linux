"""
Docker commands help text
"""

commands_info = """
DOCKER COMMANDS:

docker ps
  List running containers

docker ps -a
  List all containers (including stopped)

docker start <container>
  Start a stopped container

docker stop <container>
  Stop a running container

docker restart <container>
  Restart a container

docker rm <container>
  Remove a container

docker images
  List all images

docker pull <image>
  Pull an image from Docker Hub

docker rmi <image>
  Remove an image

docker volume ls
  List all volumes

docker volume prune
  Remove unused volumes

docker stats
  Show container resource usage

docker system df
  Show disk usage

systemctl start docker
  Start Docker service

systemctl stop docker
  Stop Docker service

systemctl restart docker
  Restart Docker service
"""
