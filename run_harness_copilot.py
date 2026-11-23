"""
run_harness_copilot.py
Execução Oficial do Execution Harness no Modo Copiloto (Assistido).
Conecta-se ao Profit Pro via DDE/RTD ou executa em modo monitoramento ativo.
Carrega os contratos:
  - data/niveis_60m.json (Zonas FVG e Dealing Range 50%)
  - data/runtime_state.json (Estado do Orquestrador e Circuit Breakers)
"""

import os
import sys
import time
import json
import argparse
from datetime import datetime

# Garante path do projeto
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, base_dir)

from core.harness.contracts import (
    ExecutionMode,
    Niveis60mContract,
    RuntimeStateContract
)
from core.harness.execution_harness import ExecutionHarness
from feeds.dde_feed import ProfitDDEFeed
from core.contract import get_current_win_contract, resolve_symbol


def load_contracts():
    niveis_path = os.path.join(base_dir, "data", "niveis_60m.json")
    state_path = os.path.join(base_dir, "data", "runtime_state.json")

    if not os.path.exists(niveis_path):
        print(f"[ERRO] Arquivo de níveis não encontrado em: {niveis_path}")
        sys.exit(1)

    if not os.path.exists(state_path):
        print(f"[ERRO] Arquivo de estado não encontrado em: {state_path}")
        sys.exit(1)

    with open(niveis_path, "r", encoding="utf-8") as f:
        niveis_data = json.load(f)
    niveis = Niveis60mContract(**niveis_data)

    with open(state_path, "r", encoding="utf-8") as f:
        state_data = json.load(f)
    state = RuntimeStateContract(**state_data)

    return niveis, state


def main():
    parser = argparse.ArgumentParser(description="Execution Harness - Modo Copiloto Assistido (WIN B3)")
    parser.add_argument("--symbol", type=str, default=None, help="Ticker do contrato (ex: WIN, WINZ26)")
    parser.add_argument("--mode", type=str, choices=["COPILOT", "FULL_AUTO"], default="COPILOT", help="Modo operacional")
    args = parser.parse_args()

    niveis, state = load_contracts()
    exec_mode = ExecutionMode(args.mode.upper())
    state.execution_mode = exec_mode

    symbol = resolve_symbol(args.symbol or niveis.ativo)

    print("=" * 80)
    print(f"🚀 INICIANDO EXECUTION HARNESS — {exec_mode.value} (MINI-ÍNDICE B3)")
    print("=" * 80)
    print(f" Ativo Monitorado   : {symbol}")
    print(f" Dealing Range 60m  : Topo {niveis.dealing_range.topo_estrutural:.0f} | Fundo {niveis.dealing_range.fundo_estrutural:.0f}")
    print(f" 50% Equilibrium    : {niveis.dealing_range.equilibrium_50:.0f} (Regra Premium & Discount Ativa)")
    print(f" Zonas Mapeadas     : {len(niveis.zonas_fvg)} zonas de FVG/iFVG")
    print(f" Circuit Breaker    : Max {state.circuit_breaker.max_daily_stops} stops diários")
    print(f" Trava de Horário   : 09:00 - 10:00 (OBSERVATION_ONLY) | 10:28 - 10:35 (NY Open)")
    print(f" Modo Operacional   : {exec_mode.value}")
    if exec_mode == ExecutionMode.COPILOT:
        print("  -> Alertas sonoros e visuais habilitados. Ordens confirmadas pelo trader.")
    else:
        print("  -> ENVIO AUTOMÁTICO DE ORDENS OCO ATIVO.")
    print("=" * 80)

    harness = ExecutionHarness(
        niveis_contract=niveis,
        runtime_state=state,
        mode=exec_mode
    )

    feed = ProfitDDEFeed()

    # Callbacks do feed
    def on_trade_event(trade):
        aggr = trade.aggressor.value if hasattr(trade.aggressor, 'value') else str(trade.aggressor)
        harness.on_trade(trade.price, trade.quantity, aggr, trade.timestamp)
        # Tick de avaliação
        harness.on_tick(trade.price, trade.timestamp)

    def on_candle_event(candle):
        harness.on_candle_closed(candle.timeframe, candle.open, candle.high, candle.low, candle.close, candle.timestamp)

    def on_book_event(snapshot):
        harness.on_book(snapshot)

    feed.set_callbacks(
        on_trade=on_trade_event,
        on_candle=on_candle_event,
        on_book=on_book_event
    )

    print(f"\n[FEED] Conectando ao Nelogica Profit Pro via DDE para {symbol}...")
    try:
        feed.connect()
        feed.subscribe_symbol(symbol)
        print("[FEED] Conexão iniciada! Monitorando fluxo institucional em tempo real...")
        print("[HARNESS] Aguardando preço atingir zonas de 60m com confirmação de fluxo...\n")
        
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[HARNESS] Encerrando monitoramento a pedido do operador.")
        feed.disconnect()
    except Exception as e:
        print(f"\n[HARNESS AVISO] Conexão DDE encerrada: {e}")
        feed.disconnect()


if __name__ == "__main__":
    main()
