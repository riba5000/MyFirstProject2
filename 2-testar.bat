@echo off
REM ============================================================
REM  2-testar.bat  -  roda UMA busca e mostra o resultado na tela
REM  NAO envia e-mail. Use para conferir se os precos fazem sentido.
REM ============================================================
cd /d "%~dp0"
chcp 65001 >nul

if not exist ".venv\Scripts\python.exe" (
    echo [ERRO] Ambiente nao encontrado. Rode 1-instalar.bat primeiro.
    pause
    exit /b 1
)

echo.
echo Rodando uma coleta de teste ^(sem enviar e-mail^) ...
echo Isso pode levar alguns minutos. Aguarde.
echo.

".venv\Scripts\python.exe" main.py --dry-run

echo.
echo ============================================
echo  Fim do teste.
echo.
echo  CONFIRA DUAS COISAS acima:
echo   1^) Os precos por pax fazem sentido em reais?
echo   2^) Apareceu algum aviso com a palavra "moeda"?
echo.
echo  O log completo fica em: logs\monitor.log
echo ============================================
echo.
pause
