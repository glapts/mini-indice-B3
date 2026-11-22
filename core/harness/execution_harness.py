"""
core/harness/execution_harness.py
Motor Central do Execution Harness Determinístico.
Opera nos modos:
  - COPILOT   : Emite alertas sonoros, visuais e estruturados (Recomendado para início).
  - FULL_AUTO : Despacha ordens OCO diretamente via ProfitDLL (Fase 2 / Futuro).
"""

import os
import json
import uuid
import winsound
from datetime import datetime
from typing import Optional, List, Dict, Any

from core.harness.contracts import (
    ExecutionMode,
    Niveis60mContract,
    RuntimeStateContract,
    TradeSignal,
    TradingDirection,
    PriceRegime,
    ZoneStatus,
    ZoneType
)
from core.harness.gatekeeper import HarnessGatekeeper
from core.harness.microstructure_filter import MicrostructureFilter
from core.harness.state_machine import FVGStateMachine


class ExecutionHarness:
    def __init__(
        self,
        niveis_contract: Niveis60mContract,
        runtime_state: Optional[RuntimeStateContract] = None,
        mode: ExecutionMode = ExecutionMode.COPILOT,
        signals_output_path: str = "data/sinais_copiloto.json"
    ):
        self.niveis = niveis_contract
        self.mode = mode
        self.signals_output_path = signals_output_path
        
        # Componentes do Harness
        self.gatekeeper = HarnessGatekeeper(
            dealing_range=self.niveis.dealing_range,
            runtime_state=runtime_state
        )
        self.microstructure = MicrostructureFilter(
            min_hft_lot=20,
            min_institutional_absorption=100
        )
        self.state_machine = FVGStateMachine(
            zones=self.niveis.zonas_fvg
        )

        self.last_signal: Optional[TradeSignal] = None
        self.generated_signals: List[TradeSignal] = []

    def set_execution_mode(self, mode: ExecutionMode):
        self.mode = mode
        print(f"[HARNESS] Modo operacional alterado para: {self.mode.value}")

    def on_tick(self, price: float, timestamp: datetime) -> Optional[TradeSignal]:
        """
        Processa cada tick de preço do ativo.
        """
        # 1. Atualiza máquina de estados das zonas
        events = self.state_machine.evaluate_price_tick(price, timestamp)
        
        # 2. Avalia se alguma zona em teste ou gatilho cumpre os requisitos
        for zone in self.state_machine.get_active_zones():
            if zone.status in (ZoneStatus.TESTING_CONTINUATION, ZoneStatus.TRIGGER_IFVG):
                inside_zone = (zone.bottom <= price <= zone.top)
                if not inside_zone:
                    continue

                # Determina direção proposta
                is_continuation = (zone.status == ZoneStatus.TESTING_CONTINUATION)
                
                if is_continuation:
                    if zone.tipo_original in (ZoneType.BEARISH, ZoneType.BREAKER):
                        proposed_dir = TradingDirection.SHORT
                        expected_defense = "SELL_DEFENSE"
                    elif zone.tipo_original in (ZoneType.BULLISH, ZoneType.SWEEP_SSL):
                        proposed_dir = TradingDirection.LONG
                        expected_defense = "BUY_DEFENSE"
                    else:
                        continue
                else: # TRIGGER_IFVG
                    # Inversão: o que era venda virou compra, e vice-versa
                    if zone.tipo_original == ZoneType.BEARISH:
                        proposed_dir = TradingDirection.LONG
                        expected_defense = "BUY_DEFENSE"
                    else:
                        proposed_dir = TradingDirection.SHORT
                        expected_defense = "SELL_DEFENSE"

                # Gatekeeper: Valida regras rígidas (Premium/Discount, horários, circuit breaker)
                allowed, gate_msg = self.gatekeeper.evaluate_entry_permission(
                    current_time=timestamp,
                    current_price=price,
                    proposed_direction=proposed_dir,
                    is_continuation=is_continuation
                )
                if not allowed:
                    continue

                # Microestrutura: Valida absorção institucional real (>= 100 contratos)
                absorbed, vol_detected, abs_msg = self.microstructure.evaluate_absorption(
                    target_price=price,
                    expected_defense=expected_defense,
                    tolerance_pts=80.0
                )
                if not absorbed:
                    continue

                # Se todos os filtros passaram, gera o TradeSignal
                signal = self._emit_signal(
                    zone=zone,
                    direction=proposed_dir,
                    entry_price=price,
                    timestamp=timestamp,
                    institutional_volume=vol_detected,
                    is_continuation=is_continuation
                )
                return signal

        return None

    def on_trade(self, price: float, qty: int, aggressor: str, timestamp: datetime) -> Dict[str, Any]:
        """Alimenta o feed do Times & Trades no filtro de microestrutura."""
        return self.microstructure.on_trade(price, qty, aggressor, timestamp)

    def on_candle_closed(self, timeframe: int, open_p: float, high_p: float, low_p: float, close_p: float, timestamp: datetime):
        """Atualiza quebras de estrutura e transições de iFVG."""
        return self.state_machine.on_candle_closed(timeframe, open_p, high_p, low_p, close_p, timestamp)

    def _emit_signal(
        self,
        zone: Any,
        direction: TradingDirection,
        entry_price: float,
        timestamp: datetime,
        institutional_volume: int,
        is_continuation: bool
    ) -> TradeSignal:
        """Gera o sinal determinístico e trata conforme o modo (COPILOT vs FULL_AUTO)."""
        stop_pts = zone.stop_sugerido_pts
        gain_pts = zone.alvo_sugerido_pts
        
        if direction == TradingDirection.LONG:
            stop_loss = entry_price - stop_pts
            take_profit = entry_price + gain_pts
        else:
            stop_loss = entry_price + stop_pts
            take_profit = entry_price - gain_pts

        regime = self.gatekeeper.get_price_regime(entry_price)
        conf_score = self.gatekeeper.runtime_state.confidence_score if self.gatekeeper.runtime_state else 0.85
        setup_type = "CONTINUIDADE FVG" if is_continuation else "INVERSÃO iFVG"

        signal = TradeSignal(
            id=f"SIG_{uuid.uuid4().hex[:8].upper()}",
            timestamp=timestamp.isoformat(),
            ativo=self.niveis.ativo,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_points=stop_pts,
            gain_points=gain_pts,
            rr_ratio=round(gain_pts / stop_pts, 2),
            zone_id=zone.id,
            setup_name=f"{setup_type} ({zone.id})",
            regime=regime,
            confidence_score=conf_score,
            execution_mode=self.mode,
            institutional_volume_detected=institutional_volume,
            explanation=(
                f"Entrada de {direction.value} em {entry_price:.0f}. "
                f"Regime: {regime.value} (50% Eq: {self.niveis.dealing_range.equilibrium_50:.0f}). "
                f"Absorção de {institutional_volume} contratos confirmada na defesa."
            )
        )

        self.last_signal = signal
        self.generated_signals.append(signal)

        # Persiste antes de qualquer alerta/dispatch externo. Assim uma falha de
        # auditoria não produz um efeito observável que possa ser repetido.
        try:
            persisted = self._persist_signals()
        except Exception:
            persisted = False
        if not persisted:
            self.generated_signals.pop()
            self.last_signal = self.generated_signals[-1] if self.generated_signals else None
            raise IOError("Falha ao persistir sinal; operação não confirmada")

        # Trata conforme o modo configurado
        if self.mode == ExecutionMode.COPILOT:
            self._handle_copilot_alert(signal)
        elif self.mode == ExecutionMode.FULL_AUTO:
            self._handle_full_auto_dispatch(signal)

        # Marca a zona como em execução para não duplicar entradas no mesmo candle
        zone.status = ZoneStatus.EXHAUSTED

        return signal

    def _handle_copilot_alert(self, signal: TradeSignal):
        """Modo Copiloto: Apresenta cartão visual rico e toca alerta sonoro de alta atenção."""
        color = "\033[92m" if signal.direction == TradingDirection.LONG else "\033[91m"
        reset = "\033[0m"
        bold = "\033[1m"

        card = f"""
{color}{bold}╔════════════════════════════════════════════════════════════════════════════════════════╗
║                     🎯 ALERTA COPILOTO: SINAL DE ENTRADA ARMADO                        ║
╠════════════════════════════════════════════════════════════════════════════════════════╣{reset}
  Ativo            : {bold}{signal.ativo}{reset}
  Direção Sugerida : {color}{bold}{signal.direction.value}{reset}
  Preço de Entrada : {bold}{signal.entry_price:.0f}{reset}
  Stop Loss        : {bold}{signal.stop_loss:.0f} (-{signal.risk_points:.0f} pts){reset}
  Alvo (Take)      : {bold}{signal.take_profit:.0f} (+{signal.gain_points:.0f} pts){reset}
  Relação R:R      : {bold}{signal.rr_ratio:.2f}{reset}
  Regime SMC       : {bold}{signal.regime.value}{reset} (50% Eq: {self.niveis.dealing_range.equilibrium_50:.0f})
  Zona de 60m      : {signal.zone_id} ({signal.setup_name})
  Absorção Tape    : {bold}{signal.institutional_volume_detected} contratos institucionais{reset}
  Score Confiança  : {bold}{signal.confidence_score * 100:.0f}%{reset}
  Ação do Trader   : {bold}Posicione ou confirme a ordem no SuperDOM do Profit Pro{reset}
{color}{bold}╚════════════════════════════════════════════════════════════════════════════════════════╝{reset}
"""
        print(card)

        # Emite beeps sonoros diferenciados (agudo para compra, grave para venda)
        try:
            if signal.direction == TradingDirection.LONG:
                winsound.Beep(1200, 150)
                winsound.Beep(1500, 200)
            else:
                winsound.Beep(800, 150)
                winsound.Beep(600, 200)
        except Exception:
            pass

    def _handle_full_auto_dispatch(self, signal: TradeSignal):
        """Modo Full-Auto (Futuro): Envia a ordem OCO diretamente na corretora."""
        print(f"\n[FULL_AUTO] DISPARANDO ORDEM OCO VIA PROFIT PRO:")
        print(f"  -> {signal.direction.value} @ {signal.entry_price:.0f} | Stop: {signal.stop_loss:.0f} | Alvo: {signal.take_profit:.0f}")
        # Hook para envio via ProfitDLL ou bridge de automação

    def _persist_signals(self) -> bool:
        """Grava histórico de sinais em JSON e informa se confirmou a gravação."""
        try:
            os.makedirs(os.path.dirname(self.signals_output_path) or ".", exist_ok=True)
            with open(self.signals_output_path, "w", encoding="utf-8") as f:
                json.dump([s.model_dump() for s in self.generated_signals], f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[HARNESS WARN] Falha ao persistir sinais: {e}")
            return False
