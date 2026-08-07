# 00 · Visão Geral do Desafio

## O que é

O **PTCG AI Battle Challenge** é uma competição do Kaggle promovida pela **The Pokémon Company**, em parceria com a Kaggle, para desenvolver **agentes de IA que joguem o Pokémon Trading Card Game (PTCG)** de forma autônoma — não construir o motor do jogo, e sim o "jogador".

O desafio é dividido em **duas competições conectadas** no Kaggle:

| Trilha | Slug Kaggle | O que avalia | Prêmio |
|---|---|---|---|
| **Simulation** | `pokemon-tcg-ai-battle` | Ladder/ranking automático (estilo Elo/TrueSkill) entre agentes submetidos, jogando partidas entre si | Parte do pool geral |
| **Strategy** | `pokemon-tcg-ai-battle-challenge-strategy` | Relatório escrito explicando a lógica/estratégia por trás do agente submetido na trilha Simulation | **US$ 240.000** (top 8 recebem US$ 30.000 cada e avançam para uma segunda fase) |

Links oficiais:
- Simulation: https://www.kaggle.com/competitions/pokemon-tcg-ai-battle
- Strategy: https://www.kaggle.com/competitions/pokemon-tcg-ai-battle-challenge-strategy

## Prazos conhecidos (a confirmar na página oficial)

> ⚠️ O conteúdo das páginas do Kaggle é renderizado via SPA (JavaScript) e não foi possível extraí-lo integralmente sem estar autenticado. As datas abaixo vêm de cobertura de imprensa e devem ser **reconfirmadas manualmente** na aba "Timeline"/"Rules" de cada competição (ver `06-riscos-questoes-abertas.md`).

- **Simulation**: submissões finais até **16/08/2026** (23:59 UTC); partidas do ladder continuam até ~31/08 ou convergência do leaderboard.
- **Strategy**: aceite das regras / entrada até **06/09/2026**; deadline de merge de equipe **06/09/2026**; submissão final do relatório até **13/09/2026**; encerramento da competição **14/09/2026**.

**Hoje é 07/08/2026 → restam ~9 dias para a trilha Simulation e ~1 mês para a trilha Strategy.** Isso é crítico para o roadmap (ver `04-roadmap.md`): o agente competitivo precisa estar pronto **antes** do relatório de estratégia, porque o relatório depende do agente já estar rodando no ladder.

## Escopo do jogo

- Formato **Standard** do PTCG, pool de ~2.000 cartas.
- Jogo de **informação imperfeita**: mão oculta do oponente, compra aleatória, estado de tabuleiro evoluindo — exige decisão sob incerteza.
- Times constroem **deck (60 cartas)** + **política/agente** que decide jogadas turno a turno.

## Nosso objetivo neste repositório

1. Construir um agente competitivo para a trilha **Simulation** (maximizar rating no ladder).
2. Produzir o **relatório de estratégia** exigido pela trilha **Strategy**, documentando a abordagem, decisões de deck e resultados.

Ver `01-definicao-problema.md` para o contrato técnico (observação/ação/submissão) e `02-estrategia-solucao.md` para o plano de ataque.
