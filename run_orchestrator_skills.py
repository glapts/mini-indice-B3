"""
run_orchestrator_skills.py
Serviço Daemon do Orquestrador de Agentes com 3 Skills (Terminal 1).
Roda em segundo plano, consolida os pareceres dos 3 agentes especialistas
(Macro, Cesta/DI e Sentinela) e dos contratos JSON das 3 Skills,
atualizando 'data/runtime_state.json' a cada ciclo.

Modo operacional: COPILOT (apenas alertas, sem ordem automática).
"""

import os
import sys
import time
import argparse
from datetime import datetime

# Garante path do projeto
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, base_dir)

from core.agents.orchestrator_skills import OrchestratorWithSkills
from core.harness.contracts import ExecutionMode


def main():
    parser = argparse.ArgumentParser(description="Daemon do Orquestrador de Agentes com Skills")
    parser.add_argument("--interval", type=int, default=10, help="Intervalo em segundos entre ciclos (padrão: 10s)")
    parser.add_argument("--mode", type=str, choices=["COPILOT", "FULL_AUTO"], default="COPILOT", help="Modo operacional")
    args = parser.parse_args()

    print("=" * 80)
    print("🧠 ORQUESTRADOR DE AGENTES COM SKILLS (TERMINAL 1)")
    print("=" * 80)
    print(" Agentes Ativos:")
    print("   1. Macro & Global (S&P 500, Treasuries, DXY, Calendário EUA)")
    print("   2. Cesta IBOV & Arbitragem (PETR4, VALE3, Bancos, Curva DI)")
    print("   3. Sentinela Político (Notícias de Brasília, Risco Fiscal, Black Swan)")
    print(" Skills Ativas:")
    print("   S1. macro-global-guard   (BLOCK / VETO_COMPRA / VETO_VENDA / ALLOW)")
    print("   S2. cesta-juros-veto     (VETO_COMPRA / VETO_VENDA / BLOCK / ALLOW)")
    print("   S3. sentinela-politico-emergencia (EMERGENCY_HALT / ALLOW)")
    print(f" Destino de Estado : data/runtime_state.json")
    print(f" Intervalo do Loop : {args.interval}s")
    print(f" Modo Configurado  : {args.mode}")
    print("=" * 80)

    orchestrator = OrchestratorWithSkills(
        execution_mode=ExecutionMode(args.mode.upper())
    )

    cycle_count = 0
    try:
        while True:
            cycle_count += 1
            now = datetime.now()

            state = orchestrator.run_cycle(current_time=now)

            status_symbol = "🟢 OPERAÇÃO LIBERADA" if state.trading_enabled else "🔴 OPERAÇÃO BLOQUEADA"
            opinion_summary = f"Dir: {state.allowed_direction.value} | Confiança: {state.confidence_score*100:.0f}%"
            print(f"[{now.strftime('%H:%M:%S')}] Ciclo #{cycle_count:04d} | {status_symbol} | {opinion_summary}")
            if not state.trading_enabled:
                print("   -> Motivo do Bloqueio: operação desabilitada pelos guardrails (Agentes + Skills).")

            # Exibe contratos das skills a cada ciclo para auditoria
            contracts = orchestrator.get_skill_contracts()
            for skill_name, c in contracts.items():
                if c["status"] != "ALLOW":
                    print(f"   [{skill_name}] {c['status']}: {c['motivo']}")

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n[ORQUESTRADOR] Encerrando serviço a pedido do operador.")


if __name__ == "__main__":
    main()
