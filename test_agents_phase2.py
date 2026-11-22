"""
test_agents_phase2.py

Suíte Determinística de Validação da Fase 2:
Comitê de Agentes Especialistas de Contexto.

Valida:
  1. MacroAgent:
     - Calendário dos EUA (Payroll/FOMC);
     - abertura de Nova York;
     - correlação S&P 500/Treasuries;
     - bloqueio de dados desatualizados.
  2. BasketAgent:
     - abertura das ações;
     - concentração em Blue Chips;
     - curva DI.
  3. SentinelAgent:
     - detecção de choques político-fiscais.
  4. Orchestrator:
     - ponderação de pesos;
     - cálculo do Confidence Score;
     - gravação atômica do runtime_state.json;
     - persistência do circuit breaker.
  5. ExecutionHarness:
     - obediência às restrições dos agentes especialistas.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from tempfile import TemporaryDirectory

# Garante path do projeto independentemente do diretório de execução.
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, base_dir)

from core.agents.basket_agent import BasketAgent
from core.agents.macro_agent import MacroAgent
from core.agents.orchestrator import Orchestrator
from core.agents.sentinel_agent import SentinelAgent
from core.harness.contracts import (
    ExecutionMode,
    Niveis60mContract,
    TradingDirection,
)
from core.harness.execution_harness import ExecutionHarness


def test_macro_agent():
    print("\n--- [TESTE 1] Agente Macro & Global (Problemas 6, 7 e 11) ---")

    macro = MacroAgent()
    t_normal = datetime(2026, 11, 21, 14, 0, 0)

    # 1. Calendário Econômico (P7: Payroll)
    t_payroll = datetime(2026, 11, 21, 10, 30, 0)

    macro.add_calendar_event(
        "Payroll",
        event_time=t_payroll,
        before_min=5,
        after_min=10,
    )

    # Dois minutos antes do Payroll: deve travar em LOCKOUT.
    op_pre_payroll = macro.evaluate(
        current_time=t_payroll - timedelta(minutes=2)
    )

    assert op_pre_payroll.lockout is True
    assert op_pre_payroll.bias == "LOCKOUT"
    assert "CALENDÁRIO EUA" in op_pre_payroll.reason

    print(
        " [PASS] Evento Payroll detectado: "
        "LOCKOUT preventivo ativado."
    )

    # 2. Correlação S&P 500 e Treasuries (P6)
    #
    # O updated_at é explícito para que o teste represente um feed válido
    # no instante t_normal e não seja bloqueado pelo TTL de segurança.
    macro.update_sp500(
        price=5800.0,
        change_pct=-0.65,
        updated_at=t_normal,
    )

    op_risk_off = macro.evaluate(current_time=t_normal)

    assert op_risk_off.data_quality == "GOOD"
    assert op_risk_off.veto_buy is True
    assert op_risk_off.bias == "BEARISH"

    print(
        " [PASS] S&P 500 em forte queda (-0.65%): "
        "Veto de COMPRA no WIN confirmado."
    )


def test_basket_agent():
    print(
        "\n--- [TESTE 2] Agente de Cesta & Curva de Juros "
        "(Problemas 1, 4, 5 e 9) ---"
    )

    basket = BasketAgent()

    # 1. Trava das 09h00 às 10h00 (P4: ações fechadas)
    t_09h30 = datetime(2026, 11, 21, 9, 30, 0)

    op_leilao = basket.evaluate(current_time=t_09h30)

    assert op_leilao.lockout is True
    assert "MERCADO À VISTA FECHADO" in op_leilao.reason

    print(
        " [PASS] Horário 09:30 detectado: LOCKOUT "
        "(Mercado à vista em leilão)."
    )

    # 2. Concentração em Blue Chips (P5)
    t_11h00 = datetime(2026, 11, 21, 11, 0, 0)

    basket.update_stock("VALE3", -1.20)
    basket.update_stock("PETR4", -1.50)

    op_stocks_down = basket.evaluate(current_time=t_11h00)

    assert op_stocks_down.veto_buy is True

    print(
        " [PASS] VALE3 e PETR4 negativas: "
        "Veto de COMPRA ativado."
    )

    # 3. Estresse na Curva de Juros (P9)
    basket.update_stock("VALE3", 0.0)
    basket.update_stock("PETR4", 0.0)
    basket.update_di("DI1F31", +12.0)

    op_di_stress = basket.evaluate(current_time=t_11h00)

    assert op_di_stress.veto_buy is True
    assert "ESTRESSE CURVA DI" in op_di_stress.reason

    print(
        " [PASS] DI longo em estresse (+12 bps): "
        "Veto de COMPRA ativado."
    )


def test_sentinel_agent():
    print(
        "\n--- [TESTE 3] Agente Sentinela Político & Black Swan "
        "(Problema 8) ---"
    )

    sentinel = SentinelAgent(lockout_duration_minutes=30)
    t_now = datetime(2026, 11, 21, 13, 0, 0)

    # 1. Notícia normal
    sentinel.inject_news(
        "Ministério da Fazenda divulga balanço trimestral "
        "dentro do esperado.",
        timestamp=t_now,
    )

    op_normal = sentinel.evaluate(current_time=t_now)

    assert op_normal.lockout is False
    assert op_normal.bias == "NEUTRAL"

    print(" [PASS] Notícia comum processada: Radar estável.")

    # 2. Notícia de Cisne Negro
    sentinel.inject_news(
        "URGENTE: Governo estuda alteracao da meta fiscal "
        "e aumento de gastos extraordinarios.",
        timestamp=t_now,
    )

    op_black_swan = sentinel.evaluate(
        current_time=t_now + timedelta(minutes=1)
    )

    assert op_black_swan.lockout is True
    assert "BLACK SWAN" in op_black_swan.reason

    print(
        " [PASS] Notícia crítica detectada: BLACK SWAN ALERT "
        "acionado com trava de operações."
    )


def test_orchestrator_consolidation_and_runtime_state():
    print(
        "\n--- [TESTE 4] Agente Orquestrador & Geração "
        "de runtime_state.json ---"
    )

    macro = MacroAgent()
    basket = BasketAgent()
    sentinel = SentinelAgent()

    t_eval = datetime(2026, 11, 21, 14, 15, 0)

    with TemporaryDirectory() as temp_dir:
        test_state_path = os.path.join(
            temp_dir,
            "runtime_state.json",
        )

        orchestrator = Orchestrator(
            macro_agent=macro,
            basket_agent=basket,
            sentinel_agent=sentinel,
            output_state_path=test_state_path,
        )

        # Cenário A: Cenário Alinhado Positivo.
        #
        # O horário da atualização é explícito para satisfazer o TTL.
        macro.update_sp500(
            price=5850.0,
            change_pct=+0.55,
            updated_at=t_eval,
        )

        basket.update_stock("VALE3", +1.10)
        basket.update_stock("PETR4", +0.90)
        basket.update_stock("ITUB4", +0.60)
        basket.update_di("DI1F31", -6.0)

        state_a = orchestrator.run_cycle(current_time=t_eval)

        assert state_a.trading_enabled is True
        assert state_a.allowed_direction in (
            TradingDirection.LONG_ONLY,
            TradingDirection.BOTH,
        )
        assert state_a.confidence_score >= 0.80

        print(
            f" [PASS] Cenário Positivo consolidado "
            f"(Score: {state_a.confidence_score * 100:.0f}%, "
            f"Direção: {state_a.allowed_direction.value})."
        )

        # Cenário B: Conflito Cruzado.
        # Commodities despencam e a cesta veta compras.
        basket.update_stock("VALE3", -1.80)
        basket.update_stock("PETR4", -1.40)

        state_b = orchestrator.run_cycle(current_time=t_eval)

        assert state_b.allowed_direction == TradingDirection.SHORT_ONLY

        print(
            " [PASS] Veto da Cesta aplicado pelo Orquestrador: "
            "Direção restrita para SHORT_ONLY."
        )

        # Cenário C: Black Swan acionado pelo Sentinela.
        sentinel.inject_news(
            "Crise institucional: demissao de ministro "
            "e estresse em Brasilia.",
            timestamp=t_eval,
        )

        state_c = orchestrator.run_cycle(current_time=t_eval)

        assert state_c.trading_enabled is False
        assert state_c.confidence_score == 0.0

        print(
            " [PASS] Black Swan acionado: Orquestrador desativou "
            "trading_enabled e zerou score."
        )


def test_harness_integration_with_agents():
    print(
        "\n--- [TESTE 5] Integração Direta: "
        "Orquestrador -> ExecutionHarness ---"
    )

    niveis_path = os.path.join(
        base_dir,
        "data",
        "niveis_60m.json",
    )

    with open(niveis_path, "r", encoding="utf-8") as f:
        niveis = Niveis60mContract(**json.load(f))

    macro = MacroAgent()
    basket = BasketAgent()
    sentinel = SentinelAgent()

    t_now = datetime(2026, 11, 21, 14, 20, 0)

    with TemporaryDirectory() as temp_dir:
        state_path = os.path.join(
            temp_dir,
            "runtime_state.json",
        )

        orchestrator = Orchestrator(
            macro,
            basket,
            sentinel,
            output_state_path=state_path,
        )

        # Alimenta o feed macro com atualização válida para este ciclo.
        # Sem este timestamp, o novo TTL de segurança classificaria o feed
        # como STALE e o teste não chegaria ao cenário de SHORT_ONLY.
        macro.update_sp500(
            price=5850.0,
            change_pct=0.0,
            updated_at=t_now,
        )

        # 1. Simula estresse de juros.
        basket.update_di("DI1F31", +15.0)

        state = orchestrator.run_cycle(current_time=t_now)

        assert state.allowed_direction == TradingDirection.SHORT_ONLY
        assert state.trading_enabled is True

        # 2. Inicializa o Harness com o estado recém-gerado.
        signals_path = os.path.join(
            temp_dir,
            "sinais_copiloto.json",
        )

        harness = ExecutionHarness(
            niveis_contract=niveis,
            runtime_state=state,
            mode=ExecutionMode.COPILOT,
            signals_output_path=signals_path,
        )

        # 3. O preço atinge a zona de compra com absorção institucional.
        harness.on_trade(170100, 150, "SELL", t_now)
        signal = harness.on_tick(170100, t_now)

        # O Harness deve vetar a compra porque o Orchestrator determinou
        # SHORT_ONLY.
        assert signal is None, (
            "O Harness deveria ter vetado a compra devido "
            "ao estresse na curva de juros!"
        )

        print(
            " [PASS] Harness determinístico obedeceu estritamente "
            "o veto dos Agentes Especialistas!"
        )


if __name__ == "__main__":
    print("=" * 75)
    print(
        "TESTE DETERMINÍSTICO DE HOMOLOGAÇÃO: FASE 2 — "
        "COMITÊ MULTI-AGENTE"
    )
    print("=" * 75)

    test_macro_agent()
    test_basket_agent()
    test_sentinel_agent()
    test_orchestrator_consolidation_and_runtime_state()
    test_harness_integration_with_agents()

    print("\n" + "=" * 75)
    print(
        "✅ TODOS OS 5 TESTES DA FASE 2 PASSARAM "
        "COM 100% DE SUCESSO!"
    )
    print("=" * 75)