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
    parser.add_argument(
        "--use-tt-clipboard", action="store_true",
        help="Habilita o feed de Times & Trades individual via Area de Transferencia "
             "(exige copiar a janela de negocios no Profit Pro)",
    )
    parser.add_argument(
        "--demo-bypass-guards", action="store_true",
        help="TESTE EM DEMO: ignora somente trading_enabled e validacao de niveis; COPILOT apenas, sem ordens. Nao usar em conta real.",
    )
    parser.add_argument(
        "--demo-signal", action="store_true",
        help="Emite um sinal sintético DEMO_TEST_ONLY e encerra; não usa mercado nem envia ordem.",
    )
    parser.add_argument(
        "--demo-direction", choices=["LONG", "SHORT"], default="LONG",
        help="Direção do sinal sintético de teste.",
    )
    args = parser.parse_args()

    if args.demo_bypass_guards and args.mode.upper() != "COPILOT":
        parser.error("--demo-bypass-guards so pode ser usado com --mode COPILOT")
    if args.demo_signal and args.mode.upper() != "COPILOT":
        parser.error("--demo-signal so pode ser usado com --mode COPILOT")

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
    print(f" Referencia Niveis  : {niveis.data_referencia}")
    cb_status = f"Max {state.circuit_breaker.max_daily_stops} stops diários" if getattr(state.circuit_breaker, "enabled", False) else "DESABILITADO (Modo Demo Manual — Testes Livres)"
    print(f" Circuit Breaker    : {cb_status}")
    print(f" Trava de Horário   : 09:00 - 10:00 (OBSERVATION_ONLY) | 10:28 - 10:35 (NY Open)")
    print(f" Modo Operacional   : {exec_mode.value}")
    if exec_mode == ExecutionMode.COPILOT:
        print("  -> Alertas sonoros e visuais habilitados. Ordens confirmadas pelo trader.")
    else:
        print("  -> ENVIO AUTOMÁTICO DE ORDENS OCO ATIVO.")

    # Validacao inicial dos niveis: o radar de zonas so opera com niveis
    # coerentes com o pregao corrente.
    from core.harness.levels_validator import validate_levels
    initial_check = validate_levels(
        niveis=niveis,
        current_price=None,
        current_symbol=niveis.ativo,
    )
    if initial_check.reference_age_days is not None:
        print(f" Idade dos Niveis    : {initial_check.reference_age_days} dia(s) uteis desde {initial_check.reference_date}")
    print("=" * 80)

    harness = ExecutionHarness(
        niveis_contract=niveis,
        runtime_state=state,
        mode=exec_mode,
        runtime_state_path=os.path.join(base_dir, "data", "runtime_state.json"),
        demo_bypass_guards=args.demo_bypass_guards,
    )

    if args.demo_signal:
        from core.harness.contracts import TradingDirection
        direction = TradingDirection.LONG if args.demo_direction == "LONG" else TradingDirection.SHORT
        harness.emit_demo_test_signal(direction)
        return

    feed = ProfitDDEFeed()

    # Feed de Times & Trades individual (clipboard do Profit).
    # Desativado por padrao: exige que o operador copie a janela de negocios
    # no Profit, e sem isso o MicrostructureFilter operaria apenas sobre
    # trades SINTETICOS derivados de volume agregado do DDE.
    tt_feed = None
    if args.use_tt_clipboard:
        from feeds.tt_feed import TimesTradesClipboardFeed
        tt_feed = TimesTradesClipboardFeed(symbol=symbol)
        print(f"[TT] Times & Trades individual ATIVADO (clipboard). "
              f"Copie a janela de negocios no Profit para alimentar o tape reading.")
    else:
        print("[TT] Times & Trades individual DESATIVADO. "
              f"Use --use-tt-clipboard para habilitar (requer copia manual no Profit).")

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

        last_tt_report = 0.0
        while True:
            if tt_feed is not None:
                now_ts = time.time()
                if now_ts - last_tt_report >= 15:
                    last_tt_report = now_ts
                    try:
                        tt_trades = tt_feed.poll_clipboard()
                    except Exception as e:
                        tt_trades = []
                        print(f"[TT WARN] Falha ao ler o clipboard: {e}")
                    if tt_trades:
                        for t in tt_trades:
                            aggr = t.aggressor.value if hasattr(t.aggressor, 'value') else str(t.aggressor)
                            harness.on_trade(t.price, t.quantity, aggr, t.timestamp)
                        print(
                            f"[TT] {len(tt_trades)} negocios REAIS ingeridos "
                            f"(total no clipboard: {tt_feed.total_trades_seen})."
                        )
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[HARNESS] Encerrando monitoramento a pedido do operador.")
        feed.disconnect()
    except Exception as e:
        print(f"\n[HARNESS AVISO] Conexão DDE encerrada: {e}")
        feed.disconnect()


if __name__ == "__main__":
    main()
