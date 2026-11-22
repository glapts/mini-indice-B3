---
name: macro-global-guard
description: Skill de guarda macroeconômica global. Monitora S&P 500, Treasuries, DXY e calendário econômico dos EUA (Payroll, FOMC, CPI). Retorna BLOCK se houver evento de alto impacto na janela operacional ou dados desatualizados (STALE).
---

# Skill: macro-global-guard

## Propósito
Camada desacoplada de filtro de contexto macroeconômico global. Atua como guarda de segurança antes da liberação de alertas pelo Execution Harness.

## Escopo
- Monitorar S&P 500, Treasuries (US 10Y), DXY e calendário econômico dos EUA.
- Detectar eventos de alto impacto (Payroll, FOMC, CPI) em janela operacional.
- Detectar dados desatualizados (STALE) do feed externo.
- Retornar contrato JSON padronizado com status `BLOCK` quando condições de risco forem identificadas.

## Regras de negócio
1. **Evento de calendário em andamento** → `BLOCK` com motivo descritivo do evento.
2. **Janela de abertura de Wall Street** (10:28–10:35 e 11:28–11:35 BRT) → `BLOCK`.
3. **Dados macro desatualizados** (feed externo excedeu TTL de 120s) → `BLOCK`.
4. **S&P 500 caindo forte ou Treasuries disparando** → `VETO_COMPRA` (não é BLOCK total, restringe direção).
5. **S&P 500 subindo forte e DXY caindo** → `VETO_VENDA`.
6. **Caso contrário** → `ALLOW`.

## Contrato de saída (JSON padronizado)
```json
{
  "skill": "macro-global-guard",
  "timestamp_brt": "YYYY-MM-DDTHH:MM:SS-03:00",
  "status": "ALLOW | BLOCK | VETO_COMPRA | VETO_VENDA | EMERGENCY_HALT",
  "motivo": "Explicação objetiva em 1 linha",
  "dados_stale": false
}
```

## Integração
Este módulo Python é desacoplado: não altera nenhuma fórmula matemática existente (`core/agents/macro_agent.py` permanece intacto). A skill consome os dados já populados pelo agente existente e emite um parecer adicional no contrato JSON padronizado.

## Módulo Python
`skill_macro_global.py` — implementa a classe `MacroGlobalGuardSkill` com método `evaluate(current_time)` retornando `AgentOpinion` e método `to_json_contract()` retornando o contrato JSON acima.
