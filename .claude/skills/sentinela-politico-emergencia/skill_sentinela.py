# Skill sentinela-politico-emergencia
# Módulo Python desacoplado da skill de sentinela político-fiscal de emergência.
# Não altera nenhuma fórmula existente em core/agents/sentinel_agent.py.
# Consome dados já populados pelo agente existente e emite contrato JSON padronizado.

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from core.agents.base_agent import BaseAgent, AgentOpinion


class SentinelaPoliticoEmergenciaSkill(BaseAgent):
    """Skill de sentinela político-fiscal de emergência.

    Monitora manchetes de Brasília, risco fiscal e eventos de cauda (Black Swan).
    Retorna EMERGENCY_HALT imediato diante de notícia crítica.
    """

    def __init__(self, lockout_duration_minutes: int = 30):
        super().__init__(name="sentinela-politico-emergencia")
        self.lockout_duration_minutes = lockout_duration_minutes
        self.news_history: List[Dict[str, Any]] = []

        self.black_swan_keywords = [
            "meta fiscal",
            "alteracao da meta",
            "estatizacao",
            "intervencao na petrobras",
            "intervencao na vale",
            "demissao de ministro",
            "demissao de campos neto",
            "demissao do presidente do bc",
            "crise institucional",
            "calote",
            "rombo fiscal",
            "contingenciamento bilionario",
            "estado de calamidade",
            "impeachment",
        ]

        self.active_black_swan: Optional[Dict[str, Any]] = None

    def inject_news(
        self,
        text: str,
        source: str = "Feed_Noticias",
        timestamp: Optional[datetime] = None,
    ):
        ts = timestamp or datetime.now()
        t_lower = text.lower()
        is_black_swan = any(kw in t_lower for kw in self.black_swan_keywords)

        item = {
            "timestamp": ts,
            "text": text,
            "source": source,
            "is_black_swan": is_black_swan,
        }
        self.news_history.append(item)

        if is_black_swan:
            self.active_black_swan = {
                "triggered_at": ts,
                "text": text,
                "source": source,
                "expires_at": ts + timedelta(minutes=self.lockout_duration_minutes),
            }

    def clear_black_swan(self):
        self.active_black_swan = None

    def evaluate(self, current_time: Optional[datetime] = None) -> AgentOpinion:
        now = current_time or datetime.now()

        if self.active_black_swan:
            if now < self.active_black_swan["expires_at"]:
                opinion = AgentOpinion(
                    agent_name=self.name,
                    bias="LOCKOUT",
                    confidence=1.0,
                    lockout=True,
                    veto_buy=True,
                    veto_sell=True,
                    reason=(
                        f"BLACK SWAN FISCAL/POLÍTICO: "
                        f"{self.active_black_swan['text']} "
                        f"[{self.active_black_swan['source']}]. "
                        f"Trava até {self.active_black_swan['expires_at'].strftime('%H:%M:%S')}."
                    ),
                    metadata={"news": self.active_black_swan},
                )
                self.last_opinion = opinion
                return opinion
            else:
                self.active_black_swan = None

        opinion = AgentOpinion(
            agent_name=self.name,
            bias="NEUTRAL",
            confidence=0.85,
            veto_buy=False,
            veto_sell=False,
            lockout=False,
            reason="Radar de notícias estável. Nenhum choque político ou fiscal detectado.",
            metadata={"last_news_count": len(self.news_history)},
        )
        self.last_opinion = opinion
        return opinion

    def to_json_contract(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        ts = now or datetime.now()
        opinion = self.evaluate(ts)

        if opinion.lockout:
            status = "EMERGENCY_HALT"
        else:
            status = "ALLOW"

        return {
            "skill": self.name,
            "timestamp_brt": ts.strftime("%Y-%m-%dT%H:%M:%S-03:00"),
            "status": status,
            "motivo": opinion.reason or "Sem restrições identificadas.",
            "dados_stale": False,
        }
