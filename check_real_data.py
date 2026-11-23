import os
import sys
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from feeds.csv_feed import parse_raw_csv_text
from batch_backtest import is_b3_holiday

def check_history_folder(dir_path: str = "data/historico"):
    target_dir = os.path.join(ROOT_DIR, dir_path) if not os.path.isabs(dir_path) else dir_path
    if not os.path.exists(target_dir):
        print(f"[!] Pasta não encontrada: {target_dir}")
        return

    csv_files = []
    for root, _, files in os.walk(target_dir):
        for f in files:
            if f.lower().endswith((".csv", ".txt")) and not f.startswith("WIN_SAMPLE"):
                csv_files.append(os.path.join(root, f))
    
    print("=" * 75)
    print("VALIDADOR DE ARQUIVOS DE DADOS HISTÓRICOS REAIS (B3 / PROFIT PRO)")
    print("=" * 75)
    print(f"Diretório monitorado: {target_dir}\n")

    if not csv_files:
        print("Nenhum arquivo CSV real foi detectado na pasta ainda.")
        print("\nPara carregar os dados reais:")
        print(" 1. Abra o gráfico de 1 minuto do WIN$ no Profit Pro.")
        print(" 2. Exporte de Janeiro a Novembro para um arquivo .csv")
        print(f" 3. Salve o arquivo nesta pasta: {target_dir}")
        print("=" * 75)
        return

    total_candles = 0
    all_dates = set()

    for fpath in csv_files:
        fname = os.path.basename(fpath)
        try:
            with open(fpath, "r", encoding="latin1", errors="replace") as f:
                content = f.read()
            records = parse_raw_csv_text(content)
            if records:
                file_dates = sorted(list(set(r["timestamp"].date() for r in records)))
                total_candles += len(records)
                all_dates.update(file_dates)
                print(f"✅ {fname:<30} | {len(records):>6} candles | {file_dates[0].strftime('%d/%m/%Y')} até {file_dates[-1].strftime('%d/%m/%Y')}")
            else:
                print(f"⚠️ {fname:<30} | Formato incompatível ou vazio")
        except Exception as e:
            print(f"❌ {fname:<30} | Erro de leitura: {e}")

    sorted_dates = sorted(list(all_dates))
    trading_dates = [d for d in sorted_dates if d.weekday() < 5 and not is_b3_holiday(d)]

    print("-" * 75)
    print(f"Total de Arquivos Analisados   : {len(csv_files)}")
    print(f"Total de Candles Identificados : {total_candles:,} barras de 1 minuto")
    print(f"Total de Pregões Oficiais B3   : {len(trading_dates)} dias úteis")
    if sorted_dates:
        print(f"Período Coberto                : {sorted_dates[0].strftime('%d/%m/%Y')} até {sorted_dates[-1].strftime('%d/%m/%Y')}")
    print("=" * 75)
    print("\nTudo pronto! Para rodar o backtest oficial nestes dados reais, execute:")
    print(f"python batch_backtest.py --dir \"{target_dir}\" --mode FIXO\n")

if __name__ == "__main__":
    check_history_folder()
