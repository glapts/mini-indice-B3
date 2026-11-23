# PLANO DE EXECUÇÃO — TESTE EM CONTA REAL (COPILOT)

**Data:** 23/11/2026 (segunda-feira)  
**Projeto:** `C:\Users\glaci\Projetos\mini-indice-B3`  
**Modo:** COPILOT (apenas alertas, sem ordem automática)  
**Automação:** NENHUMA ordem automática será enviada pelo sistema

---

## Objetivo

Validar monitoramento e bloqueios do sistema no primeiro pregão real, sem operar dinheiro real com automação.

---

## Componentes envolvidos

| Componente | Arquivo | Especialidade |
|------------|---------|---------------|
| Orquestrador de Agentes | `run_orchestrator.py` | Consolida 3 agentes especialistas e grava `data/runtime_state.json` |
| Agente Macro & Global | `core/agents/macro_agent.py` | S&P 500, Treasuries, DXY, Calendário EUA (Payroll, FOMC, CPI) |
| Agente Cesta & Curva | `core/agents/basket_agent.py` | PETR4, VALE3, Bancos, DI longo (DI1F29, DI1F31) |
| Agente Sentinela | `core/agents/sentinel_agent.py` | Notícias de Brasília, risco fiscal, Black Swan |
| Execution Harness | `run_harness_copilot.py` | Conecta ao Profit via DDE, aplica Gatekeeper, emite alertas |

---

## Pré-requisitos (antes de rodar qualquer comando)

1. Profit Pro **aberto**, logado e com conexão de mercado ativa.
2. Tabela de exportação **DDE/RTD aberta** com os ativos:
   - Contrato WIN vigente (ex: `WINZ26`)
   - `VALE3`
   - `PETR4`
   - `ITUB4`
   - `DI1F29`
   - `DI1F31`
3. **Aba "Atributos" da janela Exportar em Tempo Real — marcar também:**
   - `Oferta de Compra` (OCP)
   - `Oferta de Venda` (OVD)
   - `Volume Oferta Compra` (VOC)
   - `Volume Oferta Venda` (VOV)
   - `Lote Padrão` (LOT)

   Sem esses cinco atributos o book de topo não chega ao algoritmo.
4. Arquivo `data/niveis_60m.json` válido e com contrato do vencimento vigente.
5. Arquivo `data/runtime_state.json` existente (será sobrescrito pelo Orquestrador).

---

## Comandos do dia

### Passo 1 — Abrir PowerShell na pasta do projeto

```powershell
cd "C:\Users\glaci\Projetos\mini-indice-B3"
```

### Passo 2 — Terminal 1: Orquestrador de Agentes

```powershell
$env:PYTHONIOENCODING="utf-8"
python run_orchestrator.py --interval 10 --mode COPILOT
```

O que deve aparecer:
- Ciclos seguindo sem traceback
- `OPERAÇÃO LIBERADA` ou `OPERAÇÃO BLOQUEADA`
- Mensagem de bloqueio quando aplicável

### Passo 3 — Terminal 2: Execution Harness (após o Orquestrador estar rodando)

```powershell
$env:PYTHONIOENCODING="utf-8"
python run_harness_copilot.py --symbol WIN --mode COPILOT
```

O que deve aparecer:
- `MODO COPILOT`
- `Conexão iniciada! Monitorando fluxo institucional em tempo real...`
- Alertas sonoros e visuais quando houver setup

### Passo 4 — Consultar estado em tempo real (opcional, em outro PowerShell)

```powershell
Get-Content ".\data\runtime_state.json"
```

---

## Regras obrigatórias

| Regra | Detalhe |
|-------|---------|
| Modo obrigatório | `COPILOT` apenas |
| `FULL_AUTO` | **PROIBIDO** nesta fase |
| `.bat` de automação | Utilizar `EXECUTAR_ORQUESTRADOR_AGENTES.bat` ou rodar via PowerShell |
| Ordens automáticas | Nenhuma ordem será enviada pelo sistema |
| Ordens manuais | Por sua conta e risco, validadas manualmente |
| Encerramento | `Ctrl+C` nos dois terminais |
| Commit de dados | Não commitar arquivos em `data/` sem revisar |

---

## O que validar durante o teste

- [ ] Orquestrador permanece ativo sem traceback
- [ ] `data/runtime_state.json` é atualizado a cada ciclo
- [ ] `trading_enabled` corresponde ao bloqueio observado
- [ ] Harness permanece conectado ao DDE
- [ ] Modo continua `COPILOT`
- [ ] Dados obsoletos (`STALE`) bloqueiam a operação
- [ ] Nenhum sinal duplicado observado
- [ ] Nenhuma ordem automática enviada
- [ ] Estado persistido continua consistente

---

## Limitação conhecida

O DDE agora entrega **book de topo (nível 1)** — melhor oferta de compra/venda, volumes
nessas ofertas, spread, imbalance de topo e tamanho do lote do contrato. Esses dados
alimentam o `BookAnalyzer` e aparecem na seção `BOOK:` do alerta.

**O que continua indisponível via DDE:**

- Book L2 multi-nível (o DDE expõe só o nível 1) — por isso o alerta rotula
  `Imbalance Top1` e informa `Níveis observados: 1`
- Times & Trades individual (só agregados: `NEG`, `AGRVOLC`, `AGRVOLV`, `AGRSALDO`)

Consequência: o `MicrostructureFilter` (que exige 100 contratos absorvidos por nível)
continua operando sobre volumes agregados. **Não tratar o critério de absorção como
microestrutura real neste teste.**

## Validação específica do book no primeiro ciclo

Nos primeiros minutos de pregão, confirme em outro PowerShell:

```powershell
python test_dde_query.py
```

Esperado: `WINZ26.OCP` e `WINZ26.OVD` com valores **diferentes de zero** e
`WINZ26.LOT` = `1,00` para o mini-índice. Se vierem zerados, o book não está
publicado e o sistema segue degradando com segurança (alerta sem book).

---

## Arquivos gerados durante o teste (não commitar sem revisão)

- `data/runtime_state.json`
- `data/latest_alert.txt`
- `data/latest_alert_win.txt`
- `data/sinais_copiloto.json`

---

## Como encerrar

1. PowerShell do Harness: `Ctrl+C`
2. PowerShell do Orquestrador: `Ctrl+C`
3. Confira: `git status`
