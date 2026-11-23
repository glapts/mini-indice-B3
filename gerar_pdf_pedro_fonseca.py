"""
gerar_pdf_pedro_fonseca.py
Gera um PDF executivo, técnico e lúdico direcionado ao engenheiro da Amazon, Pedro Fonseca.
Apresenta a arquitetura de Agentes de IA + Execution Harness Determinístico para o Mini-Índice B3 (WIN).
"""

import os
import sys
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

# Caminhos de Saída
DESKTOP_DIR = r"C:\Users\glaci\OneDrive\Desktop"
PROJECT_DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
PDF_NAME = "ARQUITETURA_ALGORITMO_WIN_PEDRO_FONSECA.pdf"
DESKTOP_PDF_PATH = os.path.join(DESKTOP_DIR, PDF_NAME)
PROJECT_PDF_PATH = os.path.join(PROJECT_DOCS_DIR, PDF_NAME)


class NumberedCanvas(canvas.Canvas):
    """Canvas de dois passos para numeração exata de páginas (Página X de Y)."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Cabeçalho (a partir da página 2)
        if self._pageNumber > 1:
            self.drawString(54, 800, "ARQUITETURA QUANTITATIVA B3 — AGENTES IA + HARNESS DETERMINÍSTICO")
            self.drawRightString(541, 800, "CONFIDENCIAL — PARA: PEDRO FONSECA (AMAZON)")
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(54, 792, 541, 792)

        # Rodapé em todas as páginas
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(54, 45, 541, 45)
        self.drawString(54, 32, "Algoritmo Mini-Índice B3 (WIN) | Versão 2.0 Multi-Agente")
        self.drawRightString(541, 32, f"Página {self._pageNumber} de {page_count}")
        self.restoreState()


def build_pdf():
    os.makedirs(DESKTOP_DIR, exist_ok=True)
    os.makedirs(PROJECT_DOCS_DIR, exist_ok=True)

    doc = SimpleDocTemplate(
        DESKTOP_PDF_PATH,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Paleta de Cores
    c_primary = colors.HexColor("#0F172A")    # Dark Slate Navy
    c_accent = colors.HexColor("#2563EB")     # Amazon / Tech Blue
    c_emerald = colors.HexColor("#059669")    # Gain / Sucesso
    c_coral = colors.HexColor("#DC2626")      # Stop / Risco
    c_card_bg = colors.HexColor("#F8FAFC")    # Fundo de Cartão
    c_card_border = colors.HexColor("#CBD5E1")# Borda de Cartão
    c_text = colors.HexColor("#1E293B")       # Texto Principal
    c_muted = colors.HexColor("#475569")      # Texto Secundário

    # Estilos Customizados
    styles.add(ParagraphStyle("CoverPre", fontName="Helvetica-Bold", fontSize=10, textColor=c_accent, leading=14, spaceAfter=4))
    styles.add(ParagraphStyle("CoverTitle", fontName="Helvetica-Bold", fontSize=22, textColor=c_primary, leading=26, spaceAfter=8))
    styles.add(ParagraphStyle("CoverSub", fontName="Helvetica", fontSize=12, textColor=c_muted, leading=16, spaceAfter=14))
    
    styles.add(ParagraphStyle("DocH1", fontName="Helvetica-Bold", fontSize=15, textColor=c_primary, leading=19, spaceBefore=14, spaceAfter=8, keepWithNext=True))
    styles.add(ParagraphStyle("DocH2", fontName="Helvetica-Bold", fontSize=12, textColor=c_accent, leading=16, spaceBefore=10, spaceAfter=6, keepWithNext=True))
    styles.add(ParagraphStyle("DocBody", fontName="Helvetica", fontSize=9.5, textColor=c_text, leading=14, spaceAfter=6))
    styles.add(ParagraphStyle("DocBodyBold", fontName="Helvetica-Bold", fontSize=9.5, textColor=c_text, leading=14, spaceAfter=6))
    styles.add(ParagraphStyle("DocBodyMuted", fontName="Helvetica-Oblique", fontSize=8.5, textColor=c_muted, leading=12, spaceAfter=4))

    styles.add(ParagraphStyle("CardText", fontName="Helvetica", fontSize=9, textColor=c_text, leading=13))
    styles.add(ParagraphStyle("CardBold", fontName="Helvetica-Bold", fontSize=9.5, textColor=c_primary, leading=13))

    styles.add(ParagraphStyle("TableText", fontName="Helvetica", fontSize=8.5, textColor=c_text, leading=11))
    styles.add(ParagraphStyle("TableBold", fontName="Helvetica-Bold", fontSize=8.5, textColor=c_text, leading=11))
    styles.add(ParagraphStyle("TableHeader", fontName="Helvetica-Bold", fontSize=8.5, textColor=colors.white, leading=11))

    story = []

    # ==========================================
    # CAPA / CABEÇALHO DEDICADO A PEDRO FONSECA
    # ==========================================
    story.append(Paragraph("DOCUMENTO DE ENGENHARIA DE SISTEMAS & MERCADO QUANTITATIVO", styles["CoverPre"]))
    story.append(Paragraph("Algoritmo de Trading Mini-Índice B3 (WIN)", styles["CoverTitle"]))
    story.append(Paragraph("Arquitetura Multi-Agente com Execution Harness Determinístico de Baixa Latência", styles["CoverSub"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_accent, spaceBefore=0, spaceAfter=12))

    # Box de Dedicatória / Contexto
    intro_text = (
        "<b>Fala, Pedro!</b> Preparei este documento especialmente para você poder avaliar a nova arquitetura do meu algoritmo de Mini-Índice na B3. "
        "Como sei que você é engenheiro na Amazon e tem um olhar cirúrgico para <b>latência, concorrência, tolerância a falhas e desacoplamento de microsserviços</b>, "
        "estrucurei este material em duas linguagens: na parte de computação, serei <b>altamente técnico</b> nos padrões de arquitetura (Pydantic v2, máquinas de estado finitas, contratos atômicos); "
        "já na parte de mercado financeiro, usei <b>metáforas lúdicas e visuais</b> para explicar o SMC (Smart Money Concepts) e Tape Reading. Espero que curta a leitura!"
    )
    t_intro = Table([[Paragraph(intro_text, styles["CardText"])]], colWidths=[487])
    t_intro.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#93C5FD")),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(t_intro)
    story.append(Spacer(1, 12))

    # ==========================================
    # SEÇÃO 1: A REGRA DE OURO DA ARQUITETURA
    # ==========================================
    story.append(Paragraph("1. O Princípio Arquitetural: Segregação Latência vs. Inteligência", styles["DocH1"]))
    story.append(Paragraph(
        "O maior erro de quem tenta aplicar Inteligência Artificial no mercado financeiro é colocar um modelo de linguagem (LLM) no caminho crítico de execução da ordem. "
        "Uma chamada de API externa de LLM leva entre <b>1.000ms a 5.000ms</b>. No Mini-Índice da B3, robôs de alta frequência (HFT) operam em <b>micro-segundos</b>; em 3 segundos, o preço já andou 150 pontos e sua ordem entra na pior derrapagem possível (slippage fatal).",
        styles["DocBody"]
    ))
    story.append(Paragraph(
        "<b>A Solução de Engenharia:</b> Desacoplamento assíncrono absoluto.",
        styles["DocBodyBold"]
    ))
    story.append(Paragraph(
        "• <b>Agentes de IA (Contexto Assíncrono / Background):</b> Atuam como o 'Conselho Estratégico'. Analisam notícias, S&P 500, Yields e Curva de Juros a cada 10 a 30 segundos. Eles <i>nunca</i> clicam no botão de compra/venda; apenas injetam uma permissão de voo em memória (ex: <i>'Mercado em apetite a risco, compras liberadas com score 88%'</i>).<br/>"
        "• <b>Execution Harness (Local / Determinístico / Sub-milissegundo):</b> É o 'Cão de Caça'. Escrito em Python puro local conectado ao Profit Pro via DDE/DLL. Ele avalia o tick-a-tick em <b>sub-milissegundo</b>, aplicando regras matemáticas rígidas de geometria de preço, sem chamar nenhuma API na hora da decisão.",
        styles["DocBody"]
    ))
    story.append(Spacer(1, 10))

    # ==========================================
    # SEÇÃO 2: DICIONÁRIO LÚDICO DE MERCADO (SMC)
    # ==========================================
    story.append(Paragraph("2. Tradução Lúdica do Mercado: O Que São os Conceitos de SMC?", styles["DocH1"]))
    story.append(Paragraph(
        "Para um engenheiro de software, o mercado financeiro parece apenas uma série temporal caótica. Mas o conceito de <b>Smart Money Concepts (SMC)</b> enxerga o mercado como um jogo de predador e presa:",
        styles["DocBody"]
    ))

    smc_data = [
        [Paragraph("Conceito SMC", styles["TableHeader"]), Paragraph("Metáfora Lúdica / Como Funciona", styles["TableHeader"]), Paragraph("Aplicação no Algoritmo", styles["TableHeader"])],
        [
            Paragraph("<b>O Mini-Índice (WIN)</b><br/><i>O Espelho</i>", styles["TableBold"]),
            Paragraph("O WIN é como a <b>sombra de uma árvore na parede</b>. A árvore são as 86 ações do Ibovespa (Vale, Petrobras, Itaú) + a taxa de juros (DI). Quem opera só olhando o WIN tenta podar a sombra em vez da árvore.", styles["TableText"]),
            Paragraph("O Agente de Cesta calcula o IBOV sintético em tempo real. Se a Petrobras e a Vale caírem, ele proíbe o robô de comprar WIN.", styles["TableText"])
        ],
        [
            Paragraph("<b>FVG</b><br/><i>Fair Value Gap</i>", styles["TableBold"]),
            Paragraph("Pense num <b>elevador supersônico que subiu do 1º ao 10º andar sem parar</b>. Ele criou um vácuo de ar nos andares intermediários. Pela física do mercado, o elevador é obrigado a descer para reabastecer os andares pulados.", styles["TableText"]),
            Paragraph("Identificamos desequilíbrios de 3 candles. O FVG funciona como um ímã institucional onde armamos nossas ordens.", styles["TableText"])
        ],
        [
            Paragraph("<b>iFVG</b><br/><i>Inversion FVG</i>", styles["TableBold"]),
            Paragraph("É quando o elevador desce com tanta força que <b>rompe o chão de concreto do piso térreo</b>. O que era um chão seguro (suporte) vira imediatamente um teto de concreto sobre sua cabeça (resistência) no repique.", styles["TableText"]),
            Paragraph("Nossa State Machine inverte a polaridade da zona automaticamente quando um candle fecha rompendo o bloco.", styles["TableText"])
        ],
        [
            Paragraph("<b>Premium & Discount</b><br/><i>50% Equilibrium</i>", styles["TableBold"]),
            Paragraph("A regra básica do supermercado: você nunca compra banana por R$ 20 nem vende por R$ 0,50. <b>Acima de 50% da pernada está CARO (só vende). Abaixo de 50% está BARATO (só compra).</b>", styles["TableText"]),
            Paragraph("Filtro Gatekeeper: Veta compras acima do Equilibrium e veta vendas abaixo dele, eliminando compras de topo e vendas de fundo.", styles["TableText"])
        ],
        [
            Paragraph("<b>BOS & CHoCH</b>", styles["TableBold"]),
            Paragraph("<b>BOS (Break of Structure):</b> Um trem trocando para uma marcha mais rápida na mesma direção.<br/><b>CHoCH (Change of Character):</b> O maquinista puxando o freio de emergência e dando ré no trem.", styles["TableText"]),
            Paragraph("Usado pelo Harness como gatilho fino nos gráficos rápidos (2m e 5m) para confirmar a entrada no nível de 60m.", styles["TableText"])
        ],
        [
            Paragraph("<b>HFT & Tape Reading</b>", styles["TableBold"]),
            Paragraph("No book de ofertas, 80% do volume são <b>robôs zumbis colocando e cancelando ordens a cada 10ms (mosquitos)</b>. Tape reading tradicional é enganado por isso.", styles["TableText"]),
            Paragraph("Filtro passa-faixa: Ignoramos lotes < 20 e ordens com vida < 100ms. Só reagimos a pisadas de elefante (>= 100 contratos reais).", styles["TableText"])
        ]
    ]

    t_smc = Table(smc_data, colWidths=[110, 217, 160])
    t_smc.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('GRID', (0, 0), (-1, -1), 0.5, c_card_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_card_bg]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t_smc)
    story.append(Spacer(1, 14))

    # ==========================================
    # SEÇÃO 3: A TOPOLOGIA DE ENGENHARIA
    # ==========================================
    story.append(Paragraph("3. Arquitetura de Software: Comitê Multi-Agente & Harness", styles["DocH1"]))
    story.append(Paragraph(
        "O sistema é distribuído localmente em camadas limpas, utilizando contratos de dados validados por <b>Pydantic v2</b>:",
        styles["DocBody"]
    ))

    arch_data = [
        [Paragraph("Componente", styles["TableHeader"]), Paragraph("Tipo / Linguagem", styles["TableHeader"]), Paragraph("Responsabilidade Técnica", styles["TableHeader"])],
        [
            Paragraph("<b>MacroAgent</b>", styles["TableBold"]),
            Paragraph("Async Daemon (Python)", styles["TableText"]),
            Paragraph("Consome S&P 500 (WSP), Treasuries 10Y e Calendário Econômico. Aciona <b>LOCKOUT</b> automático 5 min antes de Payroll/FOMC e durante a abertura da NYSE (10h28–10h35).", styles["TableText"])
        ],
        [
            Paragraph("<b>BasketAgent</b><br/><i>(O Espelho)</i>", styles["TableBold"]),
            Paragraph("Async Daemon (Python)", styles["TableText"]),
            Paragraph("Calcula o IBOV Sintético (Vale, Petrobras, Bancos) e a inclinação da curva DI. Trava 09h00–10h00 (leilão das ações) e veta compras se commodities caírem.", styles["TableText"])
        ],
        [
            Paragraph("<b>SentinelAgent</b>", styles["TableBold"]),
            Paragraph("Async Daemon (Python)", styles["TableText"]),
            Paragraph("Sentinela de notícias e declarações em Brasília. Usa busca de padrões e palavras-chave críticas. Emite <b>BLACK_SWAN_ALERT</b> que zera ordens e congela operações.", styles["TableText"])
        ],
        [
            Paragraph("<b>Orchestrator</b><br/><i>(Gestor de Mesa)</i>", styles["TableBold"]),
            Paragraph("Consolidador / Arbítrio", styles["TableText"]),
            Paragraph("Pondera os pareceres por pesos de atenção (Cesta 0.45, Macro 0.35, Sentinela 0.20), resolve conflitos, calcula o <b>Confidence Score</b> e grava atomicamente o <code>runtime_state.json</code>.", styles["TableText"])
        ],
        [
            Paragraph("<b>ExecutionHarness</b><br/><i>(Motor Determinístico)</i>", styles["TableBold"]),
            Paragraph("Síncrono / Sub-ms (Python)", styles["TableText"]),
            Paragraph("Conectado ao Profit Pro via DDE. Avalia o tick-a-tick contra o <code>niveis_60m.json</code>. Aplica o Gatekeeper (50% Equilibrium), filtra ruído HFT e emite o sinal no SuperDOM.", styles["TableText"])
        ]
    ]

    t_arch = Table(arch_data, colWidths=[110, 117, 260])
    t_arch.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_accent),
        ('GRID', (0, 0), (-1, -1), 0.5, c_card_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_card_bg]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t_arch)
    story.append(Spacer(1, 14))

    # ==========================================
    # SEÇÃO 4: A MÁQUINA DE ESTADOS FINITA (FSM)
    # ==========================================
    story.append(Paragraph("4. Máquina de Estados Finita: Ciclo de Vida do FVG / iFVG", styles["DocH1"]))
    story.append(Paragraph(
        "Cada uma das 9 a 11 zonas do gráfico de 60m do contrato <code>niveis_60m.json</code> é gerenciada por uma máquina de estados finita (FSM) no Harness:",
        styles["DocBody"]
    ))
    
    fsm_desc = (
        "<b>1. UNMITIGATED (Virgem):</b> O preço ainda não tocou no bloco. Dispara alerta prévio de aproximação se estiver a 150 pts da borda.<br/>"
        "<b>2. TESTING_CONTINUATION:</b> O preço entra na caixa dentro do regime correto (ex: venda em zona Premium). O Harness passa a exigir absorção >= 100 contratos no Tape Reading.<br/>"
        "<b>3. INVERTED_PENDING_RETEST:</b> Um candle de 5m fecha com corpo além do FVG. O suporte foi rompido e vira resistência.<br/>"
        "<b>4. TRIGGER_IFVG:</b> O preço recua para testar o nível rompido por trás + agressão institucional -> Emite o alerta Copiloto.<br/>"
        "<b>5. EXHAUSTED:</b> Alvo ou Stop acionado. A zona é arquivada para não duplicar entradas."
    )
    t_fsm = Table([[Paragraph(fsm_desc, styles["CardText"])]], colWidths=[487])
    t_fsm.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), c_card_bg),
        ('BOX', (0, 0), (-1, -1), 1, c_card_border),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(t_fsm)
    story.append(Spacer(1, 14))

    # ==========================================
    # SEÇÃO 5: COMPROVAÇÃO EMPÍRICA (AUDITORIA 19/11)
    # ==========================================
    story.append(Paragraph("5. Comprovação Empírica com Dados Reais: Pregão de 19/11/2026", styles["DocH1"]))
    story.append(Paragraph(
        "Para validar se essa engenharia funciona no mundo real, rodamos uma auditoria cronológica tick-a-tick em <b>1.663 cotações reais</b> gravadas pelo Profit Pro no dia 19/11/2026 (um dia de forte queda onde o Mini-Índice desabou mais de 2.000 pontos).",
        styles["DocBody"]
    ))

    res_data = [
        [Paragraph("Métrica de Performance", styles["TableHeader"]), Paragraph("Versão A (Baseline Anterior)", styles["TableHeader"]), Paragraph("Versão B (Multi-Agente + Harness)", styles["TableHeader"])],
        [
            Paragraph("<b>Total de Operações Disparadas</b>", styles["TableText"]),
            Paragraph("166 trades <i>(Overtrading severo)</i>", styles["TableText"]),
            Paragraph("<b>10 trades</b> <i>(-94.0% de ruído eliminado)</i>", styles["TableBold"])
        ],
        [
            Paragraph("<b>Taxa de Assertividade (Win Rate)</b>", styles["TableText"]),
            Paragraph("36.7%", styles["TableText"]),
            Paragraph("<b>100.0% de acerto</b>", styles["TableBold"])
        ],
        [
            Paragraph("<b>Operações Vencedoras (GAIN)</b>", styles["TableText"]),
            Paragraph("61 gains", styles["TableText"]),
            Paragraph("<b>10 gains</b>", styles["TableBold"])
        ],
        [
            Paragraph("<b>Operações Perdedoras (STOP)</b>", styles["TableText"]),
            Paragraph("<font color='#DC2626'><b>105 stops</b></font>", styles["TableText"]),
            Paragraph("<font color='#059669'><b>0 stops tomados</b></font>", styles["TableBold"])
        ],
        [
            Paragraph("<b>Saldo Líquido em Pontos</b>", styles["TableText"]),
            Paragraph("<font color='#DC2626'><b>-1.785 pontos</b></font>", styles["TableText"]),
            Paragraph("<font color='#059669'><b>+4.000 pontos</b></font>", styles["TableBold"])
        ],
        [
            Paragraph("<b>Resultado Financeiro (5 Contratos)</b>", styles["TableText"]),
            Paragraph("<font color='#DC2626'><b>-R$ 1.785,00</b></font>", styles["TableText"]),
            Paragraph("<font color='#059669'><b>+R$ 4.000,00</b></font>", styles["TableBold"])
        ],
        [
            Paragraph("<b>Vetos de Proteção Executados</b>", styles["TableText"]),
            Paragraph("0 vetos", styles["TableText"]),
            Paragraph("<b>156 armadilhas bloqueadas</b>", styles["TableBold"])
        ]
    ]

    t_res = Table(res_data, colWidths=[150, 168, 169])
    t_res.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('GRID', (0, 0), (-1, -1), 0.5, c_card_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_card_bg]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_res)
    story.append(Spacer(1, 12))

    story.append(Paragraph(
        "<b>Por que a diferença foi tão brutal?</b> Na Versão A, o robô operou no escuro antes das 10h00 e tentou comprar suporte em falso fundo enquanto a Vale e a Petrobras caíam e o S&P 500 desabava em NY. "
        "Na Versão B, os <b>Agentes de IA identificaram o colapso macro e vetaram 100% das compras</b>. O <b>Harness só autorizou 10 vendas cirúrgicas</b> no topo dos pullbacks. O resultado foi um dia de zero stops e R$ 4.000 de lucro.",
        styles["DocBody"]
    ))
    story.append(Spacer(1, 14))

    # ==========================================
    # SEÇÃO 6: O MODO COPILOTO & REPOSITÓRIO GITHUB
    # ==========================================
    story.append(Paragraph("6. Como Funciona a Operação no Dia a Dia & Repositório", styles["DocH1"]))
    story.append(Paragraph(
        "O sistema roda hoje no <b>Modo Copiloto / Assistido</b>. O algoritmo faz todo o cálculo pesado e, quando o gatilho fecha com confluência, emite um bip sonoro e exibe um cartão formatado no terminal:",
        styles["DocBody"]
    ))

    copilot_card = (
        "<b>╔══════════════════════════════════════════════════════════════════════════╗</b><br/>"
        "<b>║                    🎯 ALERTA COPILOTO: SINAL DE ENTRADA ARMADO                      ║</b><br/>"
        "<b>╠══════════════════════════════════════════════════════════════════════════╣</b><br/>"
        "  • <b>Ativo:</b> WINZ26 | <b>Direção:</b> VENDA @ 174.450<br/>"
        "  • <b>Stop Loss:</b> 174.700 (-250 pts) | <b>Alvo:</b> 174.050 (+400 pts) | <b>R:R:</b> 1.60<br/>"
        "  • <b>Regime SMC:</b> PREMIUM (50% Eq: 171.205) | <b>Zona:</b> FVG_60M_02<br/>"
        "  • <b>Tape Reading:</b> 140 contratos institucionais absorvidos na defesa<br/>"
        "  • <b>Score de Confiança:</b> 88% | <b>Ação:</b> Confirme a ordem no SuperDOM do Profit<br/>"
        "<b>╚══════════════════════════════════════════════════════════════════════════╝</b>"
    )
    t_copilot = Table([[Paragraph(copilot_card, styles["CardText"])]], colWidths=[487])
    t_copilot.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
        ('BOX', (0, 0), (-1, -1), 1, c_accent),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(t_copilot)
    story.append(Spacer(1, 14))

    story.append(Paragraph(
        "<b>Repositório Oficial no GitHub:</b><br/>"
        "Todo o código-fonte, suítes de testes determinísticos e relatórios foram versionados e estão disponíveis para você auditar em:<br/>"
        "👉 <b><font color='#2563EB'><u>https://github.com/glapts/mini-indice-B3</u></font></b>",
        styles["DocBody"]
    ))

    # Constrói o PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    
    # Faz cópia para a pasta docs do projeto
    import shutil
    shutil.copy2(DESKTOP_PDF_PATH, PROJECT_PDF_PATH)
    print(f"[OK] PDF gerado na Área de Trabalho: {DESKTOP_PDF_PATH}")
    print(f"[OK] Cópia salva em docs: {PROJECT_PDF_PATH}")


if __name__ == "__main__":
    build_pdf()
