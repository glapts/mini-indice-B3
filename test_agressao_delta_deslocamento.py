"""
test_agressao_delta_deslocamento.py
Script determinístico para análise e teste dos cenários de Agressão de Compra e Venda
com Delta Positivo (+) / Negativo (-) e Deslocamento de Preço de +50 e -50 pontos no Mini-Índice (WIN).
"""

import sys
import os
from datetime import datetime, timedelta

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.models import Trade, AggressorSide, Direction, SignalSetup, SetupStatus
from core.contract import WIN_SPEC, TZ_BRASILIA
from analysis.tape_reading import TapeReadingAnalyzer
from setups.setup_engine import SetupEngine
from analysis.alert_formatter import format_operational_alert
import colorama
from colorama import Fore, Back, Style

colorama.init(autoreset=True)


def simular_cenario(
    nome_cenario: str,
    descricao: str,
    agressores: str,          # "COMPRA" ou "VENDA"
    delta_alvo: int,           # ex: +5000 ou -5000
    deslocamento_pts: float,  # +50.0 ou -50.0
    preco_base: float = 173000.0
):
    print("\n" + "=" * 80)
    print(Fore.CYAN + Style.BRIGHT + f"  TESTE: {nome_cenario}")
    print(Fore.WHITE + f"  Condições: Agressão {agressores} | Delta: {delta_alvo:+d} | Deslocamento: {deslocamento_pts:+.0f} pts")
    print("=" * 80)
    print(f"Objetivo Analítico: {descricao}\n")

    analyzer = TapeReadingAnalyzer(window_seconds=300, asset_spec=WIN_SPEC)
    now = datetime.now(TZ_BRASILIA)

    # Injetar trades para construir o volume e o delta desejado
    # Se delta for +5000: Compra = 7500 ct, Venda = 2500 ct (total 10000 ct)
    # Se delta for -5000: Venda = 7500 ct, Compra = 2500 ct (total 10000 ct)
    if delta_alvo > 0:
        buy_qty = 7500
        sell_qty = 2500
    else:
        buy_qty = 2500
        sell_qty = 7500

    # Injetar os negócios distribuídos ao longo do preço inicial até o preço final
    preco_inicio = preco_base
    preco_fim = preco_base + deslocamento_pts

    # Simular 10 trades de compra e 10 trades de venda
    n_trades = 10
    buy_per_trade = buy_qty // n_trades
    sell_per_trade = sell_qty // n_trades

    for i in range(n_trades):
        t_time = now - timedelta(seconds=(n_trades - i) * 15)
        # Preço interpolado
        p_interp = preco_inicio + (deslocamento_pts * (i / max(1, n_trades - 1)))
        
        # Trade de compra
        analyzer.add_trade(Trade(
            trade_id=f"B_{i}",
            timestamp=t_time,
            price=p_interp,
            quantity=buy_per_trade,
            aggressor=AggressorSide.BUY
        ))
        
        # Trade de venda
        analyzer.add_trade(Trade(
            trade_id=f"S_{i}",
            timestamp=t_time + timedelta(seconds=2),
            price=p_interp,
            quantity=sell_per_trade,
            aggressor=AggressorSide.SELL
        ))

    metrics = analyzer.get_window_metrics(seconds=300)
    delta_real = metrics["delta"]
    disp_real = metrics["price_displacement_pts"]
    padrao = metrics["flow_pattern"]

    print(f"📊 [MÉTRICAS DO TAPE READING]:")
    print(f"   * Agressão Compradora : {metrics['buy_volume']:,} contratos")
    print(f"   * Agressão Vendedora  : {metrics['sell_volume']:,} contratos")
    print(f"   * DELTA Calculado     : {delta_real:+,d} contratos")
    print(f"   * Deslocamento Preço  : {disp_real:+.0f} pontos ({preco_inicio:.0f} -> {preco_fim:.0f})")
    print(f"   * Padrão Classificado : {Fore.YELLOW}{padrao}{Style.RESET_ALL}")

    # Avaliar reação com o SetupEngine
    engine = SetupEngine(mode="FIXO", asset_spec=WIN_SPEC)
    alinhado_compra = engine._is_flow_aligned(Direction.COMPRA, metrics, flow_available=True)
    alinhado_venda = engine._is_flow_aligned(Direction.VENDA, metrics, flow_available=True)

    # Avaliar regras de Sweet Spot e Flow Override (conforme core/engine.py)
    # Sweet Spot WIN: Delta >= +3000 e Deslocamento entre +50 e +180 (para compra)
    # Sweet Spot WIN: Delta <= -3000 e Deslocamento entre -180 e -50 (para venda)
    flow_override_compra = False
    flow_override_venda = False

    if delta_real >= 3000:
        if 50.0 <= disp_real <= 180.0:
            if "ABSORÇÃO VENDEDORA" not in padrao.upper():
                flow_override_compra = True

    if delta_real <= -3000:
        if -180.0 <= disp_real <= -50.0:
            if "ABSORÇÃO COMPRADORA" not in padrao.upper():
                flow_override_venda = True

    print(f"\n🧠 [DECISÃO DETERMINÍSTICA DO ALGORITMO]:")
    print(f"   * Fluxo autoriza COMPRA?       : {'✅ SIM' if alinhado_compra else '❌ NÃO (BLOQUEADO)'}")
    print(f"   * Fluxo autoriza VENDA?        : {'✅ SIM' if alinhado_venda else '❌ NÃO (BLOQUEADO)'}")
    print(f"   * Flow Override Compra (iFVG)? : {'⚡ ATIVO (Rompe FVG)' if flow_override_compra else '⛔ INATIVO (Respeita FVG)'}")
    print(f"   * Flow Override Venda (iFVG)?  : {'⚡ ATIVO (Rompe FVG)' if flow_override_venda else '⛔ INATIVO (Respeita FVG)'}")

    return {
        "cenario": nome_cenario,
        "delta": delta_real,
        "deslocamento": disp_real,
        "padrao": padrao,
        "alinhado_compra": alinhado_compra,
        "alinhado_venda": alinhado_venda,
        "flow_override_compra": flow_override_compra,
        "flow_override_venda": flow_override_venda
    }


def main():
    print(Fore.YELLOW + Style.BRIGHT + """
==============================================================================
   BATERIA DE TESTES OFICIAIS — AGRESSÃO, DELTA (+/-) E DESLOCAMENTO (+/- 50 PTS)
   Mini-Índice B3 (WIN) — Motor Quantitativo de SMC & Tape Reading
==============================================================================
    """)

    resultados = []

    # -------------------------------------------------------------------------
    # CENÁRIO 1: Agressão Compradora | Delta Positivo (+5.000) | Deslocamento +50 pts
    # -------------------------------------------------------------------------
    r1 = simular_cenario(
        nome_cenario="1. CONTINUIDADE COMPRADORA PERFEITA (SWEET SPOT)",
        descricao="Agressão de compra maciça provocando deslocamento a favor (+50 pts). Cenário ideal de expansão direcional.",
        agressores="COMPRA",
        delta_alvo=+5000,
        deslocamento_pts=+50.0
    )
    resultados.append(r1)

    # -------------------------------------------------------------------------
    # CENÁRIO 2: Agressão Compradora | Delta Positivo (+5.000) | Deslocamento -50 pts
    # -------------------------------------------------------------------------
    r2 = simular_cenario(
        nome_cenario="2. ABSORÇÃO PASSIVA VENDEDORA (ARMADILHA DE COMPRA / TOPO FALSO)",
        descricao="Compradores agrediram massivamente a mercado (+5.000 ct), mas o preço CAIU -50 pts! Institucional passivo colocou barreira no topo.",
        agressores="COMPRA",
        delta_alvo=+5000,
        deslocamento_pts=-50.0
    )
    resultados.append(r2)

    # -------------------------------------------------------------------------
    # CENÁRIO 3: Agressão Vendedora | Delta Negativo (-5.000) | Deslocamento -50 pts
    # -------------------------------------------------------------------------
    r3 = simular_cenario(
        nome_cenario="3. CONTINUIDADE VENDEDORA PERFEITA (SWEET SPOT)",
        descricao="Agressão de venda maciça provocando deslocamento a favor (-50 pts). Cenário ideal de queda direcional limpa.",
        agressores="VENDA",
        delta_alvo=-5000,
        deslocamento_pts=-50.0
    )
    resultados.append(r3)

    # -------------------------------------------------------------------------
    # CENÁRIO 4: Agressão Vendedora | Delta Negativo (-5.000) | Deslocamento +50 pts
    # -------------------------------------------------------------------------
    r4 = simular_cenario(
        nome_cenario="4. ABSORÇÃO PASSIVA COMPRADORA (ARMADILHA DE VENDA / FUNDO FALSO)",
        descricao="Vendedores agrediram massivamente a mercado (-5.000 ct), mas o preço SUBIU +50 pts! Institucional passivo absorveu toda a venda no fundo.",
        agressores="VENDA",
        delta_alvo=-5000,
        deslocamento_pts=+50.0
    )
    resultados.append(r4)

    print("\n" + "=" * 80)
    print(Fore.GREEN + Style.BRIGHT + "   RESUMO COMPARATIVO DOS 4 CENÁRIOS DE AGRESSÃO:")
    print("=" * 80)
    for r in resultados:
        print(f"• {r['cenario']}:")
        print(f"   Delta: {r['delta']:+d} | Deslocamento: {r['deslocamento']:+.0f} pts | Padrão: {r['padrao']}")
        print(f"   Compra Autorizada? {r['alinhado_compra']} | Venda Autorizada? {r['alinhado_venda']}")
        print(f"   Flow Override Ativo? Compra={r['flow_override_compra']} / Venda={r['flow_override_venda']}")
        print("-" * 80)


if __name__ == "__main__":
    main()
