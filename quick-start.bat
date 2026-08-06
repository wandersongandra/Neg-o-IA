@echo off
REM 🚀 NEGÃO AI - Quick Start (Windows)

setlocal enabledelayedexpansion

echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║         🤖 NEGÃO AI - Quick Start (Windows)           ║
echo ║              Acordando a IA...                        ║
echo ╚════════════════════════════════════════════════════════╝
echo.

REM ============================================================================
REM STEP 1: Verificar Python
REM ============================================================================
echo [STEP 1] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ✗ Python não encontrado!
    echo  Baixe em: https://www.python.org/downloads/
    pause
    exit /b 1
) else (
    echo ✓ Python encontrado
)

REM ============================================================================
REM STEP 2: Verificar Node.js
REM ============================================================================
echo [STEP 2] Verificando Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo ✗ Node.js não encontrado!
    echo  Baixe em: https://nodejs.org/
    pause
    exit /b 1
) else (
    echo ✓ Node.js encontrado
)

REM ============================================================================
REM STEP 3: Criar venv do backend
REM ============================================================================
echo [STEP 3] Preparando Backend...
cd /d "%~dp0backend"

if not exist "venv" (
    echo  Criando ambiente virtual...
    python -m venv venv
    echo ✓ Ambiente virtual criado
) else (
    echo ✓ Ambiente virtual já existe
)

REM ============================================================================
REM STEP 4: Instalar dependências do Backend
REM ============================================================================
echo [STEP 4] Instalando dependências do Backend...
call venv\Scripts\activate.bat
pip install -q -e . 2>nul
if errorlevel 1 (
    echo ✗ Erro ao instalar dependências
    echo  Tente: pip install -e .
    pause
    exit /b 1
) else (
    echo ✓ Backend dependências instaladas
)

cd /d "%~dp0"

REM ============================================================================
REM STEP 5: Instalar dependências do Frontend
REM ============================================================================
echo [STEP 5] Instalando dependências do Frontend...
cd /d "%~dp0frontend"

if not exist "node_modules" (
    echo  Instalando pacotes...
    call npm install --silent
    if errorlevel 1 (
        echo ✗ Erro ao instalar pacotes
        pause
        exit /b 1
    ) else (
        echo ✓ Frontend dependências instaladas
    )
) else (
    echo ✓ node_modules já existe
)

cd /d "%~dp0"

REM ============================================================================
REM STEP 6: Instruções de inicialização
REM ============================================================================
echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║            ✅ Setup Concluído!                         ║
echo ╚════════════════════════════════════════════════════════╝
echo.
echo [PRÉ-REQUISITOS]
echo ✓ Python 3.13+
echo ✓ Node.js 18+
echo ✓ PostgreSQL rodando em localhost:5432
echo ✓ Redis rodando em localhost:6379
echo ✓ NVIDIA API Key configurada em .env
echo.
echo [INSTRUÇÕES DE INICIALIZAÇÃO]
echo.
echo 1️⃣  Abra TERMINAL 1 (Backend):
echo    cd backend
echo    venv\Scripts\activate
echo    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
echo.
echo 2️⃣  Abra TERMINAL 2 (Frontend):
echo    cd frontend
echo    npm run dev
echo.
echo 3️⃣  Abra no navegador:
echo    http://localhost:3000
echo.
echo [VERIFICAÇÕES]
echo  API Status:  http://localhost:8000/health
echo  API Docs:    http://localhost:8000/docs
echo  Brain:       http://localhost:8000/api/v1/brain/status
echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║     🚀 NEGÃO PRONTO PARA ACORDAR!                     ║
echo ║     Pressione qualquer tecla para fechar.             ║
echo ╚════════════════════════════════════════════════════════╝
echo.

pause
