---
name: cesta-juros-veto
description: Skill de veto de cesta e juros. Analisa correlação/divergência da cesta (PETR4, VALE3, Bancos) e estresse na curva de juros longa (DI1F29, DI1F31). Retorna VETO_COMPRA ou VETO_VENDA se houver divergência relevante nos ativos-peso ou pressão dos DIs contra a direção do setup.
---

# Skill: cesta-juros-veto

## Propósito
Camada desacoplada de filtro de contexto de cesta IBOV e curva de juros. Atua como guarda de segurança antes da liberação de alertas pelo Execution Harness.

## Escopo
- Analisar correlação/divergência da cesta (PETR4, VALE3, Bancos).
- Detectar estresse na curva de juros longa (DI1F29, DI1F31).
- Retornar contrato JSON padronizado com status `VETO_COMPRA` ou `VETO_VENDA` quando divergência relevante for identificada.

## Regras de negócio
1. **VALE3 e PETR4 caindo forte** (ambas < -0.80%) → `VETO_COMPRA`.
2. **VALE3 e PETR4 subindo forte em bloco** (ambas > 0.80% e ITUB4 > 0.50%) → `VETO_VENDA`.
3. **DI longo ou médio estressado** (>= +8.0 bps) → `VETO_COMPRA`.
4. **DI longo e médio em alívio** (<= -8.0 bps ambos) → `VETO_VENDA`.
5. **Conflito entre vetos** (compra e venda simultâneos) → `BLOCK`.
6. **Caso contrário** → `ALLOW`.

## Contrato de saída (JSON padronizado)
```json
{
  "skill": "cesta-juros-veto",
  "timestamp_brt": "YYYY-MM-DDTHH:MM:SS-03:00",
  "status": "ALLOW | BLOCK | VETO_COMPRA | VETO_VENDA | EMERGENCY_HALT",
  "motivo": "Explicação objetiva em 1 linha",
  "dados_stale": false
}
```

## Integração
Este módulo Python é desacoplado: não altera nenhuma fórmula matemática existente (`core/agents/basket_agent.py` permanece intacto). A skill consome os dados já populados pelo agente existente e emite um parecer adicional no contrato JSON padronizado.

## Módulo Python
`skill_cesta_juros.py` — implementa a classe `CestaJurosVetoSkill` com método `evaluate(current_time)` retornando `AgentOpinion` e método `to_json_contract()` retornando o contrato JSON acima.
