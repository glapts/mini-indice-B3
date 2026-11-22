"""
core/agents/base_agent.py
Classe base e contrato padrão de parecer para os Agentes Especialistas de Contexto.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional


@dataclass
class AgentOpinion:
    """Parecer estruturado emitido por cada agente especialista."""
    agent_name: str
    bias: str                      # "BULLISH", "BEARISH", "NEUTRAL", "LOCKOUT"
    confidence: float              # 0.0 a 1.0
    veto_buy: bool = False         # Veto explícito de compra
    veto_sell: bool = False        # Veto explícito de venda
    lockout: bool = False          # Trava total de operações
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    # Qualidade dos dados usados pelo parecer. Consumidores que exigem dados
    # recentes devem bloquear quando o valor for STALE ou DEGRADED.
    data_quality: str = "GOOD"


class BaseAgent(ABC):
    """Contrato base de agente assíncrono."""

    def __init__(self, name: str):
        self.name = name
        self.last_opinion: Optional[AgentOpinion] = None

    @abstractmethod
    def evaluate(self, current_time: Optional[datetime] = None) -> AgentOpinion:
        """Executa a análise do agente e devolve um parecer estruturado."""
        pass
