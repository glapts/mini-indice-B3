"""
simular_outubro_real_5ct.py
Executa a simulação dia a dia com COTAÇÕES 100% REAIS da B3 para o mês de OUTUBRO DE 2026
utilizando o lote padrão de 5 CONTRATOS (R$ 1,00 por ponto) e o algoritmo com suas 5 camadas.
"""

import os
import sys
from datetime import date
from typing import Dict, List, Any

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from batch_backtest import BatchBacktestRunner, load_and_group_csv_files


def run_october_real_simulation():
    csv_real_path = os.path.join(ROOT_DIR, "data", "historico", "WINFUT_REAL_2026.csv")
    
    if not os.path.exists(csv_real_path):
        print(f"[ERRO] Base real de dados não encontrada em: {csv_real_path}")
        return

    print("=" * 80)
    print("   SIMULAÇÃO DO ALGORITMO COM DADOS 100% REAIS DA B3 — OUTUBRO DE 2026")
    print("   Configuração: 5 Minicontratos WIN | Stop Fixo: 250 pts | Alvo Fixo: 400 pts")
    print("   Custos Computados: Slippage 5 pts/trade + Taxas B3 R$ 0,60 por contrato")
    print("=" * 80)
    print("\n[1/3] Carregando cotações históricas reais de 1 minuto exportadas do Profit Pro...")

    # Carregar e agrupar todas as sessões da base real
    all_sessions = load_and_group_csv_files(file_path=csv_real_path)

    # Filtrar estritamente o mês de Outubro/2026
    october_sessions: Dict[date, List[Dict[str, Any]]] = {
        d: candles for d, candles in all_sessions.items()
        if d.year == 2026 and d.month == 10
    }

    if not october_sessions:
        print("[ERRO] Nenhuma sessão de Outubro/2026 encontrada na base de dados.")
        return

    total_candles = sum(len(c) for c in october_sessions.values())
    print(f"[OK] Identificados {len(october_sessions)} pregões reais em Outubro/2026 ({total_candles:,} candles de 1m).")
    print("\n[2/3] Executando simulação candle a candle dia a dia...")

    # Instanciar o runner para 5 contratos
    runner = BatchBacktestRunner(
        symbol="WINZ26",
        mode="FIXO",
        slippage_points=5.0,
        b3_roundtrip_cost=0.60,
        contracts=5
    )

    runner.run_all_sessions(october_sessions)

    print("\n[3/3] Consolidando resultados e gerando relatório executivo...\n")
    report_text = runner.generate_report()
    print(report_text)

    # Exportar arquivos específicos de Outubro
    out_dir = os.path.join(ROOT_DIR, "data", "relatorios")
    txt_path, csv_path = runner.export_to_files(output_dir=out_dir)

    # Renomear para identificação fácil de Outubro
    oct_txt = os.path.join(out_dir, "RELATORIO_OUTUBRO_2026_DADOS_REAIS_5CT.txt")
    oct_csv = os.path.join(out_dir, "TRADES_OUTUBRO_2026_DADOS_REAIS_5CT.csv")
    
    try:
        if os.path.exists(oct_txt):
            os.remove(oct_txt)
        if os.path.exists(oct_csv):
            os.remove(oct_csv)
        os.rename(txt_path, oct_txt)
        os.rename(csv_path, oct_csv)
        print(f"[ARQUIVO] Relatório detalhado salvo em : {oct_txt}")
        print(f"[ARQUIVO] Planilha de trades salva em   : {oct_csv}")
    except Exception:
        print(f"[ARQUIVO] Relatório detalhado salvo em : {txt_path}")
        print(f"[ARQUIVO] Planilha de trades salva em   : {csv_path}")

    print("\n" + "=" * 80)
    print("   SIMULAÇÃO DE OUTUBRO/2026 CONCLUÍDA COM SUCESSO!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_october_real_simulation()
