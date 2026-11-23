"""
spike_rtd_excel.py

SPIKE DE VIABILIDADE - TESTE VIA NATIVO DO EXCEL (somente leitura).

O Profit Pro documenta a sintaxe nativa de RTD:
    =RTD("RTDTrading.RTDServer";; "COT";"ATIVO";"TIPO")

Este spike abre o Excel via COM (comtypes), cria formulas RTD e le o resultado.
NAO altera nenhum modulo do algoritmo. Somente leitura e diagnostico.
"""
import os
import sys
import time

import comtypes.client


def main():
    print("=" * 70)
    print("SPIKE RTD VIA EXCEL NATIVO (sintaxe =RTD do Profit Pro)")
    print("=" * 70)

    try:
        excel = comtypes.client.CreateObject("Excel.Application")
    except Exception as exc:
        print(f"[FALHA] Nao foi possivel abrir o Excel: {exc}")
        return 1

    excel.Visible = False
    excel.DisplayAlerts = False
    print("[OK] Excel instanciado.")

    wb = excel.Workbooks.Add()
    ws = wb.Worksheets(1)

    # Sintaxes candidatas derivadas do binario do Profit.
    # Template encontrado: =RTD("RTDTrading.RTDServer";; "%s"; "%s"; "%s")
    # RTDBookU / RTDTimeTradesU existem no binario.
    candidatas = [
        '=RTD("RTDTrading.RTDServer";; "COT";"WINZ26";"BOOK")',
        '=RTD("RTDTrading.RTDServer";; "COT";"WINZ26";"LST")',
        '=RTD("RTDTrading.RTDServer";; "COT";"WINZ26";"BIDPRICE")',
        '=RTD("RTDTrading.RTDServer";; "COT";"WINZ26";"ASKPRICE")',
        '=RTD("RTDTrading.RTDServer";; "COT";"WINZ26";"BIDSIZE")',
        '=RTD("RTDTrading.RTDServer";; "COT";"WINZ26";"ASKSIZE")',
        '=RTD("RTDTrading.RTDServer";; "COT";"WINZ26";"BOOKSPREAD")',
        '=RTD("RTDTrading.RTDServer";; "COT";"WINZ26";"TRD")',
        '=RTD("RTDTrading.RTDServer";; "COT";"WINZ26";"TQT")',
        '=RTD("RTDTrading.RTDServer";; "COT";"WINZ26";"AGR")',
        '=RTD("RTDTrading.RTDServer";; "COT";"WINZ26";"DELTA")',
    ]

    try:
        for idx, formula in enumerate(candidatas, start=1):
            cell = ws.Cells(idx, 1)
            try:
                cell.Formula = formula
            except Exception as exc:
                print(f"  [{idx}] ERRO AO GRAVAR: {str(exc)[:90]}")
                continue

        # Deixa o Excel calcular
        excel.Calculate()
        time.sleep(3)
        try:
            excel.Calculate()
        except Exception:
            pass
        time.sleep(2)

        print()
        print(f"{'#':<3} {'RESULTADO':<24} {'FORMULA'}")
        print("-" * 100)
        for idx, formula in enumerate(candidatas, start=1):
            try:
                valor = ws.Cells(idx, 1).Value
                texto = str(valor)[:22]
            except Exception as exc:
                texto = f"ERRO:{str(exc)[:18]}"
            print(f"{idx:<3} {texto:<24} {formula}")

        print()
        print("INTERPRETACAO:")
        for idx, formula in enumerate(candidatas, start=1):
            try:
                valor = ws.Cells(idx, 1).Value
            except Exception:
                continue
            if isinstance(valor, str) and "#" in valor:
                print(f"   {formula.split(';')[-1]:<12} -> ERRO {valor}")
            elif valor is not None:
                print(f"   {formula.split(';')[-1]:<12} -> VALOR {valor!r}")

    finally:
        try:
            wb.Close(SaveChanges=False)
        except Exception:
            pass
        try:
            excel.Quit()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
