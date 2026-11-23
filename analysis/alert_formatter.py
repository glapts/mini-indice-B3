"""
analysis/alert_formatter.py
Formatador estrito de alertas operacionais com suporte a cores ANSI no PowerShell/Terminal.
Layout otimizado para SuperDOM: Parâmetros de execução (ENTRADA, STOP, ALVOS) exibidos no topo.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import zoneinfo
import colorama
from colorama import Fore, Back, Style

# Inicializa o Colorama compatível com Windows PowerShell / CMD
colorama.init(autoreset=True)

# Código ANSI para Laranja (ANSI 256 cor 208) compatível com PowerShell / Windows Terminal
ANSI_ORANGE = "\033[38;5;208m"

from core.models import SignalSetup, SetupStatus, Direction
from core.contract import TZ_BRASILIA


def fmt_price(val: Optional[float], decimals: Optional[int] = None) -> str:
    """Formata preços no padrão brasileiro com precisão decimal adequada ao ativo."""
    if val is None:
        return "N/D"
    if decimals is not None:
        dec = decimals
    elif val < 500.0 or abs(val - round(val)) > 1e-4:
        dec = 2
    else:
        dec = 0

    if dec == 0:
        return f"{val:,.0f}".replace(",", ".")
    return f"{val:,.{dec}f}".replace(".", "X").replace(",", ".").replace("X", ",")


def _format_flow_section(
    flow: Dict[str, Any],
    use_color: bool = True,
    C_LABEL: str = "",
    C_RESET: str = "",
    symbol: Optional[str] = None
) -> list:
    out = []
    c_buy = (Fore.GREEN + Style.BRIGHT) if use_color else ""
    c_sell = (Fore.RED + Style.BRIGHT) if use_color else ""

    delta_val = flow.get('delta', 0)
    if use_color:
        if delta_val > 0:
            c_delta = Fore.GREEN + Style.BRIGHT
        elif delta_val < 0:
            c_delta = Fore.RED + Style.BRIGHT
        else:
            c_delta = Fore.YELLOW
    else:
        c_delta = ""

    c_delta_label = (Fore.BLUE + Style.BRIGHT) if use_color else ""
    c_blue_label = (Fore.BLUE + Style.BRIGHT) if use_color else ""
    c_reset_all = Style.RESET_ALL if use_color else ""
    is_vale = bool(symbol and "VALE" in symbol)
    is_wdo = bool(symbol and "WDO" in symbol)
    unit_str = "ações" if is_vale else "contratos"
    delta_str = f"{delta_val:+,d}".replace(",", ".")

    out.append(f"{C_LABEL}TIMES & TRADES:{C_RESET}")
    out.append(f"{c_buy}- Agressão compradora: {flow.get('buy_volume', 0):,} {unit_str}{C_RESET}")
    out.append(f"{c_sell}- Agressão vendedora: {flow.get('sell_volume', 0):,} {unit_str}{C_RESET}")
    out.append("- Janela de cálculo: 300 segundos")
    out.append(f"- {c_delta_label}DELTA{C_RESET}: {c_delta}{delta_str} {unit_str}{C_RESET}")

    disp_val = flow.get('price_displacement_pts', 0.0)
    c_orange = (ANSI_ORANGE + Style.BRIGHT) if use_color else ""
    reset_code = C_RESET if C_RESET else (Style.RESET_ALL if use_color else "")
    if use_color:
        if disp_val > 0:
            c_disp_num = Fore.GREEN + Style.BRIGHT
        elif disp_val < 0:
            c_disp_num = Fore.RED + Style.BRIGHT
        else:
            c_disp_num = c_orange
    else:
        c_disp_num = ""

    if is_vale:
        disp_str = f"{disp_val:+.2f}"
        out.append(f"{c_orange}- Reação do preço: Deslocamento de R$ {c_disp_num}{disp_str}{c_orange}{reset_code}")
    elif is_wdo:
        disp_str = f"{disp_val:+.1f}"
        out.append(f"{c_orange}- Reação do preço: Deslocamento de {c_disp_num}{disp_str}{c_orange} pontos{reset_code}")
    else:
        disp_str = f"{disp_val:+.0f}"
        out.append(f"{c_orange}- Reação do preço: Deslocamento de {c_disp_num}{disp_str}{c_orange} pontos{reset_code}")

    lg_trades = flow.get('large_trades', [])
    if lg_trades:
        formatted_trades = []
        for t in lg_trades[-3:]:
            side = str(t.get('side', 'BUY')).upper()
            if use_color:
                c_side = (Fore.GREEN + Style.BRIGHT) if side == 'BUY' else (Fore.RED + Style.BRIGHT)
            else:
                c_side = ""
            qty = t.get('qty', 0)
            q_fmt = f"{qty:,}".replace(",", ".")
            price = t.get('price', 0.0)
            if is_vale:
                p_fmt = f"{price:.2f}".replace(".", ",")
                formatted_trades.append(f"{c_side}{q_fmt} ações @ R$ {p_fmt} ({side}){c_reset_all}")
            elif is_wdo:
                p_fmt = f"{price:,.1f}".replace(".", "X").replace(",", ".").replace("X", ",")
                formatted_trades.append(f"{c_side}{q_fmt}ct@{p_fmt} ({side}){c_reset_all}")
            else:
                p_fmt = f"{price:,.0f}".replace(",", ".")
                formatted_trades.append(f"{c_side}{q_fmt}ct@{p_fmt} ({side}){c_reset_all}")
        out.append(f"- {c_blue_label}Grandes Execuções:{c_reset_all}")
        for tr in formatted_trades:
            out.append(f"  {tr}")
    else:
        if is_vale:
            lg_summary = "Nenhuma agressão >= 1.000 ações na janela"
        elif is_wdo:
            lg_summary = "Nenhuma agressão >= 30 contratos na janela"
        else:
            lg_summary = "Nenhuma agressão >= 100 contratos na janela"
        out.append(f"- {c_blue_label}Grandes Execuções:{c_reset_all} {lg_summary}")

    pattern = flow.get('flow_pattern', 'Fluxo em equilíbrio')
    c_pat = ""
    if use_color:
        if "Comprador" in pattern or "Compradora" in pattern:
            c_pat = Fore.GREEN + Style.BRIGHT
        elif "Vendedor" in pattern or "Vendedora" in pattern:
            c_pat = Fore.RED + Style.BRIGHT
        else:
            c_pat = Fore.YELLOW
    out.append(f"- {c_blue_label}Possível Absorção:{c_reset_all} {c_pat}{pattern}{c_reset_all}")
    out.append("- Agentes, quando disponíveis: Identificados nos negócios registrados")
    out.append("- Origem institucional: não confirmada, salvo evidência específica.")
    return out


def format_operational_alert(
    setup: Optional[SignalSetup],
    regimes: Dict[str, str],
    source_name: str = "Profit Pro DDE / Market Data",
    delay_ms: float = 0.0,
    quality_status: str = "ÍNTEGRO",
    general_status_override: Optional[str] = None,
    use_color: bool = True,
    flow_data: Optional[Dict[str, Any]] = None,
    symbol_override: Optional[str] = None,
    fvg_radar_banner: Optional[str] = None,
    sp500_macro_filter: Optional[Any] = None
) -> str:
    """
    Formata o alerta conforme a Seção 13, priorizando a visualização ágil para execução no SuperDOM.
    Inclui opcionalmente o Alerta Antecipado de FVG MTF no topo para visualização rápida no PowerShell.
    """
    now_sp = datetime.now(TZ_BRASILIA)
    time_str = now_sp.strftime("%d/%m/%Y %H:%M:%S")

    # Cores
    C_DIV = (Fore.CYAN + Style.DIM) if use_color else ""
    C_RESET = Style.RESET_ALL if use_color else ""
    C_LABEL = (Fore.WHITE + Style.BRIGHT) if use_color else ""
    
    div_main = f"{C_DIV}=================================================================={C_RESET}"
    div_sub = f"{C_DIV}------------------------------------------------------------------{C_RESET}"

    asset_title = symbol_override or (setup.symbol if setup else "WIN (Mini-Índice B3)")

    tfs_list = ["240m", "60m", "30m", "15m", "10m", "5m", "2m", "1m"] if "240m" in regimes else ["60m", "30m", "15m", "10m", "5m", "2m", "1m"]

    if setup is None:
        status_msg = general_status_override or "SEM OPERAÇÃO — AGUARDAR"
        c_status = (Fore.YELLOW + Style.BRIGHT) if use_color else ""
        
        out = []
        out.append(div_main)
        out.append(f"{C_LABEL}DATA/HORA:{C_RESET} {time_str} (America/Sao_Paulo)")
        out.append(f"{C_LABEL}ATIVO/VENCIMENTO:{C_RESET} {asset_title}")
        out.append(f"{C_LABEL}FONTE:{C_RESET} {source_name}")
        out.append(f"{C_LABEL}ATRASO E QUALIDADE:{C_RESET} {delay_ms:.1f}ms | Qualidade: {quality_status}")
        out.append(f"{C_LABEL}STATUS:{C_RESET} {c_status}{status_msg}{C_RESET}")
        out.append(div_sub)
        out.append(f"{C_LABEL}REGIME:{C_RESET}")
        for tf in tfs_list:
            reg_val = regimes.get(tf, 'INDEFINIDO')
            c_reg = Fore.WHITE if use_color else ""
            if use_color:
                if reg_val == "ALTA":
                    c_reg = Fore.GREEN + Style.BRIGHT
                elif reg_val == "BAIXA":
                    c_reg = Fore.RED + Style.BRIGHT
                elif reg_val == "CONSOLIDAÇÃO":
                    c_reg = Fore.YELLOW
            out.append(f"{tf:4}: {c_reg}{reg_val}{C_RESET}")
        out.append(div_sub)
        if flow_data and (flow_data.get('trades_count', 0) > 0 or flow_data.get('buy_volume', 0) > 0 or flow_data.get('sell_volume', 0) > 0):
            out.extend(_format_flow_section(flow_data, use_color=use_color, C_LABEL=C_LABEL, C_RESET=C_RESET, symbol=symbol_override))
            out.append(div_sub)
        if sp500_macro_filter is not None:
            c_macro = (Fore.CYAN + Style.BRIGHT) if use_color else ""
            out.append(f"{C_LABEL}MACRO S&P 500:{C_RESET} {c_macro}{sp500_macro_filter.get_summary_text()}{C_RESET}")
            out.append(div_sub)
        out.append(f"{C_LABEL}DIAGNÓSTICO:{C_RESET} Sem confluência determinística para os setups canônicos.")
        out.append(f"{C_LABEL}DECISÃO DETERMINÍSTICA:{C_RESET} {c_status}SEM OPERAÇÃO — AGUARDAR.{C_RESET}")
        out.append(div_main)
        if fvg_radar_banner:
            out.append("")
            out.append(fvg_radar_banner)
        return "\n".join(out)

    # Setup Presente
    is_blocked = (setup.status == SetupStatus.BLOQUEADO)
    is_buy = (setup.direction == Direction.COMPRA)
    c_dir = (Fore.GREEN + Style.BRIGHT) if is_buy else (Fore.RED + Style.BRIGHT)
    is_macro_blocked = bool(getattr(setup, "macro_reason", None)) or "BLOQUEADO" in str(getattr(setup, "macro_status", ""))
    if is_blocked:
        c_status = (Fore.BLACK + Back.YELLOW + Style.BRIGHT) if use_color else ""
        if is_macro_blocked:
            c_action_text = f"{Fore.YELLOW + Style.BRIGHT}[BLOQUEADO: VETO S&P 500] >>> NÃO EXECUTAR <<<{C_RESET}"
        else:
            c_action_text = f"{Fore.YELLOW + Style.BRIGHT}[BLOQUEADO: OBSTÁCULO INSTITUCIONAL FVG NO ALVO] >>> NÃO EXECUTAR <<<{C_RESET}"
    else:
        c_status = (Fore.BLACK + Back.GREEN + Style.BRIGHT) if is_buy else (Fore.BLACK + Back.RED + Style.BRIGHT)
        c_action_text = f"{c_dir}>>> {setup.direction.value} <<<{C_RESET}"
    if not use_color:
        c_status = ""
        c_dir = ""
        if is_blocked:
            c_action_text = "[BLOQUEADO: VETO S&P 500] >>> NÃO EXECUTAR <<<" if is_macro_blocked else "[BLOQUEADO: OBSTÁCULO FVG] >>> NÃO EXECUTAR <<<"
        else:
            c_action_text = f">>> {setup.direction.value} <<<"

    book = setup.book_evidence or {}
    flow = setup.flow_evidence or flow_data or {}

    # Destaques de Execução (Cores)
    c_ent = (Fore.CYAN + Style.BRIGHT) if use_color else ""
    c_stop = (Fore.RED + Style.BRIGHT) if use_color else ""
    c_alvo = (Fore.GREEN + Style.BRIGHT) if use_color else ""
    c_rr = (Fore.WHITE + Style.BRIGHT) if use_color else ""

    unit_str = "pontos" if ("WIN" in setup.symbol or "WDO" in setup.symbol) else "reais"
    dec_pts = 0 if "WIN" in setup.symbol else 2
    ent_desc = f"{fmt_price(setup.entry_price)} (ENTRADA BLOQUEADA)" if is_blocked else fmt_price(setup.entry_price)
    gatilho_desc = 'BLOQUEADO POR OBSTÁCULO INSTITUCIONAL' if is_blocked else ('CONFIRMADO' if setup.status == SetupStatus.CONFIRMADO else 'PENDENTE DE CONFIRMAÇÃO')

    col_side = "COMPRA (COLUNA AZUL)" if is_buy else "VENDA (COLUNA VERMELHA)"
    ticks_loss = int(round(setup.stop_points / 5.0)) if "WIN" in setup.symbol else int(round(setup.stop_points / 0.5))
    ticks_gain = int(round(setup.target_points / 5.0)) if "WIN" in setup.symbol else int(round(setup.target_points / 0.5))
    bg_color = (Back.GREEN if is_buy else Back.RED) if use_color else ""
    fg_white = (Fore.WHITE + Style.BRIGHT) if use_color else ""
    fg_yellow = (Fore.YELLOW + Style.BRIGHT) if use_color else ""
    c_reset = C_RESET if use_color else ""
    
    p_ent_str = fmt_price(setup.entry_price)
    p_stop_str = fmt_price(setup.stop_price)
    p_alvo_str = fmt_price(setup.target_price)

    out = []

    # =========================================================================
    # TOPO: SEÇÕES INFORMACIONAIS (rolam para cima no terminal)
    # =========================================================================

    # ── NÍVEL 5: RASTREABILIDADE TÉCNICA, FATOS E METADADOS ──
    out.append(div_main)
    out.append(f"{C_LABEL}5. RASTREABILIDADE & METADADOS DA SESSÃO:{C_RESET}")
    out.append(f"  * DATA/HORA                   : {setup.timestamp.strftime('%d/%m/%Y %H:%M:%S')} (America/Sao_Paulo)")
    out.append(f"  * ATIVO/VENCIMENTO            : {setup.symbol}")
    out.append(f"  * FONTE                       : {source_name}")
    out.append(f"  * ATRASO E QUALIDADE          : {delay_ms:.1f}ms | {quality_status}")
    if sp500_macro_filter is not None:
        c_macro = (Fore.CYAN + Style.BRIGHT) if use_color else ""
        out.append(f"  * MACRO S&P 500               : {c_macro}{sp500_macro_filter.get_summary_text()}{C_RESET}")
    
    if setup.facts_observed:
        out.append(f"  {C_LABEL}FATOS OBSERVADOS:{C_RESET}")
        c_blue_label = (Fore.BLUE + Style.BRIGHT) if use_color else ""
        for f in setup.facts_observed:
            if use_color:
                f_text = f.replace("Delta=", f"{c_blue_label}DELTA{C_RESET}=").replace("Delta", f"{c_blue_label}DELTA{C_RESET}").replace("delta", f"{c_blue_label}DELTA{C_RESET}")
            else:
                f_text = f.replace("Delta", "DELTA").replace("delta", "DELTA")
            out.append(f"    - {f_text}")

    if setup.interpretations:
        out.append(f"  {C_LABEL}INTERPRETAÇÕES:{C_RESET}")
        for i in setup.interpretations:
            out.append(f"    - {i}")

    if setup.limitations:
        out.append(f"  {C_LABEL}LIMITAÇÕES:{C_RESET}")
        for lim in setup.limitations:
            out.append(f"    - {lim}")

    # ── NÍVEL 4: GERENCIAMENTO DE RISCO, VALIDADE E INVALIDAÇÃO ──
    out.append(div_sub)
    out.append(f"{C_LABEL}4. GESTÃO DE RISCO E INVALIDAÇÃO:{C_RESET}")
    out.append(f"  * RETORNO/RISCO               : {c_rr}{setup.risk_reward:.2f}{C_RESET}")
    validity_str = setup.validity_deadline.strftime("%H:%M:%S") if setup.validity_deadline else "Próximo fechamento de barra"
    out.append(f"  * VALIDADE                    : Até {validity_str}")
    out.append(f"  * INVALIDAÇÃO                 : {setup.invalidation_criteria}")

    # ── NÍVEL 2: TESE OPERACIONAL E CONTEXTO SMC (POR QUE AGIR) ──
    out.append(div_sub)
    out.append(f"{C_LABEL}2. ESTRUTURA E CONTEXTO SMC:{C_RESET}")
    c_mag = (Fore.MAGENTA + Style.BRIGHT) if use_color else ""
    out.append(f"  * SETUP                       : {c_mag}{setup.setup_name}{C_RESET}")
    out.append(f"  * DIREÇÃO                     : {c_dir}>>> {setup.direction.value} <<<{C_RESET}")
    out.append(f"  * CONTEXTO MACRO              : {'Alinhado com Contexto Macro (A FAVOR)' if setup.in_trend_direction else 'Contratendência em relação ao Contexto Macro (CONTRA)'}")
    out.append(f"  * A FAVOR OU CONTRA O CONTEXTO: {'A FAVOR' if setup.in_trend_direction else 'CONTRA'}")
    
    struct_txt = setup.structure_event or 'Estrutura regular'
    if use_color:
        struct_txt = struct_txt.replace("agressão compradora", f"{Fore.GREEN + Style.BRIGHT}agressão compradora{C_RESET}")
        struct_txt = struct_txt.replace("agressão vendedora", f"{Fore.RED + Style.BRIGHT}agressão vendedora{C_RESET}")
    out.append(f"  * CHoCH/BOS                   : {struct_txt}")

    fvg_txt = setup.fvg_zone or 'Nenhum FVG ativo no gatilho'
    c_fvg = (Fore.YELLOW + Style.BRIGHT) if use_color else ""
    out.append(f"  * FVG                         : {c_fvg}{fvg_txt}{C_RESET}")

    sweep_txt = f"{setup.sweep_level:.0f}" if setup.sweep_level else "Não aplicável"
    out.append(f"  * NÍVEL E HORÁRIO DO SWEEP    : {sweep_txt}")

    # Regimes em formato visual organizado
    regime_line_items = []
    for tf in tfs_list:
        reg_val = regimes.get(tf, 'INDEFINIDO')
        c_reg = Fore.WHITE if use_color else ""
        if use_color:
            if reg_val == "ALTA":
                c_reg = Fore.GREEN + Style.BRIGHT
            elif reg_val == "BAIXA":
                c_reg = Fore.RED + Style.BRIGHT
            elif reg_val == "CONSOLIDAÇÃO":
                c_reg = Fore.YELLOW
        regime_line_items.append(f"{tf}:{c_reg}{reg_val}{C_RESET}")
    out.append(f"  * REGIME                      : " + " | ".join(regime_line_items))

    # =========================================================================
    # FUNDO: SEÇÕES ACIONÁVEIS (sempre visíveis sem scroll no PowerShell)
    # =========================================================================

    # ── AÇÃO IMEDIATA NO SUPERDOM (O QUE FAZER NOS PRÓXIMOS 2 SEGUNDOS) ──
    out.append(div_main)
    if not is_blocked and setup.status == SetupStatus.CONFIRMADO:
        if getattr(setup, "macro_status", None) == "CONFLUENCE":
            c_bg_conf = (Back.CYAN + Fore.BLACK + Style.BRIGHT) if use_color else ""
            out.append(f"{c_bg_conf}╔══════════════════════════════════════════════════════════════════════════╗{c_reset}")
            out.append(f"{c_bg_conf}║  🌎 [CONFLUÊNCIA S&P 500 ATIVA: WIN + S&P 500 ALINHADOS] (+20 Score)   ║{c_reset}")
            out.append(f"{c_bg_conf}╚══════════════════════════════════════════════════════════════════════════╝{c_reset}")
        out.append(f"{bg_color}{fg_white}╔══════════════════════════════════════════════════════════════════════════╗{c_reset}")
        out.append(f"{bg_color}{fg_white}║         ⚡ EXECUÇÃO NO SUPERDOM — 1 CLIQUE (SEM DIGITAR NADA) ⚡         ║{c_reset}")
        out.append(f"{bg_color}{fg_white}╠══════════════════════════════════════════════════════════════════════════╣{c_reset}")
        out.append(f"{bg_color}{fg_white}║  👉 CLIQUE NA COLUNA : {fg_yellow}{col_side:<47}{fg_white}║{c_reset}")
        out.append(f"{bg_color}{fg_white}║  👉 PREÇO DO TICK    : {fg_yellow}>>>  {p_ent_str:^10}  <<<{fg_white} (NÍVEL EXATO DE ENTRADA)    ║{c_reset}")
        if setup.partial_target_price and setup.partial_target_points:
            p_p1_str = fmt_price(setup.partial_target_price)
            tick_val = 5.0 if "WIN" in setup.symbol else (0.5 if "WDO" in setup.symbol else 0.01)
            ticks_p1 = int(round(setup.partial_target_points / tick_val)) if tick_val > 0 else 0
            val_p1 = f"{ticks_p1} ticks ({p_p1_str}) [{setup.partial_target_points:.{dec_pts}f} {unit_str} — Borda FVG]"
            pad_len_p1 = 74 - len("  👉 PARCIAL (BORDA)  : ") - len(val_p1)
            pad_p1 = " " * max(0, pad_len_p1)
            out.append(f"{bg_color}{fg_white}║  👉 PARCIAL (BORDA)  : {fg_yellow}{val_p1}{fg_white}{pad_p1}║{c_reset}")
        out.append(f"{bg_color}{fg_white}║  ESTRATÉGIA OCO      : Stop {ticks_loss} ticks ({p_stop_str}) | Alvo {ticks_gain} ticks ({p_alvo_str}) ║{c_reset}")
        out.append(f"{bg_color}{fg_white}║  QUANTIDADE          : CONTRATOS FIXOS PRÉ-CONFIGURADOS NO DOM           ║{c_reset}")
        out.append(f"{bg_color}{fg_white}╚══════════════════════════════════════════════════════════════════════════╝{c_reset}")
    elif is_blocked:
        c_bg_warn = (Back.YELLOW + Fore.BLACK + Style.BRIGHT) if use_color else ""
        out.append(f"{c_bg_warn}╔══════════════════════════════════════════════════════════════════════════╗{c_reset}")
        if is_macro_blocked:
            out.append(f"{c_bg_warn}║      ⛔ OPERAÇÃO BLOQUEADA PELO FILTRO S&P 500 — NÃO EXECUTAR NO DOM ⛔  ║{c_reset}")
            out.append(f"{c_bg_warn}╠══════════════════════════════════════════════════════════════════════════╣{c_reset}")
            reason_txt = getattr(setup, "macro_reason", "Veto macro S&P 500 ativo.") or "Veto macro S&P 500 ativo."
            pad_r = " " * max(0, 66 - len(reason_txt))
            out.append(f"{c_bg_warn}║  MOTIVO: {reason_txt[:66]}{pad_r}║{c_reset}")
        elif any("ABSORÇÃO" in str(x) for x in setup.obstacles) or any("ABSORÇÃO" in str(x) for x in setup.interpretations):
            out.append(f"{c_bg_warn}║    ⛔ OPERAÇÃO BLOQUEADA POR ABSORÇÃO NO BOOK — NÃO EXECUTAR NO DOM ⛔    ║{c_reset}")
            out.append(f"{c_bg_warn}╠══════════════════════════════════════════════════════════════════════════╣{c_reset}")
            motivo_msg = "  MOTIVO: Absorção contrária no Tape Reading. Veto institucional ativo.    "
            out.append(f"{c_bg_warn}║{motivo_msg}║{c_reset}")
        else:
            out.append(f"{c_bg_warn}║      ⛔ OPERAÇÃO BLOQUEADA PELO RADAR FVG — NÃO EXECUTAR NO DOM ⛔      ║{c_reset}")
            out.append(f"{c_bg_warn}╠══════════════════════════════════════════════════════════════════════════╣{c_reset}")
            if any("MACRO" in str(x) for x in setup.interpretations):
                motivo_msg = "  MOTIVO: Barreira institucional MACRO (60m/4h) no caminho do alvo.       "
            elif any("VETO SMC" in str(x) for x in setup.interpretations):
                motivo_msg = "  MOTIVO: Veto SMC — Deslocamento esticado (> 180 pts). Aguardar pullback."
            else:
                motivo_msg = "  MOTIVO: Barreira FVG no caminho e fluxo insuficiente p/ Flow Override.  "
            out.append(f"{c_bg_warn}║{motivo_msg}║{c_reset}")
        out.append(f"{c_bg_warn}╚══════════════════════════════════════════════════════════════════════════╝{c_reset}")

    # ── NÍVEL 1: COMANDO DE EXECUÇÃO ──
    out.append(div_main)
    out.append(f"{C_LABEL}1. COMANDO DE EXECUÇÃO:{C_RESET}")
    out.append(f"  * AÇÃO NO SUPERDOM            : {c_action_text}")
    out.append(f"  * ENTRADA                     : {c_ent}{ent_desc}{C_RESET}")
    out.append(f"  * GATILHO PENDENTE OU CONFIRMADO: {gatilho_desc}")
    out.append(f"  * STOP EM PREÇO E PONTOS      : {c_stop}{fmt_price(setup.stop_price)} ({setup.stop_points:.{dec_pts}f} {unit_str}){C_RESET}")
    if setup.partial_target_price and setup.partial_target_points:
        p_p1_str = fmt_price(setup.partial_target_price)
        out.append(f"  * ALVOS EM PREÇO E PONTOS     : {c_alvo}{p_p1_str} ({setup.partial_target_points:.{dec_pts}f} {unit_str} - PARCIAL FVG) | {fmt_price(setup.target_price)} ({setup.target_points:.{dec_pts}f} {unit_str} - FINAL){C_RESET}")
    else:
        out.append(f"  * ALVOS EM PREÇO E PONTOS     : {c_alvo}{fmt_price(setup.target_price)} ({setup.target_points:.{dec_pts}f} {unit_str}){C_RESET}")
    
    status_suffix = ""
    if setup.status == SetupStatus.CONFIRMADO and any("FLOW OVERRIDE" in str(x) for x in setup.interpretations):
        status_suffix = f" {Fore.CYAN + Style.BRIGHT}[⚡ FLOW OVERRIDE ATIVO]{C_RESET}"
    if getattr(setup, "macro_status", None) == "CONFLUENCE":
        status_suffix += f" {Fore.CYAN + Style.BRIGHT}[🌎 CONFLUÊNCIA S&P 500 ATIVA]{C_RESET}"
    out.append(f"  * STATUS                      : {c_status} {setup.status.value} {C_RESET}{status_suffix}")
    if getattr(setup, "score_smc", None) is not None:
        out.append(f"  * SCORE SMC INSTITUCIONAL     : {setup.score_smc:.0f}/100")
    
    obs_text = '; '.join(setup.obstacles) if setup.obstacles else 'Nenhum obstáculo técnico intermediário mapeado'
    if use_color:
        if "OBSTÁCULO INSTITUCIONAL" in obs_text:
            obs_text = Fore.YELLOW + Style.BRIGHT + obs_text + C_RESET
        elif "PASSAGEM LIVRE" in obs_text:
            obs_text = Fore.GREEN + Style.BRIGHT + obs_text + C_RESET
    out.append(f"  * OBSTÁCULOS / PASSAGEM       : {obs_text}")

    # ── RADAR FVG ANTECIPADO (visível logo após comando de execução) ──
    if fvg_radar_banner:
        out.append(fvg_radar_banner)
    else:
        out.append(div_sub)

    # ── NÍVEL 3: FLUXO DE ORDENS & BOOK DE OFERTAS (TAPE READING) ──
    out.append(f"{C_LABEL}3. CONFIRMAÇÃO DE FLUXO & BOOK (TAPE READING):{C_RESET}")
    out.extend(_format_flow_section(flow, use_color=use_color, C_LABEL="  * ", C_RESET=C_RESET, symbol=setup.symbol if setup else symbol_override))

    out.append(f"  {C_LABEL}BOOK:{C_RESET}")
    out.append(f"    - Comportamento observado   : {book.get('observed_behavior', 'Dados agregados ou sem profundidade L2')}")
    _bm = book.get('metrics', {}) or {}
    _depth = _bm.get('book_depth_levels', 0)
    _imb = _bm.get('book_imbalance', 'N/D')
    _imb_label = f"Imbalance Top{_depth}" if _depth else "Imbalance"
    m_str = f"Spread: {_bm.get('spread', 'N/D')} pts | {_imb_label}: {_imb}"
    if _depth:
        m_str += f" | Níveis observados: {_depth}"
    out.append(f"    - Métricas                  : {m_str}")
    out.append(f"    - Possível blefe ou evidência insuficiente: {book.get('classification', 'Evidência insuficiente')}")
    limitations_b = "; ".join(book.get('limitations', ['Feed sem eventos de livro individual']))
    out.append(f"    - Limitações                : {limitations_b}")

    out.append(div_main)

    return "\n".join(out)
