import json
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(base_dir, 'data', 'relatorios', 'resultado_jan_jul_2027.json'), 'r', encoding='utf-8') as f:
    data = json.load(f)

for m, d in data.items():
    print(f"{m} ({d['month_name']}): {len(d['days'])} dias | Trades: {d['trades_count']} | {d['wins_count']}W / {d['losses_count']}L | WR: {(d['wins_count']/d['trades_count']*100):.1f}% | Pts: {d['points_liq']:+.0f} | 1ct: R$ {d['pnl_1ct']:+.2f} | 5ct: R$ {d['pnl_5ct']:+.2f}")
