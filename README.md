# Assistente de Análise do Mini-Índice WIN — Profit Pro
### Arquitetura Multi-Agente & Execution Harness Determinístico (SMC & Microestrutura B3)

Solução modular e determinística orientada a dados verificáveis para leitura, monitoramento e geração de alertas operacionais no mini-índice futuro da B3 (**WIN**).

---

## ⚡ Execução Rápida (1-Clique)

O sistema opera com separação estrita entre **Inteligência Contextual (Agentes Assíncronos)** e **Execução Determinística (Sub-milissegundo)**:

1. **Terminal 1 — Inteligência & Clima de Mercado:**
   * Dê dois cliques em `EXECUTAR_ORQUESTRADOR_AGENTES.bat` (ou execute `python run_orchestrator.py`).
   * Monitora S&P 500, Treasuries, Payroll/FOMC, Blue Chips (PETR4/VALE3), Curva DI e Notícias de Brasília, atualizando `data/runtime_state.json`.

2. **Terminal 2 — Execution Harness (Modo Copiloto / Assistido):**
   * Dê dois cliques em `EXECUTAR_HARNESS_COPILOTO.bat` (ou execute `python run_harness_copilot.py --mode COPILOT`).
   * Conecta ao Profit Pro via DDE, aplica a regra de **Premium & Discount (50% Equilibrium)** sobre as zonas de 60m (`data/niveis_60m.json`), filtra ruídos de HFT (<20 lotes) e emite alertas visuais e sonoros no SuperDOM.

---

## 1. Diagnóstico do Ambiente & Integração Profit Pro

Durante a inspeção técnica realizada no computador local (Windows 11 Pro 64-bit), identificamos:

* **Nelogica Profit Pro instalado e ativo:**
  * **Versão:** `5.0.4.32 (64-bit)`
  * **Caminho:** `C:\Users\glaci\AppData\Roaming\Nelogica\Profit\profitchart.exe`
  * **Instância em execução:** Processo PID `21120`, Janela Principal: `ProfitPro - 5.0.4.32 - Registrado`
  * **Módulos visíveis no layout:** Gráfico 60m (`WINZ26`), Livro de Ofertas (`TBookMDIForm`), Times & Trades (`TTimesTradesForm`), Painel Chart Trading.

### Comparativo Técnico dos Métodos de Integração

| Método de Integração | Status no Computador | Disponibilidade de Fluxo (Book L2 + T&T) | Latência Estimada | Custo / Requisitos | Resultado dos Testes Locais |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **A. ProfitDLL / DataFeed SDK** | **Bloqueado** | Sim (Completo, tick-a-tick e L2) | Baixa (< 5ms) | Módulo B2B Nelogica (Chave e contrato institucional) | Arquivos `ProfitDLL64.dll` e `ProfitDataFeed.dll` **não encontrados** no sistema. A assinatura padrão do Profit Pro não inclui o SDK. |
| **B. DDE (Dynamic Data Exchange)** | **Conectado e Operacional** | Parcial (Cotações agregadas da sessão) | Média (~ 100ms - 1s) | Gratuito (Nativo do Profit Pro) | Conexão estabelecida com sucesso com `profitchart\|cot`. Requer configuração de tabela no Profit. |
| **C. RTD (Real-Time Data / COM)** | **Registrado** | Parcial (Cotações de topo e resumo) | Média (~ 500ms) | Gratuito (Nativo do Profit Pro) | ProgID `RTDTrading.RtdServer` registrado e apontando para o binário do Profit. |
| **D. NTSL (Nelogica Strategy Language)** | **Disponível** | Não (Sem sockets / sandbox) | Interna | Gratuito (Nativo do Profit Pro) | Executável dentro do Profit para coloração/alarmes, mas sem exportação estruturada externa. |
| **E. Bridge Externa Autorizada (MT5 B3 / DMA)** | **Disponível na máquina** | Sim (Completo, Book L2 + Ticks) | Baixa (< 10ms) | Gratuito (via conta demo/real de corretora homologada B3) | Terminal MT5 identificado no sistema (`FX Globe International MetaTrader 5`). |

---

## 2. Instruções de Execução (Comandos Copiáveis)

O assistente foi construído em Python 3.14 x64 sem dependências de compilação C++, utilizando o ambiente já instalado no sistema.

### Passo 1: Executar Diagnóstico de Conexão
Verifica os processos do Profit, a conexão DDE nativa e a integridade do ambiente:
```powershell
python C:\Users\glaci\Projetos\mini-indice-B3\main.py diagnose
```

### Passo 2: Teste de Replay & Validação dos 9 Setups
Executa uma simulação com os 7 tempos gráficos (1m, 2m, 5m, 10m, 15m, 30m e 60m), injeta sweeps e valida o motor determinístico:
```powershell
python C:\Users\glaci\Projetos\mini-indice-B3\main.py test-replay
```

### Passo 3: Backtest Quantitativo Fora da Amostra
Avalia os setups em múltiplas sessões simuladas, incluindo custos da B3 (R$ 0,60 round-trip) e slippage de 1 tick (5 pontos):
```powershell
python C:\Users\glaci\Projetos\mini-indice-B3\main.py backtest --mode FIXO
```

### Passo 3.1: Teste em Lote de Múltiplos Pregões Reais (Batch Backtest)
Permite carregar e testar múltiplos dias exportados do Profit Pro em lote (pasta inteira, arquivo de 30 dias ou captura contínua via Clipboard):
```powershell
# Executa nos arquivos da pasta data/historico:
python C:\Users\glaci\Projetos\mini-indice-B3\main.py batch-replay --dir data/historico --contracts 5

# Ou via arquivo específico com múltiplos dias:
python C:\Users\glaci\Projetos\mini-indice-B3\main.py batch-replay --file "caminho/do/arquivo.csv"

# Ou via menu interativo de 1 clique:
C:\Users\glaci\Projetos\mini-indice-B3\EXECUTAR_REPLAY_LOTE.bat
```

### Passo 4: Executar Monitoramento ao Vivo via DDE
Para conectar ao Profit Pro em tempo real:
1. Abra o **Profit Pro**.
2. Acesse o menu: **Ferramentas -> Exportar em tempo real (DDE / RTD)**.
3. Certifique-se de que os ativos desejados estão adicionados na tabela:
   - **WINZ26** (Mini-Índice)
   - **WDOZ26** (Mini-Dólar)
   - **VALE3** (Vale S.A.)
4. No terminal PowerShell, execute o monitoramento do ativo desejado:

#### Monitorar Mini-Índice (WIN):
```powershell
python C:\Users\glaci\Projetos\mini-indice-B3\main.py run-dde --symbol WIN
```

#### Monitorar Mini-Dólar (WDO):
```powershell
python C:\Users\glaci\Projetos\mini-indice-B3\main.py run-dde --symbol WDO
```

#### Monitorar Ações Vale (VALE3):
```powershell
python C:\Users\glaci\Projetos\mini-indice-B3\main.py run-dde --symbol VALE3
```

---

## 3. Especificações Técnicas e Parâmetros

### Ativo e Contrato Mini-Índice B3
* **Ticker Base:** `WIN`
* **Vencimentos:** Meses pares (`G` = Fev, `J` = Abr, `M` = Jun, `Q` = Ago, `V` = Out, `Z` = Dez). Vence na quarta-feira mais próxima do dia 15 do mês de vencimento.
* **Tick Mínimo:** 5 pontos.
* **Valor por Ponto:** R$ 0,20 por contrato.
* **Fuso Horário:** `America/Sao_Paulo` (UTC-3).

### Estrutura de Mercado Multi-Timeframe (Sem Médias Móveis)
* **Hierarquia e Radar de FVGs Antigos:**
  * **240m (4h), 60m e 30m:** Contexto Macro e Zonas Institucionais de Reversão (200 a 300 pts).
  * **15m e 10m:** Estrutura Intermediária e Liquidez Local.
  * **5m:** Preparação.
  * **2m e 1m:** Gatilho e Timing.
  * **Radar MTF de FVGs Antigos Não Liquidados:** Mantém em memória zonas de FVG de 10m, 15m, 30m, 60m e 240m que ainda não foram liquidadas por completo (rompidas). Dispara **Alerta Antecipado** no PowerShell com raio de aproximação de 100 a 150 pontos antes do toque na zona ou no nível de 50% (CE) com cores ANSI de alto contraste (Amarelo no rótulo de 50% CE, Vermelho para Venda e Verde para Compra).
* **Ausência de Look-Ahead Bias:** Pivôs exigem confirmação estrita de barras à direita (2 barras fechadas) antes de serem validados para quebras estruturais.
* **FVG (Fair Value Gap):** Requer 3 candles fechados. Mínima da barra 3 acima da máxima da barra 1 (alta) ou máxima da barra 3 abaixo da mínima da barra 1 (baixa). Tamanho mínimo de 10 pontos.
* **FVG de Deslocamento & 50% Consequent Encroachment (C.E.):** Identifica velas de deslocamento com corpo $\ge 180$ pts no 1m/2m e $\ge 220$ pts no 5m+, calculando o reteste no ponto médio matemático de 50% (*Consequent Encroachment*).
* **Deslocamento:** Corpo relativo $\ge 1.8 \times$ a mediana recente dos corpos das barras (mínimo 50 pontos), sem uso de médias móveis.
* **Os 10 Setups Canônicos:**
  1. Compra de Continuidade em Tendência de Alta (Recuo em FVG Clássico).
  2. Venda de Continuidade em Tendência de Baixa (Retração em FVG Clássico).
  3. Compra após Sweep de Mínima (Falso Rompimento com Absorção).
  4. Venda após Sweep de Máxima (Falso Rompimento com Absorção).
  5. Reversão Confirmada de Fundo (CHoCH de Alta).
  6. Reversão Confirmada de Topo (CHoCH de Baixa).
  7. Operação Longa após Sweep em Tempos Maiores (60m, 30m, 15m).
  8. Extremos de Consolidação (Piso e Teto de Caixote, centro bloqueado).
  9. Reteste de 50% do FVG de Deslocamento (Consequent Encroachment C.E. com BOS) em 1m, 2m, 5m, 10m, 15m, 30m e 60m.
  10. Defesa Institucional em Topos e Fundos antes de Romper (SMC Premium/Discount + Rejeição de Pavio/Desbalanceamento no 1m + Book L2 + Times & Trades).

### Tape Reading, Book de Ofertas & Terminal Visual
* **Visualização Semafórica ANSI no PowerShell:**
  * **Agressão Compradora:** Linha inteira destacada em **Verde Brilhante**.
  * **Agressão Vendedora:** Linha inteira destacada em **Vermelho Brilhante**.
  * **Delta:** Colorido conforme polaridade (+Verde / -Vermelho).
  * **Grandes Agressões:** Destaque visual individual para execuções $\ge 100$ contratos (`(BUY)` em verde e `(SELL)` em vermelho).
* **Book L2:** Monitoramento de desequilíbrio (Imbalance) no Top 5 e rastreamento de ordens volumosas retiradas rapidamente ao aproximar do preço.
* **Classificações permitidas para o Book:**
  * `Comportamento de oferta observado`
  * `Padrão compatível com possível blefe`
  * `Evidência insuficiente`
  * `Análise indisponível por limitação dos dados`
  *(NUNCA emite "spoofing confirmado").*

### Gerenciamento de Risco e Execução via SuperDOM
* **Lote Padrão de Referência:** 5 contratos (5 lotes) = **R$ 1,00 por ponto** (Stop = -R$ 250,00 | Alvo = +R$ 400,00).
* **Modo Fixo:** Stop de 250 pontos e Alvo de 400 pontos. Retorno/Risco bruto: **1,60**. Ponto de equilíbrio estatístico: **38,46%** (com 7 vitórias e 6 derrotas em 13 operações = +R$ 1.300,00 líquidos).
* **Modo Estrutural:** Stop no pivô técnico/invalidação do sweep e alvo projetado em $1,6 \times$ o stop técnico.
* **Interface Preferencial de Execução:** **SuperDOM** (Profit Pro) com estratégia OCO pré-configurada (`50 ticks Loss / 80 ticks Gain`).
* **Formatação Visual do Disparo:** Todos os preços emitidos no terminal exibem pontuação de milhar (ex.: `170.320`, `170.570`, `169.920`) para garantir clareza e rapidez no posicionamento da ordem.
* **Regra de Bloqueio:** Quando não houver confluência suficiente ou o preço estiver no centro de caixotes (entre 15% e 85%), o sistema emite estritamente: **SEM OPERAÇÃO — AGUARDAR**.

---

## 4. Pendências Objetivas

1. **Ativação da Exportação DDE no Profit:** Como o Profit Pro restringe a transmissão DDE à tabela aberta pelo usuário, é necessário manter aberta a janela de exportação DDE no menu do Profit durante o pregão.
2. **Habilitação de Book L2 Completo:** Para ter rastreamento milissegundo de cancelamentos do Book de Ofertas e Times & Trades completo com corretoras agressores, o usuário tem duas opções:
   * **Opção Institucional:** Contratar formalmente a chave do SDK **ProfitDLL / Market Data** junto à Nelogica.
   * **Opção Gratuita Homologada:** Conectar uma conta de mercado B3 (demo ou real gratuita de corretora como XP, Genial ou BTG) via **MetaTrader 5 Python API**, que disponibiliza todo o DOM e ticks da B3 sem custo adicional.
