# 01 · Definição do Problema (Contrato Técnico)

> ⚠️ **Status: não confirmado oficialmente.** Não consegui baixar o starter kit/notebook oficial nem os dados da competição (exigem login + aceite das regras no Kaggle, aos quais este ambiente não tem acesso). As informações abaixo foram reconstruídas a partir de repositórios públicos de terceiros que já competem no desafio (ver `07-referencias.md`) e **precisam ser validadas** contra o material oficial assim que tivermos acesso (ver `06-riscos-questoes-abertas.md`, item #1).

## Formato de submissão (inferido)

Cada submissão parece ser um `submission.tar.gz` contendo:

```
submission.tar.gz
├── main.py     # ponto de entrada: define a função agent()
├── deck.csv    # exatamente 60 IDs de carta (deck Standard)
└── cg/         # cópia da lib/engine oficial fornecida pela competição (dependência runtime)
```

Regras operacionais reportadas:
- Até **5 submissões/dia**; as **2 últimas** são as pontuadas no ladder.
- Cada jogada tem um **limite de tempo** (agente precisa responder rápido — nada de busca sem poda em produção).
- O agente **nunca pode "crashar"** — precisa sempre ter um fallback de jogada legal, senão perde a partida (ou é desclassificado da rodada).

## Contrato do agente (inferido)

```python
def agent(obs_dict: dict) -> list[int]:
    """
    Recebe o estado observável do jogo (mão, board, prize cards, etc,
    da perspectiva do próprio agente — informação imperfeita: não vê
    a mão do oponente).

    Retorna:
      - durante o jogo: índices das opções de jogada legais disponíveis
      - na fase de montagem de deck: 60 IDs de carta escolhidos
    """
```

Pontos a esclarecer com a spec oficial:
- Formato exato do `obs_dict` (quais chaves, histórico disponível, informação sobre prize cards do oponente etc.).
- Espaço de ações completo (attach energy, retreat, attack, use ability, play trainer, end turn — como cada um é codificado).
- Como funciona a fase de setup (mulligan, escolha de active/bench iniciais).
- Regras de empate / timeout / desconexão.

## Motor de jogo

- Chamado de **`cabt` engine** ("Combat"? "Card Auto Battle Tool"?) — simulador oficial do PTCG construído sobre `kaggle_environments`.
- É fornecido como SDK para rodar **localmente** (treino, debug, RL) com a mesma lógica do ambiente da competição — permite testar sem gastar submissões.

## Deck

- 60 cartas, formato **Standard**, universo de ~2.000 cartas possíveis.
- Implica que **parte da estratégia é metagame** (qual arquétipo de deck jogar), não só a qualidade do agente/política.

## O que precisamos validar assim que tivermos acesso oficial

1. Baixar e ler o **starter notebook** oficial (mencionado pela imprensa como cobrindo: construção de deck, avaliação de matchups, submissão).
2. Baixar o **engine/SDK `cabt`** e seus exemplos.
3. Confirmar schema exato de observação/ação lendo o código do engine (fonte de verdade > qualquer resumo de terceiros).
4. Confirmar formato de scoring do ladder (Elo puro? TrueSkill/μ,σ? Como fontes distintas mencionam ambos).
