#!/usr/bin/env bash
# vps-setup.sh — ONE-SHOT setup via Hetzner VNC console
# Copie e cole no console VNC como root (logado via painel Hetzner)
set -euo pipefail

echo "=== NEGÃO AI — VPS First Setup ==="

# 1. Instalar Docker
if ! command -v docker &>/dev/null; then
    echo "[1/4] Instalando Docker..."
    apt-get update -qq
    apt-get install -y -qq ca-certificates curl gnupg lsb-release git >/dev/null
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /opt/docker/gpg 2>/dev/null || true
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin >/dev/null
    systemctl enable --now docker
    usermod -aG docker root
    echo "Docker instalado."
fi

# 2. Clonar repositório
WORKDIR="/opt/negao"
if [ ! -d "$WORKDIR/.git" ]; then
    echo "[2/4] Clonando repositório..."
    git clone https://github.com/complianceX/Neg-o-IA.git "$WORKDIR"
else
    echo "[2/4] Atualizando código..."
    cd "$WORKDIR" && git fetch --all --tags && git reset --hard origin/main
fi

# 3. .env
cd "$WORKDIR"
if [ ! -f .env ]; then
    echo "[3/4] Criando .env..."
    cp .env.example .env
    echo "IMPORTANTE: Edite /opt/negao/.env antes de rodar o deploy:"
    echo "  - NEGAO_NVIDIA_API_KEY (opcional, para LLM real)"
    echo "  - NEGAO_SECRET_KEY (gere: python3 -c \"import secrets; print(secrets.token_hex(32))\")"
    echo "  - NEXT_PUBLIC_VAPID_PUBLIC_KEY (gere: npx web-push generate-vapid-keys)"
    echo "Pressione ENTER após editar..."
    read
fi

# 4. Build + deploy
echo "[4/4] Build e deploy..."
docker compose -f "$COMPOSE_FILE" build --pull
docker compose -f "$COMPOSE_FILE" run --rm backend alembic upgrade head || echo "[WARN] Migration failed, continuing..."
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

echo ""
echo "=== Deploy concluído! ==="
docker compose -f "$COMPOSE_FILE" ps
echo "Acesse: http://$(hostname -I | awk '{print $1}')"
