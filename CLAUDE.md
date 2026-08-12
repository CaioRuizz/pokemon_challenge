# Instruções para trabalhar neste repositório

## Documentar toda decisão e mudança

Toda mudança de código, experimento (incluindo os que **não** funcionaram), e decisão de projeto deve ser registrada em `docs/08-status-implementacao.md` (ou um novo doc em `docs/` se o assunto for grande o suficiente para merecer o próprio arquivo — indexar em `docs/README.md`) **antes ou junto do commit que a implementa**. Isso vale mesmo quando a mudança é revertida — experimentos negativos são tão valiosos quanto positivos (ver as três tentativas de política revertidas em `docs/08`, todas documentadas com o motivo).

Cada entrada deve deixar claro:
- **O que** foi tentado/mudado e **por quê** (o raciocínio, não só o resultado).
- **Como foi validado** (comando, número de partidas, decks/oponentes usados).
- **O resultado real**, incluindo quando contradiz a expectativa inicial.
- Se foi promovido, revertido, ou fica em aberto.

O objetivo é que `docs/` sozinho reconstrua a história de decisões do projeto — inclusive para o relatório da trilha Strategy do desafio (`docs/00-visao-geral.md`), que depende desse rastro.

## Contexto do projeto

Ver `docs/README.md` para o índice completo do plano e status. Resumo: agente para o Kaggle "PTCG AI Battle Challenge" (`docs/00-visao-geral.md`), engine oficial vendorizado em `vendor/cg/` (gitignorado, nunca commitar — licença restrita, ver `docs/06-riscos-questoes-abertas.md`), política em `agent/`, decks candidatos em `data/decks/`, avaliação local em `eval/local_match.py`.
