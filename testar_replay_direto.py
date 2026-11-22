# Executa o replay deterministico do projeto SEM passar pelo main.py,
# evitando a validacao de licenca (licenca.key) que bloqueia comandos hoje.
#
# Uso:
#     cd C:\Users\glaci\Projetos\mini-indice-B3
#     python testar_replay_direto.py

from feeds.replay_feed import ReplayMarketFeed
from core.engine import WinAnalysisAssistant
from core.contract import get_current_win_contract


def main():
    print("=" * 70)
    print("TESTE DE REPLAY DETERMINISTICO (SEM LICENCA)")
    print("=" * 70)

    symbol = get_current_win_contract()
    feed = ReplayMarketFeed(symbol=symbol, initial_price=171400.0)
    assistant = WinAnalysisAssistant(feed=feed, symbol=symbol, mode="FIXO")
    assistant.start()

    print("\n1. Gerando historico base com oscilacao natural...")
    for i in range(120):
        bias = 0.25 if (i % 30 < 18) else -0.25
        feed.generate_step(trend_bias=bias, inject_sweep=False)

    print("\n2. Injetando Sweep de Liquidez no topo recente...")
    feed.generate_step(trend_bias=0.0, inject_sweep=True, sweep_direction="BEARISH")

    print("\n3. Avaliando barras de confirmacao...")
    setup_found = False
    for i in range(1, 15):
        feed.generate_step(trend_bias=-0.35, inject_sweep=False)
        alert = assistant.evaluate_now()
        if "STATUS: CONFIRMADO" in alert or "STATUS: AGUARDANDO" in alert:
            print(f"\n>>> GATILHO IDENTIFICADO NA BARRA +{i} DE CONFIRMACAO! <<<")
            print(alert)
            setup_found = True
            break

    if not setup_found:
        print("\n--- RESULTADO DA AVALIACAO DETERMINISTICA ---")
        alert = assistant.evaluate_now()
        print(alert)

    assistant.stop()
    print("\n[OK] Replay deterministico concluido com sucesso.")


if __name__ == "__main__":
    main()
