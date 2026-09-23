#!/bin/bash

# Sophie local setup

set -e

echo "Sophie local setup"

check_command() {
  if command -v "$1" &> /dev/null; then
    echo "[OK] $1 encontrado"
    return 0
  else
    echo "[ERROR] $1 não encontrado"
    return 1
  fi
}

print_section() {
  echo
  echo "$1"
}

print_section "1. Verificando dependências"

check_command "node" || echo "[WARN] Node.js é necessário para o frontend"
check_command "python" || echo "[WARN] Python 3.13+ é necessário para o backend"
if check_command "docker" && docker compose version >/dev/null 2>&1; then
  DOCKER_COMPOSE_AVAILABLE=1
  echo "[OK] Docker Compose plugin encontrado"
else
  DOCKER_COMPOSE_AVAILABLE=0
  echo "[WARN] Docker Compose plugin não disponível"
fi

print_section "2. Configurando variáveis de ambiente"

if [ ! -f ".env" ]; then
  echo "[WARN] Arquivo .env não encontrado. Criando a partir de .env.example..."
  if [ -f ".env.example" ]; then
    cp .env.example .env
    chmod 600 .env
    echo "[OK] .env criado com permissão 0600"
  else
    echo "[ERROR] .env.example não encontrado"
    exit 1
  fi
else
  echo "[OK] .env já existe"
fi

if [ ! -f "frontend/.env.local" ]; then
  echo "[WARN] Arquivo frontend/.env.local não encontrado. Criando..."
  cat > frontend/.env.local << 'EOF'
NEGAO_API_URL=http://localhost:8000
EOF
  echo "[OK] frontend/.env.local criado"
else
  echo "[OK] frontend/.env.local já existe"
fi

print_section "3. Iniciando serviços de infraestrutura"

if [ $DOCKER_COMPOSE_AVAILABLE -eq 1 ]; then
  echo "Iniciando Docker Compose..."
  docker compose -f infra/docker/compose/dev.yml up -d
  echo "[OK] Docker Compose iniciado"
  
  echo "Aguardando PostgreSQL e Redis..."
  sleep 5
  
  until docker compose -f infra/docker/compose/dev.yml exec -T db pg_isready -U negao &> /dev/null; do
    echo "   PostgreSQL não está pronto..."
    sleep 2
  done
  echo "[OK] PostgreSQL pronto"
  
  until docker compose -f infra/docker/compose/dev.yml exec -T redis sh -ec 'redis-cli --no-auth-warning -a "$REDIS_PASSWORD" ping | grep -q PONG' &> /dev/null; do
    echo "   Redis não está pronto..."
    sleep 2
  done
  echo "[OK] Redis pronto"
else
  echo "[WARN] Docker Compose não disponível"
  echo "   Certifique-se de que PostgreSQL e Redis estão rodando localmente"
fi

print_section "4. Instalando dependências do backend"

if check_command "python"; then
  cd backend
  
  if [ ! -d "venv" ]; then
    echo "Criando ambiente virtual..."
    python -m venv venv
    source venv/bin/activate 2>/dev/null || . venv/Scripts/activate
    echo "[OK] Ambiente virtual criado"
  else
    source venv/bin/activate 2>/dev/null || . venv/Scripts/activate
    echo "[OK] Ambiente virtual ativado"
  fi
  
  echo "Instalando pacotes Python..."
  pip install -q -e .
  echo "[OK] Dependências do backend instaladas"
  
  cd ..
else
  echo "[ERROR] Python não encontrado. Etapa do backend ignorada."
fi

print_section "5. Instalando dependências do frontend"

if check_command "npm"; then
  cd frontend
  
  if [ ! -d "node_modules" ]; then
    echo "Instalando pacotes Node..."
    npm ci --silent
    echo "[OK] Dependências do frontend instaladas"
  else
    echo "[OK] node_modules já existe"
  fi
  
  cd ..
else
  echo "[ERROR] npm não encontrado. Etapa do frontend ignorada."
fi

print_section "6. Próximos passos"

echo "Terminal 1: iniciar backend"
echo "  cd backend"
echo "  source venv/bin/activate  # ou: venv\Scripts\activate (Windows)"
echo "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""

echo "Terminal 2: iniciar frontend"
echo "  cd frontend"
echo "  npm run dev"
echo ""

echo "Terminal 3 (opcional): monitorar logs"
echo "  docker compose logs -f"
echo ""

echo "Setup concluído."
echo ""

echo "IA externa é opcional e permanece desativada por padrão."
echo "Para ativar conscientemente o envio a um provedor externo:"
echo "1. Defina NEGAO_EXTERNAL_AI_ENABLED=true."
echo "2. Configure NEGAO_NVIDIA_API_KEY no .env."
echo ""

echo "URLs de acesso:"
echo "  Frontend: http://localhost:3000"
echo "  Backend API: http://localhost:8000"
echo "  API Docs: http://localhost:8000/api/v1/docs"
echo ""

echo "Setup local concluído."
