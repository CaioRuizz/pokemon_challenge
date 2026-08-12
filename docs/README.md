# Documentação do Plano — Pokemon TCG AI Battle Challenge

Este diretório contém **apenas planejamento** (nenhum código ainda). O objetivo é mapear o desafio, o contrato técnico conhecido/inferido, a estratégia de solução e o cronograma antes de começar a implementação.

## Índice

1. [Visão Geral](./00-visao-geral.md) — o que é o desafio, trilhas, prêmios, prazos.
2. [Definição do Problema](./01-definicao-problema.md) — contrato técnico do agente (⚠️ não confirmado oficialmente).
3. [Estratégia de Solução](./02-estrategia-solucao.md) — plano faseado (baseline → heurística → busca → RL opcional → relatório).
4. [Arquitetura Proposta](./03-arquitetura.md) — estrutura de repositório planejada para a fase de código.
5. [Roadmap](./04-roadmap.md) — cronograma cruzado com os deadlines das duas trilhas.
6. [Plano de Avaliação](./05-plano-avaliacao.md) — como testar localmente antes de gastar submissões no Kaggle.
7. [Riscos e Questões Abertas](./06-riscos-questoes-abertas.md) — **bloqueadores atuais**, começando pela falta de acesso oficial aos dados.
8. [Referências](./07-referencias.md) — fontes usadas para montar este plano.
9. [Status da Implementação](./08-status-implementacao.md) — o que já foi construído e testado (Fase 1).
10. [Meta Real do Ladder](./09-meta-real-do-ladder.md) — dados de outros agentes (episódios do ladder, tier list da comunidade) e o que fazer com eles.
11. [Fine-tuning Avançado](./10-fine-tuning-avancado.md) — critérios de "resultado satisfatório" e a rodada de otimização que os definiu.
12. [Loop Contínuo](./11-loop-continuo.md) — log das iterações do loop autônomo em andamento (a partir de 12/08), até o fechamento da trilha Simulation.

## Leia primeiro

Se for revisar só um documento, leia o **06 (Riscos e Questões Abertas)** — ele explica por que boa parte do contrato técnico ainda precisa ser validada contra a fonte oficial do Kaggle antes de começar a codar de verdade.
