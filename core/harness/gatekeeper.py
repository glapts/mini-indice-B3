"""
core/harness/gatekeeper.py
Guardião Determinístico de Regras Rígidas (Gatekeeper).
Responsável por:
  1. Filtro Premium & Discount (Dealing Range 50% Equilibrium)
  2. Trava física de horário (09h00 às 10h00 - Modo OBSERVATION_ONLY)
  3. Trava de abertura de Nova York (10h28–10h35 / 11h28–11h35)
  4. Circuit Breakers diários (Limite de 2 stops no dia)
  5. Blackout Macro e Alertas Políticos (Black Swan)
"""

from datetime import datetime, time
from typing import Tuple, Optional
from core.harness.contracts import (
    DealingRange,
    PriceRegime,
    TradingDirection,
    RuntimeStateContract
)


class HarnessGatekeeper:
    def __init__(self, dealing_range: DealingRange, runtime_state: Optional[RuntimeStateContract] = None):
        self.dealing_range = dealing_range
        self.runtime_state = runtime_state

    def update_dealing_range(self, new_range: DealingRange):
        self.dealing_range = new_range

    def update_runtime_state(self, new_state: RuntimeStateContract):
        self.runtime_state = new_state

    def get_price_regime(self, price: float) -> PriceRegime:
        """Determina se o preço atual está em zona Premium, Discount ou Equilibrium."""
        diff = price - self.dealing_range.equilibrium_50
        # Margem de tolerância para o equilíbrio puro: 50 pontos
        if abs(diff) <= 50.0:
            return PriceRegime.EQUILIBRIUM
        elif diff > 50.0:
            return PriceRegime.PREMIUM
        else:
            return PriceRegime.DISCOUNT

    def evaluate_entry_permission(
        self,
        current_time: datetime,
        current_price: float,
        proposed_direction: TradingDirection,
        is_continuation: bool = True,
        is_structural_break: bool = False
    ) -> Tuple[bool, str]:
        """
        Avalia se uma entrada proposta é rigorosamente permitida.
        Retorna (autorizado: bool, motivo: str).
        """
        # 1. Trava Geral do Orquestrador
        if self.runtime_state:
            if not self.runtime_state.trading_enabled:
                return False, "SISTEMA BLOQUEADO: trading_enabled está desativado pelo Orquestrador."
            
            # Direção permitida
            if self.runtime_state.allowed_direction == TradingDirection.NONE:
                return False, "BLOQUEIO DE DIREÇÃO: Orquestrador bloqueou todas as operações (NONE)."
            if self.runtime_state.allowed_direction == TradingDirection.LONG_ONLY and proposed_direction != TradingDirection.LONG:
                return False, "BLOQUEIO DE DIREÇÃO: Orquestrador autorizou apenas COMPRAS (LONG_ONLY)."
            if self.runtime_state.allowed_direction == TradingDirection.SHORT_ONLY and proposed_direction != TradingDirection.SHORT:
                return False, "BLOQUEIO DE DIREÇÃO: Orquestrador autorizou apenas VENDAS (SHORT_ONLY)."

            # 2. Circuit Breaker de Stops Diários (Desabilitado em Modo Demo Manual)
            cb = self.runtime_state.circuit_breaker
            if getattr(cb, "enabled", False):
                if cb.lockout_active:
                    return False, f"CIRCUIT BREAKER ATIVO: Limite diário de {cb.max_daily_stops} stops atingido."
                if cb.daily_stops_count >= cb.max_daily_stops:
                    return False, f"CIRCUIT BREAKER DISPARADO: {cb.daily_stops_count} stops registrados hoje."

            # 3. Blackout Macro e Eventos Críticos (P7 e P8)
            if self.runtime_state.macro_regime.event_lockout:
                reason = self.runtime_state.macro_regime.lockout_reason or "Evento Macro de Alto Impacto"
                return False, f"EVENT LOCKOUT ATIVO: {reason}"

        # 4. Trava de Horário Rígida: 09h00 às 10h00 (P4 - Abertura no Escuro)
        t = current_time.time()
        if time(9, 0) <= t < time(10, 0):
            return False, "TRAVA DE HORÁRIO (09:00 - 10:00): Modo OBSERVATION_ONLY ativo enquanto mercado à vista está em leilão."

        # 5. Trava de Horário: Abertura de Nova York (P11 - Fakeouts de NY)
        # Janela 1: 10h28 às 10h35 (quando NY abre 10h30)
        if time(10, 28) <= t <= time(10, 35):
            return False, "TRAVA ABERTURA NY (10:28 - 10:35): Volume anormal e fakeouts de abertura da NYSE."
        # Janela 2: 11h28 às 11h35 (quando NY abre 11h30 no horário de verão)
        if time(11, 28) <= t <= time(11, 35):
            return False, "TRAVA ABERTURA NY (11:28 - 11:35): Volume anormal e fakeouts de abertura da NYSE."

        # 6. Regra de Ouro SMC: Quebra de Estrutura (BOS) vs Premium & Discount (P10)
        # Se for um Rompimento Estrutural Institucional (BOS - Break of Structure no 5m/60m):
        # A venda no reteste de um suporte rompido é autorizada pela confirmação da quebra do nível
        if is_structural_break:
            if proposed_direction == TradingDirection.SHORT:
                return True, f"AUTORIZADO: Quebra de Estrutura (BOS) confirmada. Reteste de resistência em {current_price:.0f}."
            elif proposed_direction == TradingDirection.LONG:
                return True, f"AUTORIZADO: Quebra de Estrutura (BOS) de alta confirmada. Apoio em suporte em {current_price:.0f}."

        regime = self.get_price_regime(current_price)

        if is_continuation:
            # Em continuação:
            # - Comprar em Premium (>50%) é comprar topo esticado -> VETADO
            # - Vender em Discount (<50%) é vender fundo esticado -> VETADO
            if proposed_direction == TradingDirection.LONG and regime == PriceRegime.PREMIUM:
                return False, f"VETO PREMIUM & DISCOUNT: Preço ({current_price:.0f}) está em Zona PREMIUM (> 50% Equilibrium: {self.dealing_range.equilibrium_50:.0f}). Proibido comprar topo esticado por continuidade."
            
            if proposed_direction == TradingDirection.SHORT and regime == PriceRegime.DISCOUNT:
                return False, f"VETO PREMIUM & DISCOUNT: Preço ({current_price:.0f}) está em Zona DISCOUNT (< 50% Equilibrium: {self.dealing_range.equilibrium_50:.0f}). Proibido vender fundo esticado por continuidade."
        else:
            # Setup de Inversão (iFVG / Sweep):
            # iFVG de alta no fundo (rompeu FVG de baixa para cima) é permitido em Discount
            # iFVG de baixa no topo (rompeu FVG de alta para baixo) é permitido em Premium
            if proposed_direction == TradingDirection.LONG and regime == PriceRegime.PREMIUM:
                return False, f"VETO INVERSÃO: Preço ({current_price:.0f}) está em Zona PREMIUM. Compras por inversão exigem confirmação em Discount ou rompimento do topo."
            if proposed_direction == TradingDirection.SHORT and regime == PriceRegime.DISCOUNT:
                return False, f"VETO INVERSÃO: Preço ({current_price:.0f}) está em Zona DISCOUNT. Vendas por inversão exigem confirmação em Premium ou rompimento do fundo."

        return True, "AUTORIZADO: Todos os guardrails e regras de Premium & Discount foram validados."
