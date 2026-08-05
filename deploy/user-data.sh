#!/bin/bash
# EC2 user data for Amazon Linux 2023. Paste into "Advanced details > User data"
# when launching the instance. Installs Docker, adds swap, clones the repo.
# It deliberately does NOT start the stack — .env has to be filled in first.
set -euxo pipefail

dnf update -y
dnf install -y docker git

systemctl enable --now docker
usermod -aG docker ec2-user

# Compose v2 as a CLI plugin (not packaged in AL2023).
ARCH="$(uname -m)"
DOCKER_CONFIG=/usr/local/lib/docker
mkdir -p "${DOCKER_CONFIG}/cli-plugins"
curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-${ARCH}" \
    -o "${DOCKER_CONFIG}/cli-plugins/docker-compose"
chmod +x "${DOCKER_CONFIG}/cli-plugins/docker-compose"

# t3.micro has 1 GB of RAM. The npm/vite build and Postgres both want more
# headroom than that, and the build OOMs without swap.
if [ ! -f /swapfile ]; then
    dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >>/etc/fstab
fi

sudo -u ec2-user git clone \
    https://github.com/aayushhks/llm-eval-with-probes.git \
    /home/ec2-user/llm-eval-with-probes || true

echo "bootstrap done — ssh in, fill .env, then docker compose up"
