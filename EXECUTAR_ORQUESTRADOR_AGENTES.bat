@echo off
chcp 65001 >nul
title Comite Multi-Agente e Orquestrador (WIN B3)
cd /d "C:\Users\glaci\Projetos\mini-indice-B3"

echo ===============================================================================
echo     INICIANDO COMITE MULTI-AGENTE E ORQUESTRADOR DE MESA (WIN B3)
echo ===============================================================================
echo.
python run_orchestrator.py --interval 10 --mode COPILOT

pause
