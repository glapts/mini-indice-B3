"""
core/agents/orchestrator_skills.py

Orquestrador de Agentes com integração das 3 Skills (camadas desacopladas).
Consolida os pareceres dos Agentes Especialistas (Macro, Cesta/DI e Sentinela)
e os contratos JSON das Skills, gravando atomicamente 'data/runtime_state.json'.

Regras de seguranca:
- NAO altera nenhuma fórmula matemática existente em core/agents/macro_agent.py,
  core/agents/basket_agent.py ou core/agents/sentinel_agent.py.
- As skills atuam exclusivamente como camadas desacopladas de filtro, contexto
  e emissão de vetos antes da liberação de alertas.
"""

import os
import json
import tempfile
import importlib
from datetime import datetime
from typing import Dict, Any, Optional

try:
    from zoneinfo import ZoneInfo
    TZ_BRAT = ZoneInfo("America/Sao_Paulo")
except Exception:
    TZ_BRAT = None

from core.agents.macro_agent import MacroAgent
from core.agents.basket_agent import BasketAgent
from core.agents.sentinel_agent import SentinelAgent
from core.harness.contracts import (
    RuntimeStateContract,
    ExecutionMode,
    TradingDirection,
    CircuitBreakerState,
    MacroRegimeState,
    BasketRegimeState,
)

# Import das Skills via importlib (nomes de diretorio com hifen nao sao modulos Python validos)
import sys
from pathlib import Path
_base_dir = Path(__file__).resolve().parents[2]  # raiz do projeto
for _skill_dir in [
    ".claude/skills/macro-global-guard",
    ".claude/skills/cesta-juros-veto",
    ".claude/skills/sentinela-politico-emergencia",
]:
    _p = str(_base_dir / _skill_dir)
    if _p not in sys.path:
        sys.path.insert(0, _p)

skill_macro_global = importlib.import_module("skill_macro_global")
skill_cesta_juros = importlib.import_module("skill_cesta_juros")
skill_sentinela = importlib.import_module("skill_sentinela")

MacroGlobalGuardSkill = skill_macro_global.MacroGlobalGuardSkill
CestaJurosVetoSkill = skill_cesta_juros.CestaJurosVetoSkill
SentinelaPoliticoEmergenciaSkill = skill_sentinela.SentinelaPoliticoEmergenciaSkill


class OrchestratorWithSkills:
    """
    Orquestrador que consolida Agentes Especialistas + 3 Skills desacopladas.
    """

    def __init__(
        self,
        macro_agent: Optional[MacroAgent] = None,
        basket_agent: Optional[BasketAgent] = None,
        sentinel_agent: Optional[SentinelAgent] = None,
        output_state_path: str = "data/runtime_state.json",
        execution_mode: ExecutionMode = ExecutionMode.COPILOT,
    ):
        self.macro_agent = macro_agent or MacroAgent()
        self.basket_agent = basket_agent or BasketAgent()
        self.sentinel_agent = sentinel_agent or SentinelAgent()

        # Instancia as 3 skills (camadas desacopladas)
        self.skill_macro = MacroGlobalGuardSkill()
        self.skill_cesta = CestaJurosVetoSkill()
        self.skill_sentinela = SentinelaPoliticoEmergenciaSkill()

        self.output_state_path = output_state_path
        self.execution_mode = execution_mode
        self.max_daily_stops = 2
        self.daily_stops_count = self._load_daily_stops_count()

        # Sincroniza dados dos agentes existentes para as skills
        self._sync_agent_data_to_skills()

    # ------------------------------------------------------------------
    # Sincronização de dados (apenas leitura dos agentes existentes)
    # ------------------------------------------------------------------
    def _sync_agent_data_to_skills(self):
        """Copia dados dos agentes existentes para as skills sem alterar fórmulas."""
        # Macro -> Skill Macro
        self.skill_macro.update_market_data(
            sp500_change_pct=self.macro_agent.sp500_change_pct,
            us10y_change_bps=self.macro_agent.us10y_change_bps,
            dxy_change_pct=self.macro_agent.dxy_change_pct,
            updated_at=self.macro_agent._last_market_update,
        )
        for ev in self.macro_agent.calendar_events:
            self.skill_macro.add_calendar_event(
                name=ev["name"],
                event_time=ev["time"],
                before_min=ev.get("before_min", 5),
                after_min=ev.get("after_min", 10),
            )

        # Cesta -> Skill Cesta
        for ticker, val in self.basket_agent.stocks.items():
            self.skill_cesta.update_stock(ticker, val)
        for contract, val in self.basket_agent.di_rates.items():
            self.skill_cesta.update_di(contract, val)

        # Sentinela -> Skill Sentinela
        for news in self.sentinel_agent.news_history:
            self.skill_sentinela.inject_news(
                text=news["text"],
                source=news.get("source", "Feed_Noticias"),
                timestamp=news.get("timestamp"),
            )
        if self.sentinel_agent.active_black_swan:
            # Re-injeta o black swan ativo na skill
            bs = self.sentinel_agent.active_black_swan
            self.skill_sentinela.active_black_swan = bs

    def _load_daily_stops_count(self) -> int:
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
        self.daily_stops_count += 1
        print(f"[ORQUESTRADOR] Stop registrado! Total hoje: {self.daily_stops_count}/{self.max_daily_stops}")
        self.run_cycle()

    def _now_brt(self) -> datetime:
        # Retorna datetime naive (sem fuso) para compatibilidade com os agentes
        # existentes que usam datetime.now() sem tzinfo.
        return datetime.now()

    def run_cycle(self, current_time: Optional[datetime] = None) -> RuntimeStateContract:
        """
        Executa ciclo completo: Agentes Especialistas + 3 Skills.
        Gravacao atomica de data/runtime_state.json.
        """
        now = current_time or self._now_brt()

        # Sincroniza dados antes de avaliar (garante consistência)
        self._sync_agent_data_to_skills()

        # 1. Parecer dos Agentes Especialistas (fórmulas existentes intactas)
        op_macro = self.macro_agent.evaluate(now)
        op_basket = self.basket_agent.evaluate(now)
        op_sentinel = self.sentinel_agent.evaluate(now)

        # 2. Contratos JSON das 3 Skills (camadas desacopladas)
        contract_macro = self.skill_macro.to_json_contract(now)
        contract_cesta = self.skill_cesta.to_json_contract(now)
        contract_sentinela = self.skill_sentinela.to_json_contract(now)

        # 3. Resolucao de travaduras rígidas (Lockouts)
        is_circuit_breaker_active = self.daily_stops_count >= self.max_daily_stops

        # Lockout se qualquer agente OU skill retornar BLOCK/EMERGENCY_HALT
        skill_lockout = (
            contract_macro["status"] in ("BLOCK", "EMERGENCY_HALT")
            or contract_cesta["status"] in ("BLOCK", "EMERGENCY_HALT")
            or contract_sentinela["status"] in ("BLOCK", "EMERGENCY_HALT")
        )

        is_lockout_active = (
            op_sentinel.lockout
            or op_macro.lockout
            or op_basket.lockout
            or skill_lockout
            or is_circuit_breaker_active
        )

        trading_enabled = not is_lockout_active

        # 4. Resolucao de direcao permitida (vetos cruzados)
        veto_buy = (
            op_macro.veto_buy or op_basket.veto_buy or op_sentinel.veto_buy
            or contract_macro["status"] == "VETO_COMPRA"
            or contract_cesta["status"] == "VETO_COMPRA"
            or contract_sentinela["status"] == "VETO_COMPRA"
        )
        veto_sell = (
            op_macro.veto_sell or op_basket.veto_sell or op_sentinel.veto_sell
            or contract_macro["status"] == "VETO_VENDA"
            or contract_cesta["status"] == "VETO_VENDA"
            or contract_sentinela["status"] == "VETO_VENDA"
        )

        if veto_buy and veto_sell:
            allowed_dir = TradingDirection.NONE
        elif veto_buy:
            allowed_dir = TradingDirection.SHORT_ONLY
        elif veto_sell:
            allowed_dir = TradingDirection.LONG_ONLY
        else:
            allowed_dir = TradingDirection.BOTH

        # 5. Score de confiança ponderado (pesos existentes)
        base_confidence = (
            op_macro.confidence * 0.35
            + op_basket.confidence * 0.45
            + op_sentinel.confidence * 0.20
        )

        if (op_macro.bias == "BULLISH" and op_basket.bias == "BEARISH") or \
           (op_macro.bias == "BEARISH" and op_basket.bias == "BULLISH"):
            base_confidence -= 0.20

        confidence_score = max(0.10, min(1.0, round(base_confidence, 2)))
        if is_lockout_active:
            confidence_score = 0.0

        # 6. Montagem do RuntimeStateContract
        macro_state = MacroRegimeState(
            status=op_macro.bias,
            sp500_bias="BULLISH" if self.macro_agent.sp500_change_pct > 0 else "BEARISH",
            di_curve_bias="STRESSED" if self.basket_agent.di_rates.get("DI1F31", 0) > 5 else "STABLE",
            dxy_bias="BULLISH" if self.macro_agent.dxy_change_pct > 0 else "BEARISH",
            event_lockout=op_macro.lockout,
            lockout_reason=op_macro.reason if op_macro.lockout else None,
        )

        basket_state = BasketRegimeState(
            synthetic_ibov_alignment="ALIGNED" if not op_basket.veto_buy else "DIVERGENT",
            vale3_petr4_status="POSITIVE" if not op_basket.veto_buy else "NEGATIVE",
        )

        circuit_breaker = CircuitBreakerState(
            daily_stops_count=self.daily_stops_count,
            max_daily_stops=self.max_daily_stops,
            lockout_active=is_circuit_breaker_active,
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
            basket_regime=basket_state,
        )

        # 7. Gravacao atomica
        self._write_state_atomic(runtime_state)

        # 8. Log consolidado dos contratos das skills
        print(f"[{now.strftime('%H:%M:%S')}] Ciclo | "
              f"Macro:{contract_macro['status']} | "
              f"Cesta:{contract_cesta['status']} | "
              f"Sentinela:{contract_sentinela['status']} | "
              f"Dir:{allowed_dir.value} | Conf:{confidence_score*100:.0f}%")

        return runtime_state

    def _write_state_atomic(self, state: RuntimeStateContract):
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.output_state_path)), exist_ok=True)
            temp_dir = os.path.dirname(os.path.abspath(self.output_state_path))
            with tempfile.NamedTemporaryFile("w", dir=temp_dir, delete=False, encoding="utf-8") as tf:
                json.dump(state.model_dump(), tf, indent=2, ensure_ascii=False)
                temp_name = tf.name
            os.replace(temp_name, os.path.abspath(self.output_state_path))
        except Exception as e:
            print(f"[ORQUESTRADOR ERRO] Falha ao gravar {self.output_state_path}: {e}")

    def get_skill_contracts(self) -> Dict[str, Any]:
        """Retorna os contratos JSON atuais das 3 skills para inspeção."""
        now = self._now_brt()
        return {
            "macro-global-guard": self.skill_macro.to_json_contract(now),
            "cesta-juros-veto": self.skill_cesta.to_json_contract(now),
            "sentinela-politico-emergencia": self.skill_sentinela.to_json_contract(now),
        }
