# 07 · Referências

## Fontes oficiais

- Kaggle — PTCG AI Battle Challenge Simulation: https://www.kaggle.com/competitions/pokemon-tcg-ai-battle
- Kaggle — PTCG AI Battle Challenge Strategy: https://www.kaggle.com/competitions/pokemon-tcg-ai-battle-challenge-strategy
- Datasets de episódios (histórico de partidas do ladder), ex.: `kaggle/pokemon-tcg-ai-battle-episodes-index` e variantes datadas.

## Cobertura de imprensa (contexto, prêmios, datas — cruzar/confirmar com o oficial)

- PokéBeach — anúncio da competição, prêmio $300k+: https://www.pokebeach.com/2026/06/the-pokemon-company-launches-ai-competition-to-build-the-strongest-pokemon-tcg-player-featuring-300000-in-prizes
- EdTech Innovation Hub — cobertura geral: https://www.edtechinnovationhub.com/news/the-pokmon-company-seeks-ai-agents-for-tcg-competition-on-kaggle
- Dexerto — cobertura geral, menção a prize pool: https://www.dexerto.com/pokemon/pokemon-tcg-launches-ai-battle-challenge-with-50000-prize-pool-3376414/
- TalkEsport — cobertura geral, $300k: https://www.talkesport.com/pokemon/pokemon-tcg-ai-battle-challenge/
- Deltia's Gaming — cobertura, $240k: https://deltiasgaming.com/the-pokemon-company-issues-tcg-ai-challenge-with-240k-prize-pool-learn-more/
- PocketMonsters.net — cobertura geral: https://www.pocketmonsters.net/news/9296
- Kaggle (X/Twitter) — anúncio oficial: https://x.com/kaggle/status/2067233627583234073

## Repositórios de terceiros já competindo (referência técnica não oficial — validar contra a fonte primária)

- `wmh/ptcg-abc` — três agentes completos, análise de meta, ferramentas de avaliação local: https://github.com/wmh/ptcg-abc
- `TomBombadyl/kaggle_pokemon` — workspace para a trilha Strategy, engine POMDP/MCTS/RL: https://github.com/TomBombadyl/kaggle_pokemon
- Kaggle Notebooks públicos de exemplo (agente PPO, notebook de pesquisa, agente heurístico + pipeline de dados) — usados apenas como sinal de que existe SDK oficial para RL/simulação local.

## Observação sobre confiabilidade

Nenhuma das fontes de imprensa/terceiros acima substitui a leitura da spec oficial do Kaggle. Elas foram usadas apenas porque o conteúdo oficial (SPA + login) não estava acessível neste ambiente no momento em que este plano foi escrito (07/08/2026). Ver `06-riscos-questoes-abertas.md`.
