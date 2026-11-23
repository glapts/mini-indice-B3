"""
run_orchestrator.py
Serviço Daemon do Comitê Multi-Agente & Orquestrador de Mesa.
Roda em segundo plano, consolida os pareceres dos 3 agentes especialistas
(Macro, Cesta/DI e Sentinela) e atualiza 'data/runtime_state.json' a cada ciclo.
Alimenta os agentes em tempo real via DDE do Profit Pro (PETR4, VALE3, ITUB4, DI1F29, WSPZ26).
"""

import os
import sys
import time
import argparse
from datetime import datetime
from typing import Optional
import ctypes
from ctypes import wintypes

# Garante path do projeto
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, base_dir)

from core.agents.macro_agent import MacroAgent
from core.agents.basket_agent import BasketAgent
from core.agents.sentinel_agent import SentinelAgent
from core.agents.orchestrator import Orchestrator
from core.harness.contracts import ExecutionMode


class ProfitDDEPoller:
    """Poller DDE assíncrono para captura dos percentuais da Cesta e Macro do Profit Pro."""
    def __init__(self, service: str = "profitchart", topic: str = "cot"):
        self.service = service
        self.topic = topic
        self.user32 = ctypes.windll.user32
        self.CP_WINUNICODE = 1200
        self.XTYP_REQUEST = 0x00B0 | 0x2000
        self.CF_TEXT = 1
        self.id_inst = wintypes.DWORD(0)
        self.cb_func = None
        self.initialized = False
        self._init_dde()

    def _init_dde(self):
        try:
            WINSTA_ALL = 0x37F
            DESKTOP_ALL = 0x1FF
            hwinsta = self.user32.OpenWindowStationW("winsta0", False, WINSTA_ALL)
            if hwinsta:
                self.user32.SetProcessWindowStation(hwinsta)
            hdesk = self.user32.OpenDesktopW("default", 0, False, DESKTOP_ALL)
            if hdesk:
                self.user32.SetThreadDesktop(hdesk)

            PFNCALLBACK = ctypes.WINFUNCTYPE(ctypes.c_void_p, wintypes.UINT, wintypes.UINT, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
            self.cb_func = PFNCALLBACK(lambda *args: 0)
            res = self.user32.DdeInitializeW(ctypes.byref(self.id_inst), self.cb_func, 0, 0)
            self.initialized = (res == 0)
        except Exception:
            self.initialized = False

    def query(self, item_name: str) -> Optional[str]:
        if not self.initialized:
            return None
        try:
            hsz_srv = self.user32.DdeCreateStringHandleW(self.id_inst.value, self.service, self.CP_WINUNICODE)
            hsz_top = self.user32.DdeCreateStringHandleW(self.id_inst.value, self.topic, self.CP_WINUNICODE)
            hconv = self.user32.DdeConnect(self.id_inst.value, hsz_srv, hsz_top, None)
            val = None
            if hconv:
                hsz_item = self.user32.DdeCreateStringHandleW(self.id_inst.value, item_name, self.CP_WINUNICODE)
                pdw_res = wintypes.DWORD(0)
                hdata = self.user32.DdeClientTransaction(
                    None, 0, hconv, hsz_item, self.CF_TEXT, self.XTYP_REQUEST, 1000, ctypes.byref(pdw_res)
                )
                if hdata:
                    size = self.user32.DdeGetData(hdata, None, 0, 0)
                    if size > 0:
                        buf = ctypes.create_string_buffer(size)
                        self.user32.DdeGetData(hdata, buf, size, 0)
                        val = buf.value.decode('latin-1', errors='replace').strip()
                    self.user32.DdeFreeDataHandle(hdata)
                self.user32.DdeFreeStringHandle(self.id_inst.value, hsz_item)
                self.user32.DdeDisconnect(hconv)
            self.user32.DdeFreeStringHandle(self.id_inst.value, hsz_srv)
            self.user32.DdeFreeStringHandle(self.id_inst.value, hsz_top)
            return val
        except Exception:
            return None


def poll_profit_feed(poller: ProfitDDEPoller, basket: BasketAgent, macro: MacroAgent):
    """Lê variações percentuais em tempo real e atualiza os agentes."""
    def parse_pct(val_str: Optional[str]) -> Optional[float]:
        if not val_str:
            return None
        try:
            clean = val_str.replace('%', '').replace('+', '').replace('.', '').replace(',', '.').strip()
            return float(clean)
        except ValueError:
            return None

    # Blue Chips da Cesta
    for stock in ["VALE3", "PETR4", "ITUB4"]:
        raw = poller.query(f"{stock}.VAR")
        pct = parse_pct(raw)
        if pct is not None:
            basket.update_stock(stock, pct)

    # Curva de Juros DI (DI1F29 / DI1F31)
    raw_di29 = poller.query("DI1F29.VAR")
    pct_di29 = parse_pct(raw_di29)
    if pct_di29 is not None:
        # 1% de variação no DI equivale aprox a 10 bps
        basket.update_di("DI1F29", pct_di29 * 5.0)

    # Macro S&P 500 Futuro
    for sp_sym in ["WSPZ26", "WSP", "ISPZ26", "ISP"]:
        raw_sp = poller.query(f"{sp_sym}.VAR")
        raw_sp_ult = poller.query(f"{sp_sym}.ULT")
        pct_sp = parse_pct(raw_sp)
        ult_sp = parse_pct(raw_sp_ult)
        if pct_sp is not None:
            macro.update_sp500(price=ult_sp or 6000.0, change_pct=pct_sp)
            break


def main():
    parser = argparse.ArgumentParser(description="Daemon do Comitê de Agentes e Orquestrador")
    parser.add_argument("--interval", type=int, default=10, help="Intervalo em segundos entre ciclos (padrão: 10s)")
    parser.add_argument("--mode", type=str, choices=["COPILOT", "FULL_AUTO"], default="COPILOT", help="Modo operacional")
    args = parser.parse_args()

    print("=" * 80)
    print("🧠 INICIANDO COMITÊ MULTI-AGENTE & ORQUESTRADOR DE MESA (ASSÍNCRONO)")
    print("=" * 80)
    print(" Agentes Ativos:")
    print("   1. Macro & Global (S&P 500, Treasuries, DXY, Calendário EUA)")
    print("   2. Cesta IBOV & Arbitragem (PETR4, VALE3, Bancos, Curva DI)")
    print("   3. Sentinela Político (Notícias de Brasília, Risco Fiscal, Black Swan)")
    print(f" Destino de Estado : data/runtime_state.json")
    print(f" Intervalo do Loop : {args.interval}s")
    print(f" Modo Configurado  : {args.mode}")
    print("=" * 80)

    macro = MacroAgent()
    basket = BasketAgent()
    sentinel = SentinelAgent()
    poller = ProfitDDEPoller()

    orchestrator = Orchestrator(
        macro_agent=macro,
        basket_agent=basket,
        sentinel_agent=sentinel,
        execution_mode=ExecutionMode(args.mode.upper())
    )

    cycle_count = 0
    try:
        while True:
            cycle_count += 1
            now = datetime.now()
            
            # Atualiza Cesta e Macro via DDE se Profit Pro estiver transmitindo
            poll_profit_feed(poller, basket, macro)
            
            state = orchestrator.run_cycle(current_time=now)
            
            status_symbol = "🟢 OPERAÇÃO LIBERADA" if state.trading_enabled else "🔴 OPERAÇÃO BLOQUEADA"
            opinion_summary = f"Dir: {state.allowed_direction.value} | Confiança: {state.confidence_score*100:.0f}%"
            print(f"[{now.strftime('%H:%M:%S')}] Ciclo #{cycle_count:04d} | {status_symbol} | {opinion_summary}")
            if not state.trading_enabled:
                print("   -> Motivo do Bloqueio: operação desabilitada pelos guardrails.")
            
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n[ORQUESTRADOR] Encerrando serviço a pedido do operador.")


if __name__ == "__main__":
    main()
