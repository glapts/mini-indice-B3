"""
core/harness/contracts.py
Contratos de dados e esquemas Pydantic v2 do Execution Harness.
Define o modelo de comunicação entre Agentes de IA (Assíncronos) e o Harness (Determinístico).
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


class ExecutionMode(str, Enum):
    """
    Modo operacional do Harness:
      COPILOT   : Emite alertas visuais, sonoros e estruturados no SuperDOM/Console para ação humana.
      FULL_AUTO : Despacha a ordem OCO diretamente na corretora via Profit Pro.
    """
    COPILOT = "COPILOT"
    FULL_AUTO = "FULL_AUTO"


class ZoneType(str, Enum):
    BEARISH = "BEARISH"
    BULLISH = "BULLISH"
    BREAKER = "BREAKER"
    SWEEP_SSL = "SWEEP_SSL"
    SWEEP_BSL = "SWEEP_BSL"
    IFVG_BULLISH = "IFVG_BULLISH"
    IFVG_BEARISH = "IFVG_BEARISH"


class ZoneStatus(str, Enum):
    UNMITIGATED = "UNMITIGATED"
    TESTING_CONTINUATION = "TESTING_CONTINUATION"
    INVERTED_PENDING_RETEST = "INVERTED_PENDING_RETEST"
    TRIGGER_IFVG = "TRIGGER_IFVG"
    EXHAUSTED = "EXHAUSTED"
    INVALIDATED = "INVALIDATED"


class PrimarySetup(str, Enum):
    CONTINUATION_SELL = "CONTINUATION_SELL"
    CONTINUATION_BUY = "CONTINUATION_BUY"
    CONTINUATION_BUY_IF_CONFIRMED = "CONTINUATION_BUY_IF_CONFIRMED"
    INVERSION_SELL = "INVERSION_SELL"
    INVERSION_BUY = "INVERSION_BUY"
    LIQUIDITY_SWEEP_BUY = "LIQUIDITY_SWEEP_BUY"
    LIQUIDITY_SWEEP_SELL = "LIQUIDITY_SWEEP_SELL"


class TradingDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    BOTH = "BOTH"
    LONG_ONLY = "LONG_ONLY"
    SHORT_ONLY = "SHORT_ONLY"
    NONE = "NONE"


class PriceRegime(str, Enum):
    PREMIUM = "PREMIUM"       # Caro (> 50% Equilibrium) -> Vendas favorecidas
    DISCOUNT = "DISCOUNT"     # Barato (< 50% Equilibrium) -> Compras favorecidas
    EQUILIBRIUM = "EQUILIBRIUM" # Em cima do 50% (+/- margem)


class DealingRange(BaseModel):
    """Dealing Range Macro (normalmente extraído do gráfico de 60m)."""
    topo_estrutural: float = Field(..., description="Máxima macro da pernada")
    fundo_estrutural: float = Field(..., description="Mínima macro da pernada")
    equilibrium_50: float = Field(..., description="Ponto médio (50%) = (Topo + Fundo)/2")

    @model_validator(mode="after")
    def validate_equilibrium(self):
        if self.topo_estrutural <= self.fundo_estrutural:
            raise ValueError("topo_estrutural deve ser estritamente maior que fundo_estrutural")
        calculated = round((self.topo_estrutural + self.fundo_estrutural) / 2.0, 2)
        # Se equilibrium_50 não foi fornecido precisamente, corrige automaticamente
        if abs(self.equilibrium_50 - calculated) > 5.0:
            self.equilibrium_50 = calculated
        return self


class FVGZone(BaseModel):
    """Representação de uma zona FVG ou Liquidity Sweep de 60 minutos."""
    id: str
    tipo_original: ZoneType
    top: float
    ce_50: float
    bottom: float
    setup_primario: PrimarySetup
    stop_sugerido_pts: float = 250.0
    alvo_sugerido_pts: float = 400.0
    status: ZoneStatus = ZoneStatus.UNMITIGATED
    inversion_level: Optional[float] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_bounds(self):
        if self.top < self.bottom:
            self.top, self.bottom = self.bottom, self.top
        if not (self.bottom <= self.ce_50 <= self.top):
            self.ce_50 = round((self.top + self.bottom) / 2.0, 2)
        return self


class Niveis60mContract(BaseModel):
    """Contrato JSON gerado pelo Gemini / Analista de 60m."""
    versao_contrato: str = "2.0"
    ativo: str = "WINZ26"
    data_referencia: str
    dealing_range: DealingRange
    zonas_fvg: List[FVGZone] = Field(default_factory=list, alias="zonas_fvg")


class CircuitBreakerState(BaseModel):
    """Estado do Circuit Breaker diário (desabilitado em modo Demo Manual)."""
    enabled: bool = False
    daily_stops_count: int = 0
    max_daily_stops: int = 999
    lockout_active: bool = False


class MacroRegimeState(BaseModel):
    """Parecer do Agente Macro & Global."""
    status: str = "RISK_ON"           # RISK_ON, RISK_OFF, NEUTRAL, EVENT_LOCKOUT
    sp500_bias: str = "BULLISH"       # BULLISH, BEARISH, NEUTRAL
    di_curve_bias: str = "STABLE"     # STABLE, STRESSED, FALLING
    dxy_bias: str = "BEARISH"         # BULLISH, BEARISH, NEUTRAL
    event_lockout: bool = False       # Trava de Payroll, FOMC, CPI
    lockout_reason: Optional[str] = None


class BasketRegimeState(BaseModel):
    """Parecer do Agente de Cesta & Arbitragem ("O Espelho")."""
    synthetic_ibov_alignment: str = "ALIGNED" # ALIGNED, DIVERGENT
    vale3_petr4_status: str = "POSITIVE"      # POSITIVE, NEGATIVE, NEUTRAL


class RuntimeStateContract(BaseModel):
    """Contrato consolidado pelo Orquestrador e injetado no Harness."""
    timestamp: str
    execution_mode: ExecutionMode = ExecutionMode.COPILOT
    trading_enabled: bool = True
    allowed_direction: TradingDirection = TradingDirection.BOTH
    min_fvg_timeframe: int = 15
    risk_mode: str = "NORMAL"
    confidence_score: float = 0.85
    circuit_breaker: CircuitBreakerState = Field(default_factory=CircuitBreakerState)
    macro_regime: MacroRegimeState = Field(default_factory=MacroRegimeState)
    basket_regime: BasketRegimeState = Field(default_factory=BasketRegimeState)
    feed_quality: dict = Field(default_factory=dict)


class TradeSignal(BaseModel):
    """Payload de sinal gerado pelo Harness para Copiloto ou Execução."""
    id: str
    timestamp: str
    ativo: str
    direction: TradingDirection
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_points: float = 250.0
    gain_points: float = 400.0
    rr_ratio: float = 1.60
    zone_id: str
    setup_name: str
    regime: PriceRegime
    confidence_score: float
    execution_mode: ExecutionMode
    institutional_volume_detected: int
    explanation: str
