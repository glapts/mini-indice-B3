# testar_hoje_replay.ps1
# Teste válido para hoje (22/11/2026) sem precisar do mercado real ou do Profit Pro conectado.
# Usa o ReplayMarketFeed determinístico do próprio projeto para validar o motor SMC,
# os 9 setups e a geração de alertas em COPILOT.
#
# Uso:
#   cd "C:\Users\glaci\Projetos\mini-indice-B3"
#   .\testar_hoje_replay.ps1

$projeto = "C:\Users\glaci\Projetos\mini-indice-B3"

if (-not (Test-Path $projeto)) {
    Write-Error "Pasta do projeto não encontrada: $projeto"
    exit 1
}

Set-Location $projeto

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  TESTE VÁLIDO PARA HOJE - REPLAY DETERMINÍSTICO " -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Projeto   : $projeto" -ForegroundColor Gray
Write-Host "Fonte     : ReplayMarketFeed (dados sintéticos determinísticos)" -ForegroundColor Gray
Write-Host "Objetivo  : Validar motor SMC, setups e alertas sem mercado real" -ForegroundColor Gray
Write-Host ""

$env:PYTHONIOENCODING="utf-8"

Write-Host "[1/2] Executando teste determinístico de replay..." -ForegroundColor Green
python main.py test-replay --mode FIXO

$exitCode = $LASTEXITCODE

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "[OK] Teste de replay concluído com sucesso." -ForegroundColor Green
} else {
    Write-Error "O teste de replay falhou com código de saída $exitCode."
    exit $exitCode
}

Write-Host ""
Write-Host "[2/2] Validando testes unitários..." -ForegroundColor Green
python -m unittest discover -s tests -p "test_*.py"

$exitCode2 = $LASTEXITCODE

Write-Host ""
if ($exitCode2 -eq 0) {
    Write-Host "[OK] Testes unitários concluídos com sucesso." -ForegroundColor Green
} else {
    Write-Error "Os testes unitários falharam com código de saída $exitCode2."
    exit $exitCode2
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  TESTE DE HOJE CONCLUÍDO COM SUCESSO           " -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "O motor está validado. Para amanhã, use:" -ForegroundColor Gray
Write-Host "  .\iniciar_copiloto.ps1" -ForegroundColor Yellow
Write-Host ""
