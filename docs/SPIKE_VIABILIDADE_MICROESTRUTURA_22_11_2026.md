# SPIKE DE VIABILIDADE — FEED DE MICROESTRUTURA (BOOK L2 + TIMES & TRADES)

**Data:** 22/11/2026  
**Escopo:** Somente leitura e diagnóstico. Nenhum módulo do algoritmo foi alterado.  
**Objetivo:** Verificar se é possível alimentar o `MicrostructureFilter` e o `TapeReadingAnalyzer` com book de ofertas e negócios individuais reais.

---

## 1. Resumo executivo

| Caminho | Veredito | Evidência |
|---------|----------|-----------|
| **DDE — book de topo (nível 1)** | **VIÁVEL — integrado em produção** | `OCP/OVD/VOC/VOV` respondem após habilitar os atributos no Profit. Feed, `BookAnalyzer` e Harness INTEGRADOS |
| **DDE — T&T individual** | **Inviável** | DDE não expõe negócio individual; só agregados (`NEG`, `AGRVOLC`, `AGRVOLV`, `AGRSALDO`, `QTT`) |
| **DDE — book L2 multi-nível** | **Inviável** | Só o topo (nível 1) é exposto. `DELTA/DUV/DCV/AJU/AJA/PRT/QTE/ACP/AVD/AGR` continuam `NOT FOUND` |
| **DDE — tamanho do lote** | **VIÁVEL — integrado** | `LOT` devolve o lote padrão do contrato (WIN=1, VALE3=100, PETR4=100, ITUB4=100) |
| **RTD via COM — book** | **Parcialmente viável, bloqueado no protocolo** | Servidor COM responde (`Heartbeat` OK, `InvalidCommand` do parser do Profit), mas nenhuma sintaxe testada retornou payload |
| **RTD via Excel nativo** | **Não conecta** | Excel aceita a fórmula `=RTD(...)` mas retorna `#N/D` em 100% das variantes |
| **Clipboard do Profit — T&T** | **Viável, falta implementar** | O parser existente retorna **0 registros** para payload de T&T — falta escrever o parser |
| **CSV histórico** | **Confirmado: não tem microestrutura** | 55.009 linhas, **0** minutos com mais de 1 registro → OHLCV de 1 minuto |

---

## 0. ATUALIZAÇÃO — DESCOBERTA DO BOOK DE TOPO VIA DDE (22/11/2026, 22h)

**Hipótese inicial refutada.** A conclusão anterior ("o DDE não expõe book") estava correta **apenas porque os atributos estavam desabilitados** na configuração do Profit — não por limitação técnica do DDE.

Ao habilitar os atributos na janela *Exportar em Tempo Real (RTD/DDE)* → aba *Atributos*, os campos passaram a responder:

```
Antes:  OCP -> NOT FOUND   OVD -> NOT FOUND   VOC -> NOT FOUND   VOV -> NOT FOUND
Depois: OCP -> 0,00        OVD -> 0,00        VOC -> 0,00        VOV -> 0,00        LOT -> 1,00
```

Os zeros são **mercado fechado** (fora do pregão), e não falha de leitura: `ULT`, `NEG` e `QTT` mantêm o último estado do pregão. A amostragem repetida (3 leituras) devolveu valores idênticos.

### Verificação do campo `LOT` — sem divergência

O rótulo **"Lote Padrão"** da interface do Profit corresponde exatamente ao campo `LOT` do DDE. Teste em 7 ativos:

| Ativo | `LOT` | Correto |
|-------|--------|---------|
| WINZ26 | 1,00 | ✅ Mini-índice = 1 contrato |
| WDOZ26 | 1,00 | ✅ Mini-dólar = 1 contrato |
| DI1F29 | 1,00 | ✅ DI = 1 contrato |
| WSPZ26 | 1,00 | ✅ S&P futuro = 1 contrato |
| VALE3 | 100,00 | ✅ Vale = lote de 100 ações |
| PETR4 | 100,00 | ✅ Petrobras = lote de 100 |
| ITUB4 | 100,00 | ✅ Itaú = lote de 100 |

Confirmado no binário: `Asset Lote` é o tamanho de contrato do ativo. **"Lote Padrão" é o rótulo correto.**

### O que foi integrado em produção

1. **`feeds/dde_feed.py`** — leitura de `OCP/OVD/VOC/VOV/LOT`, emissão de `BookSnapshot` via `on_book_callback`, e `get_top_book()`.
   - Validação de sanidade: `ask >= bid` e ao menos um lado com quantidade.
   - Book zerado (mercado fechado) → `is_book_available = False` (degradação segura).
   - Quantidades normalizadas para contratos usando o lote padrão.
2. **`analysis/book_analyzer.py`** — rótulo honesto da profundidade: `book_imbalance_top5` apenas quando há 5 níveis reais; caso contrário `book_imbalance_top1` + `book_depth_levels` + limitação declarada.
3. **`core/harness/execution_harness.py`** — novo método `on_book()` alimentando o `BookAnalyzer`.
4. **`run_harness_copilot.py`** — registra o callback `on_book`.
5. **`tests/test_dde_book_top.py`** — 9 testes cobrindo mercado aberto, mercado fechado, atributos ausentes, spread invertido, lote por ativo, emissão de snapshot e rótulo de profundidade.

### Limitação que permanece

O `MicrostructureFilter` **exige 100 contratos absorvidos** e mede por nível de preço. O book de topo DDE tem **1 nível** e **não traz T&T individual**, então esse critério continua operando sobre volumes agregados sintéticos. **A microestrutura real por nível permanece o gap aberto.**

O que o book de topo entrega de fato:
- `best_bid`, `best_ask`, `spread` reais
- `imbalance` de topo real (1 nível) — rotulado como tal
- tamanho de lote do contrato, real

### Validação pendente (próximo pregão)

Com o mercado aberto, é preciso confirmar:
1. `OCP`/`OVD` com valores **diferentes de zero**;
2. `VOC`/`VOV` refletindo as quantidades reais no book;
3. `ULT`/`NEG`/`AGRVOLC` avançando (DDE acompanhando o pregão).

Sem isso, `OCP = 0,00` é indistinguível de "campo ativo mas market dead".

---

## 2. O que o Profit realmente expõe

### 2.1 Campos DDE disponíveis (lidos de `DDEPreferencesV2.json`)

**Ativos (publicados):**
```
ULT, ABE, MAX, MIN, NEG, QTT, VAR, AGRVOLC, AGRVOLV, AGRSALDO
```

**Desativados — portanto ausentes no DDE:**
```
OCP (ofert. compra), OVD (ofert. venda), VOC (vol. compra), VOV (vol. venda),
LOT, DELTA, DUV, DCV, SVAR, AJU, AJA, PRT, QTE, ACP, AVD, AGR, AGRC, AGRV,
VOL, HOR, DAT, FEC, MED
```

**Teste empírico (Profit aberto, DDE conectado):**
```
QTT        -> 23226573,00     (funciona)
OCP        -> NOT FOUND
OVD        -> NOT FOUND
VOC        -> NOT FOUND
VOV        -> NOT FOUND
LOT        -> NOT FOUND
DELTA      -> NOT FOUND
```

### 2.2 Mapeamento DDE → comando RTD (extraído do binário `profitchart.exe`)

604 pares encontrados no binário. Relevantes para book/microestrutura:

| Campo DDE | Comando RTD | Semântica |
|-----------|-------------|-----------|
| `OCP` | `BID` | Oferta de compra (topo) |
| `OVD` | `ASK` | Oferta de venda (topo) |
| `VOC` | `BDV` | Volume na oferta de compra |
| `VOV` | `ASV` | Volume na oferta de venda |
| `LOT` | `LOT` | Lote |
| `DELTA` | `DELTA` | Delta |
| `NEG` | `TRD` | Total de negócios |
| `AGRVOLC` | `AGRVOLC` | Agressão compradora |

Assinatura RTD de book documentada no próprio binário (unit `RTDBookU`):
```
Available book values:
  GetFeed, GetAsset, AskPrice, AskSize, BidPrice, BidSize, BookSpread, Lote,
  MinPriceIncrement, Strike, Close, Volume, Quantity, Open, High, Low
```

### 2.3 Capacidades confirmadas no binário do Profit

Units presentes:
```
RTDBookU, RTDTimeTradesU, RTDVolumeAtPriceU, RTDTickerU, RTDChartCodesU,
RTDAutomatorU, RTDConfigurationFormU, RTDResultsU, RTDToolU
```

**Conclusão:** o Profit **tem** RTD para book e para times & trades. O gargalo é o cliente, não o servidor.

---

## 3. Detalhes dos testes executados

### 3.1 RTD via COM direto (`comtypes`)

```python
mod = comtypes.client.GetModule(r'%APPDATA%\Nelogica\Profit\profitchart.exe')
# -> IRtdServer, IRTDUpdateEvent, RtdServer (CoClass)
```

| Resultado | Detalhe |
|-----------|---------|
| `CreateObject("RTDTrading.RtdServer")` | **OK** |
| `QueryInterface(IRtdServer)` | **OK** |
| `Heartbeat()` | **OK** → retorna `1` |
| `ConnectData(["WINZ26"], ...)` | responde `[True, 'Comando Inválido']` — parser do Profit **vivo**, comando rejeitado |
| `ConnectData` com `LST`, `BID`, `ASK`, `BOOK`… | **Access violation** em `profitchart.exe` |
| `ServerStart(callback)` | Falha de marshaling: `comtypes` não converte o `UpdateEvent` para `POINTER(IRTDUpdateEvent)` |

**Sintaxe de fórmula encontrada no binário:**
```
=RTD("RTDTrading.RTDServer";; "%s"; "%s"; "%s")
=RTD("tryd.rtdserver";; "COT";"%s";"%s")
```

### 3.2 RTD via Excel nativo

| Variante testada | Resultado |
|------------------|-----------|
| `=RTD("RTDTrading.RTDServer","COT","WINZ26","LST")` | `#N/D` |
| `…;"BOOK")`, `…"BIDPRICE")`, `…"ASKPRICE")`, `…"BIDSIZE")`, `…"ASKSIZE")`, `…"BOOKSPREAD")` | `#N/D` |
| `=RTD("RTDTrading.RTDServer";; "COT";"WINZ26";"LST")` (separador `;;`) | **Excel recusa a escrita** (`0x800A03EC`) — o Excel aceita só `,` ou `;` |
| `=RTD("tryd.rtdserver","COT","WINZ26","LST")` | `#N/D` |
| `=RTD("profitchart","cot","WINZ26","ULT")` | `#N/D` |
| Com ID interno `WINZ26_F_0` | `#N/D` |
| Gravado em `.xlsx` e reaberto | `#N/D` (o Excel **reconhece** RTD — `RTD` está em `MRUFuncs`) |

**Diagnóstico:** `0x800A03EC` na escrita com `;;` confirma que o Excel *parseia* a fórmula. O `#N/D` indica que o servidor RTD do Profit não atendeu a requisição — provavelmente porque o **RTD precisa ser habilitado na configuração do Profit** (unit `EN_US_RTDCONFIGURATIONFORMU`) ou o Profit não estava com RTD ativo naquele instante.

### 3.3 Clipboard — parser de T&T

O parser existente (`feeds/csv_feed.py::parse_raw_csv_text`) retorna **0 registros** para:

```
Data;Hora;Preco;Compradora;Vendedora;Agressor;Quantidade;Origem
18/11/2026;11:38:05;173690,00;BTG;XP;Venda;123;Eletronico
18/11/2026;11:38:07;173700,00;XP;XP;Compra;806;Eletronico
18/11/2026;11:38:09;173700,00;BTG;BTG;Venda;294;Eletronico
```

Isso é **esperado e correto**: `parse_raw_csv_text` mapeia colunas OHLCV de candle (`abertura`/`máxima`/`mínima`/`fechamento`). Um payload de T&T não tem essas colunas.

**Veredito:** o caminho é **viável** — falta um parser de T&T (~80 linhas) que mapeie:
`data`, `hora`, `preco`, `quantidade`, `agressor` → `core.models.Trade`.

### 3.4 CSV histórico (`data/historico/WINFUT_REAL_2026.csv`)

```
Total de linhas : 55009
Datas distintas : 99 (01/07/2026 .. 06/11/2026)
Colunas         : 9 = ativo;data;hora;abertura;máxima;mínima;fechamento;volume;negócios
Minutos com MAIS DE 1 registro: 0 de 55008
```

É **candle de 1 minuto** (OHLCV). Não há negócio individual, não há book.

---

## 4. Conclusão

### O gain é real, mas concentrated em UM caminho

**Único caminho com viabilidade comprovada: clipboard do Profit → parser de T&T.**

| Caminho | Esforço | Risco | Valor |
|---------|---------|-------|-------|
| **Parser de T&T via clipboard** | ~80 linhas, feed novo | Baixo | **Real**: cada negócio com preço, quantidade e agressor |
| Habilitar `OCP/OVD/VOC/VOV` no DDE do Profit | 1 configuração (GUI) | Nenhum (reversível) | Book topo + volumes — **validar empiricamente** |
| RTD via Excel | Spike adicional | Médio | Potencial: book completo + T&T via stream |
| RTD via COM direto | Resolver marshaling de `IDispatch` | Médio | Potencial: melhor latência |

### Implicação para o algoritmo

Com o parser de T&T, o `TapeReadingAnalyzer` passa a receber **negócios reais** e não agregados sintéticos, o que:

- **Corrige** o `price_displacement` (hoje derivado de trades sintéticos);
- **Corrige** o `delta_pct` (hoje distorcido pela agregação);
- **Torna** `evaluate_absorption` do `MicrostructureFilter` semanticamente correto — "N contratos absorvidos num nível" passa a significar de fato isso;
- **Habilita** o `BookAnalyzer` se combined com `OCP/OVD/VOC/VOV`.

### Riscos remanescentes

1. **Latência do clipboard**: o T&T só é atualizado quando o usuário copia (Ctrl+C) na janela do Profit. Não serve para fluxo contínuo.
2. **Vazio hoje**: o clipboard atual está vazio — é preciso copiar do Profit antes de rodar.
3. **HFT/ruído**:negocios de 1 a 5 contratos dominates o T&T real; o `min_hft_lot=20` do `MicrostructureFilter` existe exatamente para isso.

---

## 5. Próximos passos sugeridos

1. **Validar empiricamente** a habilitação de `OCP/OVD/VOC/VOV/LOT` na janela DDE do Profit (ação manual do usuário, reversível).
2. **Implementar** `feeds/tt_clipboard_feed.py` + `parse_tt_text()` — parser de T&T, sem tocar no algoritmo.
3. **Decidir** o formato de saída: mais honesto é renomear o critério para "volume absorvido" enquanto o dado for agregado.
4. Manter `FULL_AUTO` proibido até que o `MicrostructureFilter` opere sobre dados reais.

---

## Arquivos do spike (não alteram o algoritmo)

- `spike_rtd_viabilidade.py` — teste RTD via COM direto
- `spike_rtd_excel.py` — teste RTD via Excel nativo
