@echo off
chcp 65001 >nul
title Assistente WIN - Execution Harness (Modo Copiloto)
cd /d "C:\Users\glaci\Projetos\mini-indice-B3"

echo ===============================================================================
echo     INICIANDO EXECUTION HARNESS - MODO COPILOTO / ASSISTIDO (WIN B3)
echo ===============================================================================
echo.
python run_harness_copilot.py --mode COPILOT

pause
