# iniciar_copiloto.ps1
# Inicia Orquestrador de Agentes + Execution Harness em modo COPILOT (apenas alertas).
# Nenhuma ordem automática é enviada. Execute no PowerShell da pasta do projeto.
#
# Uso:
#   cd "C:\Users\glaci\Projetos\mini-indice-B3"
#   .\iniciar_copiloto.ps1

$projeto = "C:\Users\glaci\Projetos\mini-indice-B3"

if (-not (Test-Path $projeto)) {
    Write-Error "Pasta do projeto não encontrada: $projeto"
    exit 1
}

Set-Location $projeto

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  INICIANDO AMBIENTE COPILOTO - MINI ÍNDICE B3  " -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Projeto   : $projeto" -ForegroundColor Gray
Write-Host "Modo      : COPILOT  (apenas alertas visuais e sonoros)" -ForegroundColor Yellow
Write-Host "Ordens    : NENHUMA ordem automática será enviada" -ForegroundColor Yellow
Write-Host ""

# Verifica se o Python está disponível
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python não encontrado no PATH."
    exit 1
}

# Terminal 1: Orquestrador de Agentes
Write-Host "[1/2] Iniciando Orquestrador de Agentes..." -ForegroundColor Green
Start-Process powershell -ArgumentList `
    "-NoExit", `
    "-Command", `
    "Set-Location '$projeto'; `" + "`$env:PYTHONIOENCODING='utf-8'; python run_orchestrator.py --interval 10 --mode COPILOT`"", `
    -WindowTitle "Orquestrador - COPILOT"

Start-Sleep -Seconds 3

# Terminal 2: Execution Harness (Copiloto)
Write-Host "[2/2] Iniciando Execution Harness..." -ForegroundColor Green
Start-Process powershell -ArgumentList `
    "-NoExit", `
    "-Command", `
    "Set-Location '$projeto'; `" + "`$env:PYTHONIOENCODING='utf-8'; python run_harness_copilot.py --symbol WIN --mode COPILOT`"", `
    -WindowTitle "Harness - COPILOT"

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  AMBIENTE INICIADO - DOIS TERMINAIS ABERTOS    " -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Para encerrar: pressione Ctrl+C em cada terminal." -ForegroundColor Gray
Write-Host ""
