# 05 · Plano de Avaliação

## Por que avaliação local importa aqui

- Cota reportada de submissões (5/dia, só as 2 últimas contam) torna o Kaggle um recurso caro para iterar.
- Relatos de equipes já competindo indicam que **simulação local nem sempre prevê o ranking real do ladder** — então avaliação local serve para **eliminar candidatos ruins rapidamente**, não para prever o rating final com precisão.

## Camadas de avaliação (do mais barato ao mais caro)

1. **Testes de legalidade/robustez** (`eval/` + `tests/`): rodar o agente contra estados de jogo variados garantindo que nunca retorna ação ilegal e nunca lança exceção. Isso é pré-requisito para qualquer submissão — falha aqui é bloqueante.
2. **Partidas locais 1x1** via SDK `cabt`: política A vs política B, N partidas, winrate + intervalo de confiança. Usado para comparar Fase 1 vs Fase 2 vs Fase 3 entre si.
3. **Matriz de matchup entre decks candidatos**: cada arquétipo candidato vs os demais (e, se disponível, vs decks públicos de referência de terceiros/exemplos oficiais), pilotados pela mesma política, para isolar "efeito deck" de "efeito política".
4. **Ladder real (Kaggle)**: fonte de verdade final. Só sobem para cá versões que já passaram nas camadas 1–3.

## Métricas

- **Winrate** (com intervalo de confiança — número de partidas locais precisa ser suficiente para não confundir ruído com sinal, já que o jogo tem componente de aleatoriedade forte).
- **Taxa de crash/erro** (deve ser 0% antes de qualquer submissão).
- **Tempo médio/máx por jogada** (para não estourar o limite de tempo por movimento).
- **Rating no ladder ao longo do tempo** (acompanhar histórico das submissões, não só o valor atual — ajuda a escrever o relatório da trilha Strategy depois).

## Processo de promoção de uma versão

```
passa testes de legalidade (100%)
    → vence a versão atual em partidas locais (winrate estatisticamente > 50%)
        → roda dentro do limite de tempo por jogada
            → candidata a consumir uma das submissões diárias
```

## Registro de experimentos

Cada rodada de avaliação relevante deve ser registrada (arquivo/planilha simples) com: data, versão do agente, deck usado, adversário/baseline, resultado, decisão tomada. Isso vira insumo direto do relatório da trilha Strategy (`02-estrategia-solucao.md`, Fase 5) — não é burocracia, é o material bruto do entregável final.
