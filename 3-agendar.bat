@echo off
REM ============================================================
REM  3-agendar.bat  -  agenda a rodada diaria no Windows
REM  Depois disso o monitor roda sozinho e manda o e-mail.
REM ============================================================
cd /d "%~dp0"
chcp 65001 >nul

echo.
echo ============================================
echo  Agendar rodada diaria
echo ============================================
echo.
echo ANTES DE CONTINUAR: o e-mail so funciona se o .env
echo estiver com a Senha de App do Gmail em SMTP_PASSWORD.
echo.

set "HORA=08:00"
set /p HORA=Horario da rodada diaria [08:00]:

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0agendar.ps1" -Hora "%HORA%"
if errorlevel 1 (
    echo.
    echo [ERRO] Nao foi possivel agendar.
    pause
    exit /b 1
)

echo.
pause
