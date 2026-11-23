# Skill cesta-juros-veto
# Módulo Python desacoplado da skill de veto de cesta e juros.
# Não altera nenhuma fórmula existente em core/agents/basket_agent.py.
# Consome dados já populados pelo agente existente e emite contrato JSON padronizado.

from datetime import datetime, time
from typing import Dict, Any, Optional

from core.agents.base_agent import BaseAgent, AgentOpinion


class CestaJurosVetoSkill(BaseAgent):
    """Skill de veto de cesta e juros.

    Analisa correlação/divergência da cesta (PETR4, VALE3, Bancos)
    e estresse na curva de juros longa (DI1F29, DI1F31).
    """

    def __init__(self):
        super().__init__(name="cesta-juros-veto")
        self.stocks: Dict[str, float] = {
            "VALE3": 0.0,
            "PETR4": 0.0,
            "ITUB4": 0.0,
            "BBDC4": 0.0,
        }
        self.di_rates: Dict[str, float] = {
            "DI1F27": 0.0,
            "DI1F29": 0.0,
            "DI1F31": 0.0,
        }

    def update_stock(self, ticker: str, change_pct: float):
        t_clean = ticker.upper().strip()
        self.stocks[t_clean] = change_pct

    def update_di(self, contract: str, change_bps: float):
        c_clean = contract.upper().strip()
        self.di_rates[c_clean] = change_bps

    def evaluate(self, current_time: Optional[datetime] = None) -> AgentOpinion:
        now = current_time or datetime.now()
        t = now.time()

        # 1. Mercado à vista fechado (09:00-10:00) -> BLOCK total
        if time(9, 0) <= t < time(10, 0):
            opinion = AgentOpinion(
                agent_name=self.name,
                bias="LOCKOUT",
                confidence=1.0,
                lockout=True,
                veto_buy=True,
                veto_sell=True,
                reason="MERCADO À VISTA FECHADO: Blue Chips em leilão. WIN operando sem formação de preço real.",
                metadata={"time": t.strftime("%H:%M:%S")},
            )
            self.last_opinion = opinion
            return opinion

        veto_buy = False
        veto_sell = False
        reasons: list[str] = []

        # 2. Concentração de Blue Chips
        vale = self.stocks.get("VALE3", 0.0)
        petr = self.stocks.get("PETR4", 0.0)
        itub = self.stocks.get("ITUB4", 0.0)

        if vale < -0.80 and petr < -0.80:
            veto_buy = True
            reasons.append(
                f"VETO BLUE CHIPS: VALE3 ({vale:+.2f}%) e PETR4 ({petr:+.2f}%) em queda firme."
            )
        elif vale > 0.80 and petr > 0.80 and itub > 0.50:
            veto_sell = True
            reasons.append(
                f"FORÇA BLUE CHIPS: VALE3 ({vale:+.2f}%) e PETR4 ({petr:+.2f}%) em forte alta."
            )

        # 3. Estresse na Curva de DI
        di_longo = self.di_rates.get("DI1F31", 0.0)
        di_medio = self.di_rates.get("DI1F29", 0.0)

        if di_longo >= 8.0 or di_medio >= 8.0:
            veto_buy = True
            reasons.append(
                f"ESTRESSE CURVA DI: DI longo subindo ({di_longo:+.1f} bps)."
            )
        elif di_longo <= -8.0 and di_medio <= -8.0:
            veto_sell = True
            reasons.append(
                f"ALÍVIO CURVA DI: DI longo em queda ({di_longo:+.1f} bps)."
            )

        # 4. Consolidação do viés
        if veto_buy and veto_sell:
            bias = "LOCKOUT"
            conf = 0.90
        elif veto_buy:
            bias = "BEARISH"
            conf = 0.88
        elif veto_sell:
            bias = "BULLISH"
            conf = 0.88
        else:
            bias = "NEUTRAL"
            conf = 0.75
            reasons.append("Cesta IBOV e Curva DI em equilíbrio.")

        opinion = AgentOpinion(
            agent_name=self.name,
            bias=bias,
            confidence=conf,
            veto_buy=veto_buy,
            veto_sell=veto_sell,
            lockout=bool(veto_buy and veto_sell),
            reason="; ".join(reasons),
            metadata={"stocks": self.stocks.copy(), "di_rates": self.di_rates.copy()},
        )
        self.last_opinion = opinion
        return opinion

    def to_json_contract(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        ts = now or datetime.now()
        opinion = self.evaluate(ts)

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
            "dados_stale": False,
        }
