@echo off
REM ============================================================
REM  1-instalar.bat  -  rode UMA VEZ, com duplo-clique
REM  Cria um ambiente Python isolado e instala as dependencias.
REM ============================================================
cd /d "%~dp0"
chcp 65001 >nul

echo.
echo ============================================
echo  Monitor de Tarifas - Instalacao
echo ============================================
echo.

REM --- Python instalado? ---
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado.
    echo.
    echo Baixe em https://www.python.org/downloads/
    echo IMPORTANTE: marque "Add Python to PATH" durante a instalacao.
    echo.
    pause
    exit /b 1
)
for /f "delims=" %%v in ('python --version') do echo Python encontrado: %%v

REM --- Ambiente isolado (.venv): evita conflito com outros programas ---
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo Criando ambiente isolado .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERRO] Falha ao criar o ambiente virtual.
        pause
        exit /b 1
    )
)

echo.
echo Instalando dependencias ^(pode demorar alguns minutos^) ...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao instalar as dependencias.
    pause
    exit /b 1
)

REM --- .env: criado a partir do exemplo se ainda nao existir ---
if not exist ".env" (
    echo.
    echo Criando arquivo .env a partir do modelo ...
    copy /y ".env.example" ".env" >nul
    echo.
    echo ATENCAO: falta preencher o .env com a senha de e-mail.
    echo Vou abrir o arquivo no Bloco de Notas.
    echo Procure a linha SMTP_PASSWORD e coloque a Senha de App do Gmail.
    echo.
    pause
    notepad .env
)

echo.
echo ============================================
echo  Instalacao concluida.
echo  Proximo passo: duplo-clique em 2-testar.bat
echo ============================================
echo.
pause
