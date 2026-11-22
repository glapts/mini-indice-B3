# Skill macro-global-guard
# Módulo Python desacoplado da skill de guarda macroeconômica global.
# Não altera nenhuma fórmula existente em core/agents/macro_agent.py.
# Consome dados já populados pelo agente existente e emite contrato JSON padronizado.

from datetime import datetime, time, timedelta
from typing import Dict, Any, Optional, List

from core.agents.base_agent import BaseAgent, AgentOpinion


class MacroGlobalGuardSkill(BaseAgent):
    """Skill de guarda macroeconômica global.

    Monitora S&P 500, Treasuries, DXY e calendário econômico dos EUA.
    Retorna BLOCK se houver evento de alto impacto ou dados STALE.
    """

    def __init__(self):
        super().__init__(name="macro-global-guard")
        self.sp500_change_pct: float = 0.0
        self.us10y_change_bps: float = 0.0
        self.dxy_change_pct: float = 0.0
        self._last_market_update: Optional[datetime] = None
        self.data_ttl_seconds = 120
        self.calendar_events: List[Dict[str, Any]] = []

    def update_market_data(
        self,
        sp500_change_pct: float,
        us10y_change_bps: float,
        dxy_change_pct: float,
        updated_at: Optional[datetime] = None,
    ):
        self.sp500_change_pct = sp500_change_pct
        self.us10y_change_bps = us10y_change_bps
        self.dxy_change_pct = dxy_change_pct
        self._last_market_update = updated_at or datetime.now()

    def add_calendar_event(
        self,
        name: str,
        event_time: datetime,
        before_min: int = 5,
        after_min: int = 10,
    ):
        self.calendar_events.append({
            "name": name,
            "time": event_time,
            "before_min": before_min,
            "after_min": after_min,
        })

    def _is_data_stale(self, now: datetime) -> bool:
        if self._last_market_update is None:
            return True
        return (now - self._last_market_update).total_seconds() > self.data_ttl_seconds

    def evaluate(self, current_time: Optional[datetime] = None) -> AgentOpinion:
        now = current_time or datetime.now()

        # 1. Evento de calendário em andamento -> BLOCK
        for ev in self.calendar_events:
            ev_time = ev["time"]
            start_window = ev_time - timedelta(minutes=ev["before_min"])
            end_window = ev_time + timedelta(minutes=ev["after_min"])
            if start_window <= now <= end_window:
                opinion = AgentOpinion(
                    agent_name=self.name,
                    bias="LOCKOUT",
                    confidence=1.0,
                    lockout=True,
                    veto_buy=True,
                    veto_sell=True,
                    reason=f"CALENDÁRIO EUA: Evento '{ev['name']}' em janela de alto impacto.",
                    metadata={"event": ev["name"], "data_quality": "GOOD"},
                    data_quality="GOOD",
                )
                self.last_opinion = opinion
                return opinion

        # 2. Janela de abertura de Wall Street -> BLOCK
        t = now.time()
        if (time(10, 28) <= t <= time(10, 35)) or (time(11, 28) <= t <= time(11, 35)):
            opinion = AgentOpinion(
                agent_name=self.name,
                bias="LOCKOUT",
                confidence=0.95,
                lockout=True,
                veto_buy=True,
                veto_sell=True,
                reason="ABERTURA DE WALL STREET: Janela de volatilidade extrema.",
                metadata={"time": t.strftime("%H:%M:%S"), "data_quality": "GOOD"},
                data_quality="GOOD",
            )
            self.last_opinion = opinion
            return opinion

        # 3. Dados desatualizados -> BLOCK
        if self._is_data_stale(now):
            opinion = AgentOpinion(
                agent_name=self.name,
                bias="LOCKOUT",
                confidence=0.0,
                lockout=True,
                veto_buy=True,
                veto_sell=True,
                reason="DADOS MACRO DESATUALIZADOS: feed externo excedeu TTL de segurança.",
                metadata={"data_quality": "STALE"},
                data_quality="STALE",
            )
            self.last_opinion = opinion
            return opinion

        # 4. Correlação S&P 500 / Treasuries
        veto_buy = False
        veto_sell = False
        bias = "NEUTRAL"
        confidence = 0.70
        reasons: List[str] = []

        if self.sp500_change_pct < -0.40 or self.us10y_change_bps > 4.0:
            veto_buy = True
            bias = "BEARISH"
            confidence = 0.85
            reasons.append(
                f"Aversão a Risco Global: S&P 500 ({self.sp500_change_pct:+.2f}%) "
                f"ou US 10Y ({self.us10y_change_bps:+.1f} bps)."
            )
        elif self.sp500_change_pct > 0.40 and self.dxy_change_pct < 0.0:
            veto_sell = True
            bias = "BULLISH"
            confidence = 0.85
            reasons.append(
                f"Apetite por Risco Global: S&P 500 ({self.sp500_change_pct:+.2f}%)."
            )
        else:
            bias = "NEUTRAL"
            confidence = 0.75
            reasons.append("Mercado externo em estabilidade.")

        opinion = AgentOpinion(
            agent_name=self.name,
            bias=bias,
            confidence=confidence,
            veto_buy=veto_buy,
            veto_sell=veto_sell,
            lockout=False,
            reason="; ".join(reasons),
            metadata={
                "sp500_pct": self.sp500_change_pct,
                "us10y_bps": self.us10y_change_bps,
                "dxy_pct": self.dxy_change_pct,
                "data_quality": "GOOD",
            },
            data_quality="GOOD",
        )
        self.last_opinion = opinion
        return opinion

    def to_json_contract(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        ts = now or datetime.now()
        opinion = self.last_opinion or self.evaluate(ts)

        if opinion.lockout or (opinion.veto_buy and opinion.veto_sell):
            status = "BLOCK"
        elif opinion.veto_buy:
            status = "VETO_COMPRA"
        elif opinion.veto_sell:
            status = "VETO_VENDA"
        else:
            status = "ALLOW"

        return {
            "skill": self.name,
            "timestamp_brt": ts.strftime("%Y-%m-%dT%H:%M:%S-03:00"),
            "status": status,
            "motivo": opinion.reason or "Sem restrições identificadas.",
            "dados_stale": opinion.data_quality == "STALE",
        }
