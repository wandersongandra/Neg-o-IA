@echo off
REM Sophie local setup for Windows

setlocal enabledelayedexpansion

echo.
echo Sophie local setup
echo.

echo [1] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python não encontrado.
    echo  Baixe em: https://www.python.org/downloads/
    pause
    exit /b 1
) else (
    echo [OK] Python encontrado
)

echo [2] Verificando Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js não encontrado.
    echo  Baixe em: https://nodejs.org/
    pause
    exit /b 1
) else (
    echo [OK] Node.js encontrado
)

echo [3] Preparando backend...
cd /d "%~dp0backend"

if not exist "venv" (
    echo Criando ambiente virtual...
    python -m venv venv
    echo [OK] Ambiente virtual criado
) else (
    echo [OK] Ambiente virtual já existe
)

echo [4] Instalando dependências do backend...
call venv\Scripts\activate.bat
pip install -q -e . 2>nul
if errorlevel 1 (
    echo [ERROR] Erro ao instalar dependências.
    echo  Tente: pip install -e .
    pause
    exit /b 1
) else (
    echo [OK] Dependências do backend instaladas
)

cd /d "%~dp0"

echo [5] Instalando dependências do frontend...
cd /d "%~dp0frontend"

if not exist "node_modules" (
    echo Instalando pacotes...
    call npm install --silent
    if errorlevel 1 (
        echo [ERROR] Erro ao instalar pacotes.
        pause
        exit /b 1
    ) else (
        echo [OK] Dependências do frontend instaladas
    )
) else (
    echo [OK] node_modules já existe
)

cd /d "%~dp0"

echo [6] Instruções de inicialização
echo.
echo Pré-requisitos:
echo  Python 3.13+
echo  Node.js 18+
echo  PostgreSQL rodando em localhost:5432
echo  Redis rodando em localhost:6379
echo  NVIDIA API Key configurada em .env
echo.
echo Instruções de inicialização:
echo.
echo 1. Abra o terminal do backend:
echo    cd backend
echo    venv\Scripts\activate
echo    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
echo.
echo 2. Abra o terminal do frontend:
echo    cd frontend
echo    npm run dev
echo.
echo 3. Abra no navegador:
echo    http://localhost:3000
echo.
echo Verificações:
echo  API Status:  http://localhost:8000/health
echo  API Docs:    http://localhost:8000/docs
echo  Brain:       http://localhost:8000/api/v1/brain/status
echo.
echo Setup concluído. Pressione qualquer tecla para fechar.
echo.

pause
