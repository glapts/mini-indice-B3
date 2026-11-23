@echo off
chcp 65001 > nul
cls
echo ======================================================================
echo   BACKTEST COM DADOS HISTORICOS REAIS B3 (JANEIRO A NOVEMBRO)
echo   Algoritmo SMC & Tape Reading Institucional
echo ======================================================================
echo.

cd /d "C:\Users\glaci\Projetos\mini-indice-B3"

echo 1. Verificando arquivos CSV na pasta data\historico...
python check_real_data.py
echo.

set /p RESP="Deseja iniciar o processamento completo agora? (S/N): "
if /i "%RESP%"=="S" (
    echo.
    echo Iniciando Replay e Auditoria Quantitativa...
    python batch_backtest.py --dir "data\historico" --mode FIXO
) else (
    echo Operacao cancelada.
)

pause
