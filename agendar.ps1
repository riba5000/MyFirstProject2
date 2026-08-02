# Registra (ou atualiza) a tarefa diaria no Agendador de Tarefas do Windows.
# Chamado por 3-agendar.bat - nao precisa rodar isto direto.

param(
    [string]$Hora = "08:00",
    [string]$Nome = "MonitorTarifasAsia",
    [switch]$Remover
)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $MyInvocation.MyCommand.Path

if ($Remover) {
    Unregister-ScheduledTask -TaskName $Nome -Confirm:$false
    Write-Host "Tarefa '$Nome' removida." -ForegroundColor Yellow
    exit 0
}

# pythonw.exe roda sem abrir janela preta todo dia; o registro vai para logs\monitor.log
$python = Join-Path $raiz ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $python)) {
    Write-Host "[ERRO] Ambiente nao encontrado. Rode 1-instalar.bat primeiro." -ForegroundColor Red
    exit 1
}

$acao = New-ScheduledTaskAction -Execute $python -Argument "main.py" -WorkingDirectory $raiz
$gatilho = New-ScheduledTaskTrigger -Daily -At $Hora

# StartWhenAvailable: se o PC estava desligado no horario, roda assim que ligar.
# As opcoes de bateria evitam que o notebook pule a execucao fora da tomada.
$opcoes = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $Nome `
    -Action $acao -Trigger $gatilho -Settings $opcoes `
    -Description "Monitor de tarifas FLN -> Sudeste Asiatico (rodada diaria)" `
    -Force | Out-Null

Write-Host ""
Write-Host "Tarefa '$Nome' agendada para todo dia as $Hora." -ForegroundColor Green
Write-Host "Se o PC estiver desligado no horario, roda assim que ligar."
Write-Host ""
Write-Host "Ver no Windows:  Agendador de Tarefas > Biblioteca do Agendador"
Write-Host "Testar agora:    Start-ScheduledTask -TaskName $Nome"
Write-Host "Remover:         powershell -ExecutionPolicy Bypass -File agendar.ps1 -Remover"
