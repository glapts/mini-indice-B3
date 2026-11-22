---
name: sentinela-politico-emergencia
description: Skill de sentinela político-fiscal de emergência. Monitora manchetes de Brasília, risco fiscal e eventos de cauda (Black Swan). Retorna EMERGENCY_HALT imediato diante de notícia crítica ou ruído político capaz de distorcer o fluxo técnico.
---

# Skill: sentinela-politico-emergencia

## Propósito
Camada desacoplada de filtro de contexto político-fiscal. Atua como guarda de emergência antes da liberação de alertas pelo Execution Harness.

## Escopo
- Monitorar manchetes de Brasília, risco fiscal e eventos de cauda (Black Swan).
- Detectar palavras-chave críticas (meta fiscal, estatização, intervenção, calote, impeachment, etc.).
- Retornar contrato JSON padronizado com status `EMERGENCY_HALT` imediato diante de notícia crítica.

## Regras de negócio
1. **Notícia com palavra-chave Black Swan detectada** → `EMERGENCY_HALT` com trava de 30 minutos.
2. **Alerta de cisne negro expirado** → retorna ao estado normal (`ALLOW`).
3. **Sem notícias críticas** → `ALLOW`.

## Palavras-chave monitoradas
meta fiscal, alteracao da meta, estatizacao, intervencao na petrobras, intervencao na vale, demissao de ministro, demissao de campos neto, demissao do presidente do bc, crise institucional, calote, rombo fiscal, contingenciamento bilionario, estado de calamidade, impeachment.

## Contrato de saída (JSON padronizado)
```json
{
  "skill": "sentinela-politico-emergencia",
  "timestamp_brt": "YYYY-MM-DDTHH:MM:SS-03:00",
  "status": "ALLOW | BLOCK | VETO_COMPRA | VETO_VENDA | EMERGENCY_HALT",
  "motivo": "Explicação objetiva em 1 linha",
  "dados_stale": false
}
```

## Integração
Este módulo Python é desacoplado: não altera nenhuma fórmula matemática existente (`core/agents/sentinel_agent.py` permanece intacto). A skill consome os dados já populados pelo agente existente e emite um parecer adicional no contrato JSON padronizado.

## Módulo Python
`skill_sentinela.py` — implementa a classe `SentinelaPoliticoEmergenciaSkill` com método `evaluate(current_time)` retornando `AgentOpinion` e método `to_json_contract()` retornando o contrato JSON acima.
