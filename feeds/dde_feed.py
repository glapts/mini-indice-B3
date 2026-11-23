"""
feeds/dde_feed.py
Conector nativo DDE (Dynamic Data Exchange) para o Nelogica Profit Pro.
Lê as cotações em tempo real do serviço 'profitchart' e tópico 'cot'.
Arquitetura thread-safe: DdeInitialize e DdeConnect executados na mesma thread de polling.
"""

import ctypes
from ctypes import wintypes
import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict

from feeds.base_feed import BaseMarketFeed, FeedHealth
from core.models import Candle, Trade, AggressorSide, BookSnapshot, BookLevel
from core.contract import TZ_BRASILIA, round_to_tick


# DDE Constants
CP_WINUNICODE = 1200
XTYP_REQUEST = 0x00B0 | 0x2000
CF_TEXT = 1
TIMEOUT_MS = 2000

PFNCALLBACK = ctypes.WINFUNCTYPE(
    ctypes.c_void_p, wintypes.UINT, wintypes.UINT, ctypes.c_void_p,
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p
)


class ProfitDDEFeed(BaseMarketFeed):
    """
    Feed oficial DDE do Nelogica Profit Pro.
    Garante que a inicialização e o loop DDEML residam na mesma thread Win32.
    """

    def __init__(self, service_name: str = "profitchart", topic_name: str = "cot"):
        super().__init__(source_name="Nelogica ProfitPro (DDE)")
        self.service_name = service_name
        self.topic_name = topic_name
        
        self.symbol: Optional[str] = None
        self.running: bool = False
        self.worker_thread: Optional[threading.Thread] = None
        
        # Windows API
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        
        # Valores em cache
        self.last_price: float = 0.0
        self.last_open: float = 0.0
        self.last_high: float = 0.0
        self.last_low: float = 0.0

        # Book de ofertas de topo (nível 1) exposto pelo Profit via DDE.
        # Requer os atributos OCP/OVD/VOC/VOV habilitados na janela
        # "Exportar em Tempo Real (RTD/DDE)" do Profit Pro.
        self.last_best_bid: float = 0.0
        self.last_best_ask: float = 0.0
        self.last_bid_qty: int = 0
        self.last_ask_qty: int = 0
        self.contract_lot_size: int = 0
        self._book_stale_since: Optional[datetime] = None

        # Módulo Macro S&P 500 DDE
        self.sp500_symbol: Optional[str] = None
        self.on_sp500_tick_callback = None

    def set_sp500_callback(self, callback):
        """Define callback para recepção de ticks em tempo real do S&P 500."""
        self.on_sp500_tick_callback = callback

    def set_sp500_symbol(self, symbol: str):
        """Define o ticker do S&P 500 a ser monitorado (ex: WSPZ26 ou ISPZ26)."""
        if symbol:
            self.sp500_symbol = symbol.upper().strip()

    def connect(self) -> bool:
        """Marca conexão como pronta para a thread."""
        self.health.connected = True
        return True

    def subscribe_symbol(self, symbol: str) -> bool:
        self.symbol = symbol.upper()
        if not self.running:
            self.running = True
            self.worker_thread = threading.Thread(target=self._worker_thread_run, daemon=True)
            self.worker_thread.start()
        return True

    def _worker_thread_run(self):
        """Thread dedicada que mantém a instância DDE ativa no Windows."""
        # Anexar à desktop interativa
        WINSTA_ALL = 0x37F
        DESKTOP_ALL = 0x1FF
        hwinsta = self.user32.OpenWindowStationW("winsta0", False, WINSTA_ALL)
        if hwinsta:
            self.user32.SetProcessWindowStation(hwinsta)
            hdesk = self.user32.OpenDesktopW("default", 0, False, DESKTOP_ALL)
            if hdesk:
                self.user32.SetThreadDesktop(hdesk)

        def dde_cb(*args):
            return 0

        cb_func = PFNCALLBACK(dde_cb)
        id_inst = wintypes.DWORD(0)
        res = self.user32.DdeInitializeW(ctypes.byref(id_inst), cb_func, 0, 0)
        if res != 0:
            self.health.connected = False
            self.health.error_message = f"DdeInitializeW falhou na thread: {res}"
            return

        hsz_srv = self.user32.DdeCreateStringHandleW(id_inst.value, self.service_name, CP_WINUNICODE)
        hsz_top = self.user32.DdeCreateStringHandleW(id_inst.value, self.topic_name, CP_WINUNICODE)

        # Tentar conectar ao DDE com resiliência a inicialização do Profit Pro
        hconv = None
        while self.running and not hconv:
            hconv = self.user32.DdeConnect(id_inst.value, hsz_srv, hsz_top, None)
            if not hconv:
                err = self.user32.DdeGetLastError(id_inst.value)
                self.health.connected = False
                self.health.error_message = (
                    f"Aguardando transmissão DDE do Profit Pro ('{self.service_name}|{self.topic_name}')..."
                )
                time.sleep(1.5)
            else:
                self.health.connected = True
                self.health.error_message = ""

        if not self.running or not hconv:
            self.user32.DdeFreeStringHandle(id_inst.value, hsz_srv)
            self.user32.DdeFreeStringHandle(id_inst.value, hsz_top)
            self.user32.DdeUninitialize(id_inst.value)
            return

        def query_item(item_name: str) -> Optional[str]:
            hsz_item = self.user32.DdeCreateStringHandleW(id_inst.value, item_name, CP_WINUNICODE)
            pdw_res = wintypes.DWORD(0)
            hdata = self.user32.DdeClientTransaction(
                None, 0, hconv, hsz_item, CF_TEXT, XTYP_REQUEST, TIMEOUT_MS, ctypes.byref(pdw_res)
            )
            val = None
            if hdata:
                size = self.user32.DdeGetData(hdata, None, 0, 0)
                if size > 0:
                    buf = ctypes.create_string_buffer(size)
                    self.user32.DdeGetData(hdata, buf, size, 0)
                    val = buf.value.decode('latin-1', errors='replace').strip()
                self.user32.DdeFreeDataHandle(hdata)
            self.user32.DdeFreeStringHandle(id_inst.value, hsz_item)
            return val

        # Estado de agregação minuto a minuto e Tape Reading incremental
        active_1m_candle: Optional[Candle] = None
        current_minute_tag: Optional[int] = None
        last_vol_c: float = 0.0
        last_vol_v: float = 0.0

        # Mapeamento do S&P 500 para ingestão não-bloqueante
        from core.contract import get_current_sp500_contract
        candidate_sp_symbols = []
        if self.sp500_symbol:
            candidate_sp_symbols.append(self.sp500_symbol)
        wsp_sym = get_current_sp500_contract(prefix="WSP")
        isp_sym = get_current_sp500_contract(prefix="ISP")
        if wsp_sym not in candidate_sp_symbols:
            candidate_sp_symbols.append(wsp_sym)
        if isp_sym not in candidate_sp_symbols:
            candidate_sp_symbols.append(isp_sym)

        active_sp_sym = candidate_sp_symbols[0]
        sp_found = False
        last_sp_probe_time = 0.0

        # Loop contínuo de polling na mesma thread
        while self.running:
            try:
                t0 = time.perf_counter()
                now = datetime.now(TZ_BRASILIA)

                val_str = query_item(f"{self.symbol}.ULT")
                t1 = time.perf_counter()
                self.health.latency_ms = (t1 - t0) * 1000.0
                self.health.last_received_time = now

                # Ingestão S&P 500 em tempo real (zero latência adicional ao WIN)
                t_now = time.time()
                if sp_found or (t_now - last_sp_probe_time >= 15.0):
                    last_sp_probe_time = t_now
                    symbols_to_try = [active_sp_sym] if sp_found else candidate_sp_symbols
                    for cand_sym in symbols_to_try:
                        sp_res = query_item(f"{cand_sym}.ULT")
                        if sp_res:
                            active_sp_sym = cand_sym
                            sp_found = True
                            try:
                                sp_clean = sp_res.replace('.', '').replace(',', '.')
                                sp_price = float(sp_clean)
                                if sp_price > 0 and self.on_sp500_tick_callback:
                                    self.on_sp500_tick_callback(sp_price, now, active_sp_sym)
                            except ValueError:
                                pass
                            break

                if val_str:
                    try:
                        clean_val = val_str.replace('.', '').replace(',', '.')
                        price = float(clean_val)
                        self.last_price = price
                        self.health.last_event_time = now
                        self.health.error_message = ""

                        # Ler métricas de sessão do Profit Pro
                        raw_abe = query_item(f"{self.symbol}.ABE")
                        raw_max = query_item(f"{self.symbol}.MAX")
                        raw_min = query_item(f"{self.symbol}.MIN")
                        raw_neg = query_item(f"{self.symbol}.NEG")
                        # Resiliência de tags de agressão (AGRVOLC / AGRCOMP / AGRC)
                        raw_agr_c = (
                            query_item(f"{self.symbol}.AGRVOLC") or 
                            query_item(f"{self.symbol}.AGRCOMP") or 
                            query_item(f"{self.symbol}.AGRC")
                        )
                        raw_agr_v = (
                            query_item(f"{self.symbol}.AGRVOLV") or 
                            query_item(f"{self.symbol}.AGRVEND") or 
                            query_item(f"{self.symbol}.AGRV")
                        )

                        open_p = float(raw_abe.replace('.', '').replace(',', '.')) if raw_abe else price
                        high_p = float(raw_max.replace('.', '').replace(',', '.')) if raw_max else price
                        low_p = float(raw_min.replace('.', '').replace(',', '.')) if raw_min else price
                        trades_count = int(float(raw_neg.replace('.', '').replace(',', '.'))) if raw_neg else 0
                        vol_c = float(raw_agr_c.replace('.', '').replace(',', '.')) if raw_agr_c else 0.0
                        vol_v = float(raw_agr_v.replace('.', '').replace(',', '.')) if raw_agr_v else 0.0

                        self.last_open = open_p
                        self.last_high = high_p
                        self.last_low = low_p

                        # ─────────────────────────────────────────────
                        # BOOK DE OFERTAS DE TOPO (nível 1) via DDE
                        # Requer OCP/OVD/VOC/VOV habilitados no Profit Pro.
                        # ─────────────────────────────────────────────
                        self._read_top_book(query_item, now, price)

                        # Delta e Tape Reading incremental (sem distorção de acumulação diária)
                        delta_c = 0.0
                        delta_v = 0.0
                        if last_vol_c > 0 and vol_c >= last_vol_c:
                            delta_c = vol_c - last_vol_c
                        if last_vol_v > 0 and vol_v >= last_vol_v:
                            delta_v = vol_v - last_vol_v
                        last_vol_c = vol_c
                        last_vol_v = vol_v

                        if delta_c > 0 or delta_v > 0:
                            self.health.is_flow_available = True
                            if self.on_trade_callback:
                                if delta_c > 0:
                                    self.on_trade_callback(Trade("DDE_BUY", now, price, int(delta_c), AggressorSide.BUY))
                                if delta_v > 0:
                                    self.on_trade_callback(Trade("DDE_SELL", now, price, int(delta_v), AggressorSide.SELL))

                        # Agregação determinística de candles de 1m alinhada ao relógio
                        min_tag = (now.hour * 60) + now.minute
                        if current_minute_tag is None:
                            current_minute_tag = min_tag
                            active_1m_candle = Candle(
                                timeframe=1,
                                open_time=now,
                                close_time=now,
                                open=price,
                                high=price,
                                low=price,
                                close=price,
                                volume=delta_c + delta_v,
                                trades_count=1,
                                buy_volume=delta_c,
                                sell_volume=delta_v,
                                is_closed=False
                            )
                        elif min_tag != current_minute_tag:
                            # O minuto anterior acabou de encerrar -> fechar e despachar barra de 1m (apenas sessão regular >= 09:00)
                            if active_1m_candle is not None:
                                active_1m_candle.is_closed = True
                                active_1m_candle.close_time = now
                                if self.on_candle_callback and active_1m_candle.open_time.hour >= 9:
                                    self.on_candle_callback(active_1m_candle)

                            # Abrir novo candle de 1m para o minuto atual
                            current_minute_tag = min_tag
                            active_1m_candle = Candle(
                                timeframe=1,
                                open_time=now,
                                close_time=now,
                                open=price,
                                high=price,
                                low=price,
                                close=price,
                                volume=delta_c + delta_v,
                                trades_count=1,
                                buy_volume=delta_c,
                                sell_volume=delta_v,
                                is_closed=False
                            )
                        else:
                            # Atualizar candle intrabar de 1m
                            if active_1m_candle is not None:
                                active_1m_candle.high = max(active_1m_candle.high, price)
                                active_1m_candle.low = min(active_1m_candle.low, price)
                                active_1m_candle.close = price
                                active_1m_candle.close_time = now
                                active_1m_candle.volume += (delta_c + delta_v)
                                active_1m_candle.buy_volume += delta_c
                                active_1m_candle.sell_volume += delta_v
                                active_1m_candle.trades_count += 1

                    except ValueError:
                        pass
                else:
                    self.health.error_message = (
                        "Aguardando transmissão do ativo pelo Profit Pro."
                    )

            except Exception as e:
                self.health.error_message = f"Erro no poll DDE: {e}"

            time.sleep(1.0)

        # Encerramento na thread
        self.user32.DdeDisconnect(hconv)
        self.user32.DdeFreeStringHandle(id_inst.value, hsz_srv)
        self.user32.DdeFreeStringHandle(id_inst.value, hsz_top)
        self.user32.DdeUninitialize(id_inst.value)
        self.health.connected = False

    def _query_item(self, item_name: str, timeout_ms: int = 400) -> Optional[str]:
        """Consulta síncrona sob demanda para ferramentas como scan-dde."""
        WINSTA_ALL = 0x37F
        DESKTOP_ALL = 0x1FF
        hwinsta = self.user32.OpenWindowStationW("winsta0", False, WINSTA_ALL)
        if hwinsta:
            self.user32.SetProcessWindowStation(hwinsta)
            hdesk = self.user32.OpenDesktopW("default", 0, False, DESKTOP_ALL)
            if hdesk:
                self.user32.SetThreadDesktop(hdesk)

        # Se chamada fora da thread, cria contexto rápido
        id_inst = wintypes.DWORD(0)
        cb_func = PFNCALLBACK(lambda *args: 0)
        self.user32.DdeInitializeW(ctypes.byref(id_inst), cb_func, 0, 0)
        hsz_srv = self.user32.DdeCreateStringHandleW(id_inst.value, self.service_name, CP_WINUNICODE)
        hsz_top = self.user32.DdeCreateStringHandleW(id_inst.value, self.topic_name, CP_WINUNICODE)
        hconv = self.user32.DdeConnect(id_inst.value, hsz_srv, hsz_top, None)
        val = None
        if hconv:
            hsz_item = self.user32.DdeCreateStringHandleW(id_inst.value, item_name, CP_WINUNICODE)
            pdw_res = wintypes.DWORD(0)
            hdata = self.user32.DdeClientTransaction(
                None, 0, hconv, hsz_item, CF_TEXT, XTYP_REQUEST, timeout_ms, ctypes.byref(pdw_res)
            )
            if hdata:
                size = self.user32.DdeGetData(hdata, None, 0, 0)
                if size > 0:
                    buf = ctypes.create_string_buffer(size)
                    self.user32.DdeGetData(hdata, buf, size, 0)
                    val = buf.value.decode('latin-1', errors='replace').strip()
                self.user32.DdeFreeDataHandle(hdata)
            self.user32.DdeFreeStringHandle(id_inst.value, hsz_item)
            self.user32.DdeDisconnect(hconv)
        self.user32.DdeFreeStringHandle(id_inst.value, hsz_srv)
        self.user32.DdeFreeStringHandle(id_inst.value, hsz_top)
        self.user32.DdeUninitialize(id_inst.value)
        return val

    def disconnect(self):
        self.running = False
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2.0)
        self.health.connected = False

    # ------------------------------------------------------------------
    # BOOK DE OFERTAS DE TOPO (nível 1) via DDE
    # ------------------------------------------------------------------
    def _parse_num(self, raw: Optional[str]) -> Optional[float]:
        """Converte string numérica do Profit (pt-BR) em float."""
        if raw is None:
            return None
        try:
            clean = raw.replace('.', '').replace(',', '.').replace('%', '').strip()
            if not clean:
                return None
            return float(clean)
        except ValueError:
            return None

    def _read_top_book(self, query_item, now: datetime, last_price: float):
        """
        Lê o book de ofertas de topo (nível 1) do Profit via DDE.

        Campos esperados (aba "Atributos" da janela Exportar em Tempo Real):
            OCP -> Melhor oferta de compra (preço)
            OVD -> Melhor oferta de venda (preço)
            VOC -> Volume na oferta de compra
            VOV -> Volume na oferta de venda
            LOT -> Tamanho do lote padrão do contrato

        Sem esses atributos habilitados no Profit, os campos não existem e o
        book permanece indisponível — o motor segue degradando com segurança.
        """
        raw_bid = query_item(f"{self.symbol}.OCP")
        raw_ask = query_item(f"{self.symbol}.OVD")
        raw_bid_qty = query_item(f"{self.symbol}.VOC")
        raw_ask_qty = query_item(f"{self.symbol}.VOV")
        raw_lot = query_item(f"{self.symbol}.LOT")

        if raw_bid is None and raw_ask is None:
            # Atributos de book não habilitados no Profit (ou mercado sem book).
            self.health.is_book_available = False
            self._book_stale_since = self._book_stale_since or now
            return

        bid_price = self._parse_num(raw_bid) or 0.0
        ask_price = self._parse_num(raw_ask) or 0.0
        bid_qty = int(self._parse_num(raw_bid_qty) or 0.0)
        ask_qty = int(self._parse_num(raw_ask_qty) or 0.0)
        lot = int(self._parse_num(raw_lot) or 0.0)
        if lot > 0:
            self.contract_lot_size = lot

        # Mercado fechado produz book zerado. Considera o book válido somente
        # quando há preço de oferta coerente com o último negócio.
        book_valid = (
            bid_price > 0 and ask_price > 0
            and ask_price >= bid_price
            and (bid_qty > 0 or ask_qty > 0)
        )

        if not book_valid:
            self.health.is_book_available = False
            self._book_stale_since = self._book_stale_since or now
            return

        self.last_best_bid = bid_price
        self.last_best_ask = ask_price
        self.last_bid_qty = bid_qty
        self.last_ask_qty = ask_qty
        self.health.is_book_available = True
        self._book_stale_since = None

        # Normaliza as quantidades para contratos, respeitando o lote padrão.
        lot_size = self.contract_lot_size if self.contract_lot_size > 0 else 1
        bids = [BookLevel(price=bid_price, quantity=max(1, bid_qty // lot_size))]
        asks = [BookLevel(price=ask_price, quantity=max(1, ask_qty // lot_size))]

        if self.on_book_callback:
            self.on_book_callback(BookSnapshot(timestamp=now, bids=bids, asks=asks))

    def get_top_book(self) -> Optional[Dict[str, float]]:
        """Retorna o snapshot do book de topo em cache (ou None se indisponivel)."""
        if not self.health.is_book_available:
            return None
        return {
            "best_bid": self.last_best_bid,
            "best_ask": self.last_best_ask,
            "bid_quantity": self.last_bid_qty,
            "ask_quantity": self.last_ask_qty,
            "contract_lot_size": self.contract_lot_size,
        }
