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

# AL2023 ships buildx 0.12, but current Compose needs >= 0.17 and fails the
# build with "compose build requires buildx 0.17.0 or later". The release asset
# carries its version in the filename, so the tag has to be looked up first.
case "${ARCH}" in
    x86_64) BUILDX_ARCH=amd64 ;;
    aarch64) BUILDX_ARCH=arm64 ;;
    *) BUILDX_ARCH="${ARCH}" ;;
esac
BUILDX_VER="$(curl -fsSL https://api.github.com/repos/docker/buildx/releases/latest |
    grep -oP '"tag_name":\s*"\K[^"]+')"
curl -fsSL "https://github.com/docker/buildx/releases/download/${BUILDX_VER}/buildx-${BUILDX_VER}.linux-${BUILDX_ARCH}" \
    -o "${DOCKER_CONFIG}/cli-plugins/docker-buildx"
chmod +x "${DOCKER_CONFIG}/cli-plugins/docker-buildx"

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
