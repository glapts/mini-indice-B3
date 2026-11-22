"""
core/agents/orchestrator.py
Agente Orquestrador ("O Gestor de Mesa").
Consolida os pareceres dos Agentes Especialistas (Macro, Cesta/DI e Sentinela),
calcula o Score de Confiança consolidado, resolve conflitos e atualiza
atomicamente o arquivo 'data/runtime_state.json' lido pelo Execution Harness.
"""

import os
import json
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional

from core.agents.macro_agent import MacroAgent
from core.agents.basket_agent import BasketAgent
from core.agents.sentinel_agent import SentinelAgent
from core.harness.contracts import (
    RuntimeStateContract,
    ExecutionMode,
    TradingDirection,
    CircuitBreakerState,
    MacroRegimeState,
    BasketRegimeState
)


class Orchestrator:
    def __init__(
        self,
        macro_agent: Optional[MacroAgent] = None,
        basket_agent: Optional[BasketAgent] = None,
        sentinel_agent: Optional[SentinelAgent] = None,
        output_state_path: str = "data/runtime_state.json",
        execution_mode: ExecutionMode = ExecutionMode.COPILOT
    ):
        self.macro_agent = macro_agent or MacroAgent()
        self.basket_agent = basket_agent or BasketAgent()
        self.sentinel_agent = sentinel_agent or SentinelAgent()
        
        self.output_state_path = output_state_path
        self.execution_mode = execution_mode
        self.max_daily_stops = 2
        self.daily_stops_count = self._load_daily_stops_count()

    def _load_daily_stops_count(self) -> int:
        """Carrega o contador somente se o estado persistido for do dia atual."""
        try:
            with open(self.output_state_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            timestamp = datetime.fromisoformat(payload["timestamp"])
            if timestamp.date() == datetime.now().date():
                return int(payload.get("circuit_breaker", {}).get("daily_stops_count", 0))
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            pass
        return 0

    def record_stop_loss(self):
        """Registra um stop acionado no dia para o Circuit Breaker."""
        self.daily_stops_count += 1
        print(f"[ORQUESTRADOR] Stop registrado! Total hoje: {self.daily_stops_count}/{self.max_daily_stops}")
        self.run_cycle()

    def run_cycle(self, current_time: Optional[datetime] = None) -> RuntimeStateContract:
        """
        Executa um ciclo completo de consolidação de inteligência dos agentes
        e grava o runtime_state.json atualizado.
        """
        now = current_time or datetime.now()

        # 1. Coleta parecer de cada especialista
        op_macro = self.macro_agent.evaluate(now)
        op_basket = self.basket_agent.evaluate(now)
        op_sentinel = self.sentinel_agent.evaluate(now)

        # 2. Resolução de Travas Rígidas (Lockouts de Segurança)
        is_circuit_breaker_active = self.daily_stops_count >= self.max_daily_stops
        is_lockout_active = (
            op_sentinel.lockout or
            op_macro.lockout or
            op_basket.lockout or
            is_circuit_breaker_active
        )

        trading_enabled = not is_lockout_active

        # 3. Resolução de Direção Permitida (Vetos Cruzados)
        veto_buy = op_macro.veto_buy or op_basket.veto_buy or op_sentinel.veto_buy
        veto_sell = op_macro.veto_sell or op_basket.veto_sell or op_sentinel.veto_sell

        if veto_buy and veto_sell:
            allowed_dir = TradingDirection.NONE
        elif veto_buy:
            allowed_dir = TradingDirection.SHORT_ONLY
        elif veto_sell:
            allowed_dir = TradingDirection.LONG_ONLY
        else:
            allowed_dir = TradingDirection.BOTH

        # 4. Cálculo Ponderado do Score de Confiança
        # Pesos: Macro (0.35) + Cesta/DI (0.45) + Sentinela (0.20)
        base_confidence = (
            op_macro.confidence * 0.35 +
            op_basket.confidence * 0.45 +
            op_sentinel.confidence * 0.20
        )

        # Penalidade por conflito direto entre Macro e Cesta
        if (op_macro.bias == "BULLISH" and op_basket.bias == "BEARISH") or \
           (op_macro.bias == "BEARISH" and op_basket.bias == "BULLISH"):
            base_confidence -= 0.20

        confidence_score = max(0.10, min(1.0, round(base_confidence, 2)))

        if is_lockout_active:
            confidence_score = 0.0

        # 5. Montagem do Contrato RuntimeStateContract
        macro_state = MacroRegimeState(
            status=op_macro.bias,
            sp500_bias="BULLISH" if self.macro_agent.sp500_change_pct > 0 else "BEARISH",
            di_curve_bias="STRESSED" if self.basket_agent.di_rates.get("DI1F31", 0) > 5 else "STABLE",
            dxy_bias="BULLISH" if self.macro_agent.dxy_change_pct > 0 else "BEARISH",
            event_lockout=op_macro.lockout,
            lockout_reason=op_macro.reason if op_macro.lockout else None
        )

        basket_state = BasketRegimeState(
            synthetic_ibov_alignment="ALIGNED" if not op_basket.veto_buy else "DIVERGENT",
            vale3_petr4_status="POSITIVE" if not op_basket.veto_buy else "NEGATIVE"
        )

        circuit_breaker = CircuitBreakerState(
            daily_stops_count=self.daily_stops_count,
            max_daily_stops=self.max_daily_stops,
            lockout_active=is_circuit_breaker_active
        )

        runtime_state = RuntimeStateContract(
            timestamp=now.isoformat(),
            execution_mode=self.execution_mode,
            trading_enabled=trading_enabled,
            allowed_direction=allowed_dir,
            min_fvg_timeframe=15,
            risk_mode="CONSERVATIVE" if confidence_score < 0.75 else "NORMAL",
            confidence_score=confidence_score,
            circuit_breaker=circuit_breaker,
            macro_regime=macro_state,
            basket_regime=basket_state
        )

        # 6. Gravação Atômica do Arquivo (Evita colisão de leitura no Harness)
        self._write_state_atomic(runtime_state)

        return runtime_state

    def _write_state_atomic(self, state: RuntimeStateContract):
        """Grava o JSON usando arquivo temporário e replace atômico."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.output_state_path)), exist_ok=True)
            temp_dir = os.path.dirname(os.path.abspath(self.output_state_path))
            
            with tempfile.NamedTemporaryFile("w", dir=temp_dir, delete=False, encoding="utf-8") as tf:
                json.dump(state.model_dump(), tf, indent=2, ensure_ascii=False)
                temp_name = tf.name
            
            # Substituição atômica no sistema de arquivos do Windows
            os.replace(temp_name, os.path.abspath(self.output_state_path))
        except Exception as e:
            print(f"[ORQUESTRADOR ERRO] Falha ao gravar {self.output_state_path}: {e}")
