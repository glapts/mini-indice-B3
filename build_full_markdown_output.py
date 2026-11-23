import json
import math

import os
base_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(base_dir, 'data', 'relatorios', 'resultado_jan_jul_2027.json'), 'r', encoding='utf-8') as f:
    months_data = json.load(f)

for m_key, m in months_data.items():
    m_name = m["month_name"]
    days = m["days"]
    
    tot_days = len(days)
    pos_days = len([d for d in days if d["points_liq"] > 0])
    neg_days = len([d for d in days if d["points_liq"] < 0])
    neut_days = len([d for d in days if d["points_liq"] == 0])
    
    tot_trades = sum(d["trades_count"] for d in days)
    tot_wins = sum(d["wins"] for d in days)
    tot_losses = sum(d["losses"] for d in days)
    wr = (tot_wins / tot_trades * 100) if tot_trades > 0 else 0
    
    tot_pts = sum(d["points_liq"] for d in days)
    tot_1ct = sum(d["pnl_1ct"] for d in days)
    tot_5ct = sum(d["pnl_5ct"] for d in days)
    
    # Simulação de trades para drawdown e profit factor
    # Cada vitória dá +395 pts (400 - 5 slippage), cada derrota dá -255 pts (-250 - 5 slippage)
    # Lucro bruto = tot_wins * (395 * 0.20 - 0.60) = tot_wins * 78.40
    # Perda bruta = tot_losses * (255 * 0.20 + 0.60) = tot_losses * 51.60
    gain_reais = tot_wins * 78.40
    loss_reais = tot_losses * 51.60
    pf = (gain_reais / loss_reais) if loss_reais > 0 else 999.0
    payoff = (395.0 / 255.0)  # ~1.55
    ev_pts = tot_pts / tot_trades if tot_trades > 0 else 0
    ev_reais = tot_1ct / tot_trades if tot_trades > 0 else 0
    
    # Drawdown diário
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for d in days:
        equity += d["pnl_1ct"]
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd
    if max_dd == 0:
        max_dd = 51.60  # no trade level, at least 1 stop
    
    print(f"\n### {m_name.upper()} DE 2027")
    print("```text")
    print(f"================================================================================")
    print(f"  RELATÓRIO DE REPLAY EM LOTE & BACKTEST — {m_name.upper()} DE 2027")
    print(f"  Ativo: WINZ27 (Mini-Índice B3) | Modo: FIXO (Stop: 250 pts | Alvo: 400 pts)")
    print(f"  Custos Computados: Slippage 5.0 pts/trade + Taxas B3 R$ 0.60/trade")
    print(f"================================================================================")
    print("")
    print("1. RESUMO EXECUTIVO DIÁRIO:")
    print("-" * 80)
    print(f"{'Data':^10} | {'Barras':^6} | {'Trades':^6} | {'Vitórias':^8} | {'Derrotas':^8} | {'WR %':^6} | {'Saldo Pts':^10} | {'Líq. 1ct':^12}")
    print("-" * 80)
    for d in days:
        tag = "+" if d["points_liq"] > 0 else ""
        print(f"{d['date_str']:^10} | {d['candles_count']:^6} | {d['trades_count']:^6} | {d['wins']:^8} | {d['losses']:^8} | {d['win_rate']:5.1f}% | {tag}{d['points_liq']:>8.0f} pts | R$ {d['pnl_1ct']:>9.2f}")
    print("-" * 80)
    print("")
    print("2. MÉTRICAS CONSOLIDADAS DE PERFORMANCE:")
    print("-" * 80)
    print(f"Total de Pregões Testados     : {tot_days} dias ({pos_days} Positivos | {neg_days} Negativos | {neut_days} Neutros)")
    print(f"Taxa de Dias Lucrativos        : {(pos_days/tot_days*100):.1f}%")
    print(f"Total de Operações Disparadas  : {tot_trades} trades ({tot_wins} Alvos / {tot_losses} Stops)")
    print(f"Média de Trades por Pregão    : {(tot_trades/tot_days):.1f} trades/dia")
    print(f"Taxa de Acerto Global (WinRate): {wr:.1f}% (Breakeven R:R 1.6 é 38.5%)")
    print(f"Saldo Total em Pontos (Líquido): {tot_pts:+,.0f} pontos (com 5.0 pts de derrapagem)")
    print(f"Resultado Líquido (1 contrato) : R$ {tot_1ct:+,.2f}")
    print(f"Resultado Líquido (5 contratos): R$ {tot_5ct:+,.2f}")
    print(f"Fator de Lucro (Profit Factor) : {pf:.2f}")
    print(f"Relação Payoff (Gain / Loss)   : {payoff:.2f}")
    print(f"Expectativa Matemática / Trade : {ev_pts:+.1f} pontos | R$ {ev_reais:+.2f} por trade")
    print(f"Drawdown Máximo Estimado       : R$ {max_dd:,.2f} ({max_dd/0.20:,.0f} pts)")
    print("-" * 80)
    print("```")
