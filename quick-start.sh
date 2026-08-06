#!/bin/bash

# 🚀 NEGÃO AI — Quick Start Script
# Automatiza a inicialização do projeto

set -e

echo "╔════════════════════════════════════════════════════════╗"
echo "║         🤖 NEGÃO AI - Quick Start                     ║"
echo "╚════════════════════════════════════════════════════════╝"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funções
check_command() {
  if command -v $1 &> /dev/null; then
    echo -e "${GREEN}✓${NC} $1 encontrado"
    return 0
  else
    echo -e "${RED}✗${NC} $1 não encontrado"
    return 1
  fi
}

print_section() {
  echo -e "\n${BLUE}▶ $1${NC}"
}

# ============================================================================
# STEP 1: Verificar Dependências
# ============================================================================
print_section "STEP 1: Verificando dependências"

check_command "node" || echo -e "${YELLOW}⚠${NC} Node.js necessário para o frontend"
check_command "python" || echo -e "${YELLOW}⚠${NC} Python 3.13+ necessário para o backend"
check_command "docker" && DOCKER_AVAILABLE=1 || DOCKER_AVAILABLE=0
check_command "docker-compose" && DOCKER_COMPOSE_AVAILABLE=1 || DOCKER_COMPOSE_AVAILABLE=0

# ============================================================================
# STEP 2: Criar .env se não existir
# ============================================================================
print_section "STEP 2: Configurando variáveis de ambiente"

if [ ! -f ".env" ]; then
  echo -e "${YELLOW}⚠${NC} Arquivo .env não encontrado. Criando a partir de .env.example..."
  if [ -f ".env.example" ]; then
    cp .env.example .env
    echo -e "${GREEN}✓${NC} .env criado"
  else
    echo -e "${RED}✗${NC} .env.example não encontrado!"
    exit 1
  fi
else
  echo -e "${GREEN}✓${NC} .env já existe"
fi

if [ ! -f "frontend/.env.local" ]; then
  echo -e "${YELLOW}⚠${NC} Arquivo frontend/.env.local não encontrado. Criando..."
  cat > frontend/.env.local << 'EOF'
NEXT_PUBLIC_API_URL=http://localhost:8000
NEGAO_API_URL=http://localhost:8000
NEGAO_API_KEY=REDACTED
EOF
  echo -e "${GREEN}✓${NC} frontend/.env.local criado"
else
  echo -e "${GREEN}✓${NC} frontend/.env.local já existe"
fi

# ============================================================================
# STEP 3: Iniciar Docker Compose (se disponível)
# ============================================================================
print_section "STEP 3: Iniciando serviços de infraestrutura"

if [ $DOCKER_COMPOSE_AVAILABLE -eq 1 ]; then
  echo -e "${BLUE}→${NC} Iniciando Docker Compose..."
  docker compose up -d
  echo -e "${GREEN}✓${NC} Docker Compose iniciado"
  
  echo -e "${BLUE}→${NC} Aguardando PostgreSQL e Redis ficarem prontos..."
  sleep 5
  
  # Verificar conexão DB
  until docker compose exec -T db pg_isready -U negao &> /dev/null; do
    echo "  ⏳ PostgreSQL não está pronto..."
    sleep 2
  done
  echo -e "${GREEN}✓${NC} PostgreSQL pronto"
  
  # Verificar Redis
  until docker compose exec -T redis redis-cli ping &> /dev/null; do
    echo "  ⏳ Redis não está pronto..."
    sleep 2
  done
  echo -e "${GREEN}✓${NC} Redis pronto"
else
  echo -e "${YELLOW}⚠${NC} Docker Compose não disponível"
  echo "   Certifique-se de que PostgreSQL e Redis estão rodando localmente"
fi

# ============================================================================
# STEP 4: Instalar dependências do Backend
# ============================================================================
print_section "STEP 4: Instalando dependências do Backend"

if check_command "python"; then
  cd backend
  
  if [ ! -d "venv" ]; then
    echo -e "${BLUE}→${NC} Criando ambiente virtual..."
    python -m venv venv
    source venv/bin/activate 2>/dev/null || . venv/Scripts/activate
    echo -e "${GREEN}✓${NC} Ambiente virtual criado"
  else
    source venv/bin/activate 2>/dev/null || . venv/Scripts/activate
    echo -e "${GREEN}✓${NC} Ambiente virtual ativado"
  fi
  
  echo -e "${BLUE}→${NC} Instalando pacotes Python..."
  pip install -q -e .
  echo -e "${GREEN}✓${NC} Backend dependências instaladas"
  
  cd ..
else
  echo -e "${RED}✗${NC} Python não encontrado. Pulando backend setup."
fi

# ============================================================================
# STEP 5: Instalar dependências do Frontend
# ============================================================================
print_section "STEP 5: Instalando dependências do Frontend"

if check_command "npm"; then
  cd frontend
  
  if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}→${NC} Instalando pacotes Node..."
    npm install --silent
    echo -e "${GREEN}✓${NC} Frontend dependências instaladas"
  else
    echo -e "${GREEN}✓${NC} node_modules já existe"
  fi
  
  cd ..
else
  echo -e "${RED}✗${NC} npm não encontrado. Pulando frontend setup."
fi

# ============================================================================
# STEP 6: Mostrar instruções de inicialização
# ============================================================================
print_section "STEP 6: Próximos passos"

echo -e "${BLUE}→ TERMINAL 1: Iniciar Backend${NC}"
echo "  cd backend"
echo "  source venv/bin/activate  # ou: venv\Scripts\activate (Windows)"
echo "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""

echo -e "${BLUE}→ TERMINAL 2: Iniciar Frontend${NC}"
echo "  cd frontend"
echo "  npm run dev"
echo ""

echo -e "${BLUE}→ TERMINAL 3 (Opcional): Monitor de logs${NC}"
echo "  docker compose logs -f"
echo ""

echo -e "${GREEN}✓${NC} Setup concluído!"
echo ""

echo "╔════════════════════════════════════════════════════════╗"
echo "║     ⚠️  NÃO ESQUEÇA DE ADICIONAR NVIDIA API KEY!       ║"
echo "║  1. Vá a: https://build.nvidia.com                   ║"
echo "║  2. Crie uma conta e gere API Key                    ║"
echo "║  3. Adicione em .env:                                ║"
echo "║     NEGAO_NVIDIA_API_KEY=sua-chave-aqui            ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

echo "URLs de acesso:"
echo "  Frontend: http://localhost:3000"
echo "  Backend API: http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""

echo -e "${GREEN}🚀 NEGÃO PRONTO PARA ACORDAR!${NC}"
