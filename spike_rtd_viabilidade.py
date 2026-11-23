"""
spike_rtd_viabilidade.py

SPIKE DE VIABILIDADE (somente leitura, nao altera o algoritmo).
Testa se o RTD do Nelogica Profit Pro (RTDTrading.RtdServer via COM) expoe
dados de book de ofertas / Times & Trades.

NAO modifica nenhum modulo do algoritmo. Somente leitura e diagnostico.
"""
import comtypes
import comtypes.client
import ctypes
import sys
from ctypes import HRESULT
from comtypes import GUID, IUnknown, COMMETHOD


class IRtdServer(IUnknown):
    _iid_ = GUID("{EC0E6191-DB51-11D3-8F3E-00C04F3651B8}")
    _methods_ = [
        COMMETHOD([], HRESULT, "ServerStart", (['in'], ctypes.c_void_p, "CallbackObject")),
        COMMETHOD([], HRESULT, "ConnectData",
                  (['in'], ctypes.c_long, "TopicID"),
                  (['in'], ctypes.POINTER(comtypes.automation.VARIANT), "Strings"),
                  (['in', 'out'], ctypes.POINTER(ctypes.c_bool), "GetNewValues"),
                  (['out', 'retval'], ctypes.POINTER(comtypes.automation.VARIANT), "pvarOut")),
        COMMETHOD([], HRESULT, "RefreshData",
                  (['in', 'out'], ctypes.POINTER(ctypes.c_long), "TopicCount"),
                  (['out', 'retval'], ctypes.POINTER(comtypes.automation.VARIANT), "parrayOut")),
        COMMETHOD([], HRESULT, "DisconnectData", (['in'], ctypes.c_long, "TopicID")),
        COMMETHOD([], HRESULT, "Heartbeat"),
        COMMETHOD([], HRESULT, "ServerTerminate"),
    ]


class RtCallback:
    """Callback COM minimo exigido pelo IRtdServer."""

    def __init__(self):
        self.updates = 0
        self.errors = []
        self.disconnected = False

    def UpdateData(self):
        self.updates += 1
        return 0

    def Disconnect(self):
        self.disconnected = True
        return 0

    def Error(self, error_type):
        self.errors.append(error_type)
        return 0


def main():
    print("=" * 70)
    print("SPIKE RTD - Nelogica Profit Pro (RTDTrading.RtdServer)")
    print("=" * 70)

    try:
        rtd = comtypes.client.CreateObject("RTDTrading.RtdServer")
        print("[OK] ProgID RTDTrading.RtdServer instanciado.")
    except Exception as exc:
        print(f"[FALHA] Nao foi possivel instanciar RTD: {exc}")
        return 1

    server = rtd.QueryInterface(IRtdServer)
    print("[OK] Interface IRtdServer obtida.")

    callback = RtCallback()
    try:
        result = server.ServerStart(callback)
        print(f"[OK] ServerStart retornou: {result}")
    except Exception as exc:
        print(f"[FALHA] ServerStart: {type(exc).__name__}: {str(exc)[:180]}")
        try:
            server.ServerTerminate()
        except Exception:
            pass
        return 1

    try:
        print(f"[..] Heartbeat: {server.Heartbeat()}")
    except Exception as exc:
        print(f"[..] Heartbeat falhou: {str(exc)[:120]}")

    # Tentar conectar em topicos realistas do Profit
    topicos = [
        ["WINZ26"],
        ["WINZ26", "ULT"],
        ["WINZ26", "ULT", "ABE", "MAX", "MIN", "NEG", "QTT",
         "AGRVOLC", "AGRVOLV", "AGRSALDO", "VAR"],
    ]
    for strings in topicos:
        try:
            arr = (comtypes.automation.VARIANT * len(strings))()
            for i, s in enumerate(strings):
                arr[i].value = s
            topic_id = ctypes.c_long(0)
            get_new = ctypes.c_bool(True)
            out = comtypes.automation.VARIANT()
            res = server.ConnectData(
                ctypes.byref(topic_id),
                ctypes.byref(arr),
                ctypes.byref(get_new),
                ctypes.byref(out),
            )
            print(f"[..] ConnectData({strings}) -> {res}")
            if res == 0:
                try:
                    print(f"     payload: {out.value}")
                except Exception:
                    print("     payload: <vazio>")
        except Exception as exc:
            print(f"[..] ConnectData({strings[0]}...) falhou: {type(exc).__name__}: {str(exc)[:120]}")

    try:
        print(f"[..] RefreshData: {server.RefreshData(0)}")
    except Exception as exc:
        print(f"[..] RefreshData falhou: {str(exc)[:120]}")

    print()
    print(f"Callbacks UpdateData recebidos: {callback.updates}")
    print(f"Callbacks Error recebidos: {callback.errors}")
    print(f"Desconectado pelo servidor: {callback.disconnected}")

    try:
        server.ServerTerminate()
    except Exception:
        pass

    print()
    print("CONCLUSAO DO SPIKE:")
    if callback.updates > 0:
        print("  O RTD/tutorials emitiu callbacks -> servidor RTD ativo.")
    else:
        print("  Nenhum callback UpdateData. Possiveis causas:")
        print("   - Profit Pro nao esta aberto / sem transmissao RTD habilitada")
        print("   - Nome de topico/topic string diferente do esperado")
        print("   - RTD do Profi expoe apenas cotações agregadas (mesmo escopo do DDE)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
