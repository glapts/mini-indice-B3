"""
analysis/book_analyzer.py
Módulo de análise do Livro de Ofertas (Book L2 / Profundidade).
Identifica comportamentos de liquidez passiva, persistência e padrões compatíveis com possível blefe.
Estritamente descritivo: NUNCA emite 'spoofing confirmado' e declara limitações de dados.
"""

from typing import List, Dict, Optional, Tuple, Deque
from collections import deque
from datetime import datetime, timedelta
import numpy as np

from core.models import BookSnapshot, BookLevel, BookEvent


class BookAnalyzer:
    """
    Analisa a dinâmica de profundidade e eventos de ofertas.
    Registra tamanho relativo, concentração, cancelamentos e reposições.
    """

    def __init__(self, depth_levels: int = 10):
        self.depth_levels = depth_levels
        self.snapshots_history: Deque[BookSnapshot] = deque(maxlen=1000)
        self.events_history: Deque[BookEvent] = deque(maxlen=5000)
        
        # Histórico de ofertas em monitoramento por nível de preço
        self.price_level_tracker: Dict[float, Dict[str, any]] = {}

    def update_snapshot(self, snapshot: BookSnapshot):
        """Atualiza com um novo snapshot do livro."""
        self.snapshots_history.append(snapshot)
        self._analyze_snapshot_levels(snapshot)

    def add_event(self, event: BookEvent):
        """Registra evento atômico de inserção, alteração ou cancelamento."""
        self.events_history.append(event)

    def _analyze_snapshot_levels(self, snapshot: BookSnapshot):
        """Avalia concentração de liquidez nos melhores níveis."""
        if not snapshot.bids or not snapshot.asks:
            return

        # Calcular média de quantidade por nível nos 5 primeiros níveis
        bid_qtys = [lvl.quantity for lvl in snapshot.bids[:5]]
        ask_qtys = [lvl.quantity for lvl in snapshot.asks[:5]]
        
        avg_bid = np.mean(bid_qtys) if bid_qtys else 0.0
        avg_ask = np.mean(ask_qtys) if ask_qtys else 0.0
        
        # Registrar níveis com concentração anômala (> 3x a média)
        for lvl in snapshot.bids[:self.depth_levels]:
            if avg_bid > 0 and lvl.quantity >= 3.0 * avg_bid and lvl.quantity >= 150:
                self._track_large_level(lvl.price, lvl.quantity, "BID", snapshot.timestamp)
                
        for lvl in snapshot.asks[:self.depth_levels]:
            if avg_ask > 0 and lvl.quantity >= 3.0 * avg_ask and lvl.quantity >= 150:
                self._track_large_level(lvl.price, lvl.quantity, "ASK", snapshot.timestamp)

    def _track_large_level(self, price: float, quantity: int, side: str, ts: datetime):
        if price not in self.price_level_tracker:
            self.price_level_tracker[price] = {
                "first_seen": ts,
                "last_seen": ts,
                "side": side,
                "max_qty": quantity,
                "times_appeared": 1,
                "times_withdrawn": 0,
                "executed_qty": 0
            }
        else:
            rec = self.price_level_tracker[price]
            rec["last_seen"] = ts
            rec["max_qty"] = max(rec["max_qty"], quantity)
            rec["times_appeared"] += 1

    def evaluate_book_behavior(self, current_price: float) -> Dict[str, any]:
        """
        Retorna o diagnóstico estruturado do Livro conforme exigido no escopo.
        Classificações permitidas:
        - 'Comportamento de oferta observado'
        - 'Padrão compatível com possível blefe'
        - 'Evidência insuficiente'
        - 'Análise indisponível por limitação dos dados'
        """
        if not self.snapshots_history:
            return {
                "status": "Análise indisponível por limitação dos dados",
                "observed_behavior": "Nenhum snapshot de livro recebido até o momento",
                "metrics": {},
                "classification": "Análise indisponível por limitação dos dados",
                "limitations": [
                    "Feed de profundidade de mercado L2 ausente ou não configurado",
                    "Impossível verificar ordens individuais sem identificador estável",
                    "Cancelamentos rápidos não rastreáveis sem eventos atômicos da B3"
                ],
                "alternative_explanations": "Mercado fechado ou feed RTD/DDE fornecendo apenas cotações agregadas de topo."
            }

        latest = self.snapshots_history[-1]
        best_bid = latest.best_bid or 0.0
        best_ask = latest.best_ask or 0.0

        # Calcular desequilibrio (Imbalance) nos primeiros 5 niveis.
        # O feed DDE do Profit expoe apenas o TOPO do livro (nivel 1). Quando
        # menos de 5 niveis estao disponiveis, a metrica e rotulada honestamente
        # como "top1" e o numero de niveis realmente observados e informado.
        bid_vol_top5 = sum(l.quantity for l in latest.bids[:5])
        ask_vol_top5 = sum(l.quantity for l in latest.asks[:5])
        total_top5 = bid_vol_top5 + ask_vol_top5
        imbalance = ((bid_vol_top5 - ask_vol_top5) / total_top5) if total_top5 > 0 else 0.0

        depth_levels_observed = min(len(latest.bids), len(latest.asks))
        is_full_depth = depth_levels_observed >= 5
        imbalance_label = "book_imbalance_top5" if is_full_depth else "book_imbalance_top1"
        imbalance_depth = 5 if is_full_depth else max(1, depth_levels_observed)

        # Verificar se houve grandes ofertas retiradas repetidamente
        suspicious_patterns = []
        for price, rec in list(self.price_level_tracker.items()):
            # Se a oferta sumiu do snapshot recente mas foi vista anteriormente
            is_currently_present = any(l.price == price for l in (latest.bids + latest.asks))
            if not is_currently_present:
                dist_pts = abs(price - current_price)
                duration_sec = (rec["last_seen"] - rec["first_seen"]).total_seconds()

                # Se era uma grande oferta (> 200 contratos), durou pouco tempo (< 10 segundos)
                # e sumiu quando o preço se aproximou (< 20 pontos)
                if rec["max_qty"] >= 200 and duration_sec < 10.0 and dist_pts <= 25.0:
                    suspicious_patterns.append({
                        "price": price,
                        "side": rec["side"],
                        "max_qty": rec["max_qty"],
                        "duration_sec": duration_sec,
                        "distance_when_pulled": dist_pts
                    })

        metrics = {
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread": latest.spread,
            "bid_volume_top5": bid_vol_top5,
            "ask_volume_top5": ask_vol_top5,
            imbalance_label: round(imbalance, 3),
            "book_imbalance": round(imbalance, 3),
            "book_depth_levels": depth_levels_observed,
            "book_imbalance_depth": imbalance_depth,
            "suspicious_patterns_count": len(suspicious_patterns),
            "suspicious_events": suspicious_patterns
        }

        if suspicious_patterns:
            classification = "Padrão compatível com possível blefe"
            observed = f"Retirada rápida de grandes volumes ({suspicious_patterns[0]['max_qty']} contratos) no nível {suspicious_patterns[0]['price']} quando o preço se aproximou."
            alt_exp = "Algoritmo de market making reposicionando lote dinamicamente ou execução parcial não identificada."
        elif abs(imbalance) >= 0.4:
            classification = "Comportamento de oferta observado"
            side_str = "compradora" if imbalance > 0 else "vendedora"
            observed = f"Forte concentração de liquidez {side_str} no topo do livro (Imbalance: {imbalance:+.2f})."
            alt_exp = "Pressão de liquidez natural ou barreira defensiva de participantes passivos."
        else:
            classification = "Evidência insuficiente"
            observed = "Livro distribuído sem concentração fora do padrão recente."
            alt_exp = "Distribuição usual de liquidez sem anomalias observáveis."

        return {
            "status": classification,
            "observed_behavior": observed,
            "metrics": metrics,
            "classification": classification,
            "limitations": [
                "Ausência de identificador único de ordem (GUID) na camada pública de dados",
                "Remoção de oferta não comprova cancelamento deliberado (pode ser execução ou reposicionamento de risco)",
                "Agentes iguais nas corretoras não comprovam mesmo investidor final",
                "Nunca afirmar 'spoofing confirmado' com base apenas em dados do feed público",
                (
                    "Feed DDE expõe apenas o TOPO do livro (nível 1); imbalance medido em 1 nível, não em 5"
                    if not is_full_depth
                    else "Livro completo com 5 níveis observados"
                )
            ],
            "alternative_explanations": alt_exp
        }
