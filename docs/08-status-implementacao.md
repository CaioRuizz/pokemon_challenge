# 08 · Status da Implementação (Fases 1 e 2)

Atualizado em 07/08/2026. Este documento resume o que já foi **construído e testado**, complementando o plano (docs 00–07).

## O que existe hoje

| Componente | Arquivo | Status |
|---|---|---|
| Vendorização do engine oficial | `vendor/cg/` (gitignorado) + `scripts/fetch_official.sh` | ✅ Funciona, testado |
| Agente baseline (nunca crasha) | `agent/main.py`, `agent/fallback.py`, `agent/policy_baseline.py` | ✅ Validado em ~50 partidas locais, 0 erros/seleções ilegais |
| Política heurística (Fase 2) | `agent/policy_heuristic.py`, `agent/card_data.py` | ✅ Pontua ataques por dano efetivo (fraqueza/resistência) e prioriza nocaute garantido; recua quando o ativo está com HP crítico |
| Cadeia de fallback em camadas | `agent/main.py` | ✅ `policy_heuristic` → `policy_baseline` → `fallback.safe_selection`, cada camada cobrindo exceção da anterior |
| Deck real (60 cartas) | `agent/deck.csv` (= `data/decks/fighting_rush_v1.csv`) | ✅ Mono-Fighting, 4 atacantes básicos sem evolução + Switch/Ultra Ball + energia |
| Harness de avaliação local | `eval/local_match.py` | ✅ CLI reutilizável, roda políticas/decks diferentes um contra o outro via `cg/game.py` |
| Empacotamento da submissão | `build/package_submission.sh` → `build/submission.tar.gz` (gitignorado) | ✅ Testado isolado (extraído + `main.agent()` chamado fora do repo) |

## O que o baseline faz (e não faz)

- **Política**: para a decisão principal do turno (`SelectType.MAIN`), prioriza `ATTACK > EVOLVE > ABILITY > PLAY > ATTACH > RETREAT > END`. Para qualquer outra decisão (escolher alvo, energia, sim/não, etc.), pega as primeiras opções legais disponíveis — sem heurística de conteúdo.
- **Não lê o texto/efeito das cartas.** Não sabe que um ataque como "Rising Chop" só funde dano contra Pokémon `ex`, nem pondera trocas táticas. Isso é esperado — é o objetivo da Fase 2 (`docs/02-estrategia-solucao.md`).
- **Nunca falha**: todo caminho passa por `agent/fallback.py`, que garante índice válido (`minCount`≤len≤`maxCount`, sem duplicata, dentro do range de opções) mesmo se a lógica "inteligente" (`policy_baseline.choose`) lançar exceção — coberto por `try/except` em `agent/main.py`.

## Deck escolhido: por quê

Sem acesso ao `/rules` (banlist e regras específicas do Standard vigente ainda não lidas — ver `06-riscos-questoes-abertas.md` item 6), optei por **não copiar um decklist de meta humano real** (ex.: Gardevoir ex, Gholdengo ex — vistos em pesquisa geral de Standard) porque:
1. Não há garantia de que essas cartas/arquétipos existem neste pool específico de ~1.267 cartas do engine (o pool tem nomes e cartas que não batem 1:1 com o meta "real" que eu conheço — ex.: `Professor's Research`, `Nest Ball` e `Iono` não foram encontrados na base).
2. Decks de combo real dependem de sequenciamento cuidadoso (evoluções, abilities encadeadas) que o baseline não sabe fazer.

Em vez disso, montei um deck **mono-Fighting, só Pokémon básicos (sem evolução)**, com ataques **sem condição de texto** (evitando atacar "para não fazer nada" por não cumprir um requisito que o bot não entende), usando dados reais de `all_card_data()`/`all_attack()`:
- Okidogi, Sandy Shocks, Lunatone, Hitmontop (4 cópias cada = 16 Pokémon)
- Switch, Ultra Ball (4 cópias cada = 8 treinadores utilitários simples)
- Basic {F} Energy (36 cópias)

Isso é deliberadamente conservador — o objetivo é ter algo **legal e jogável agora**, não o deck ótimo (isso é Fase 2).

## Resultado honesto: heurística vs. baseline no deck atual

Testei `policy_heuristic` contra `policy_baseline` pilotando o **mesmo deck** dos dois lados (30 partidas): **47% a 47%** (2 empates) — sem vantagem estatística clara. Isso não é um bug; é uma consequência direta de como o deck atual foi montado:
- Cada Pokémon do deck só tem **1 ataque utilizável** por carta → não há "qual ataque escolher" para a heurística otimizar.
- Os dois lados são **do mesmo tipo (Fighting)** → a lógica de fraqueza/resistência da heurística nunca é acionada (fraqueza nunca bate contra o próprio tipo).

A vantagem da heurística deve aparecer em três cenários que este teste não cobre: (1) contra decks de **tipo diferente** (fraqueza/resistência entram em jogo), (2) contra Pokémon com **múltiplos ataques** (trade-off custo/dano), (3) quando o ativo entra em **risco de HP baixo** (lógica de retreat). Sanity check contra o placeholder degenerado confirma que não houve regressão (80% de vitórias, em linha com os 90% do baseline puro). A heurística já é a política ativa por padrão (com o baseline como rede de segurança na cadeia de fallback), então isso não bloqueia nada — só significa que, **para ganhar rating de verdade, o próximo ganho concreto está mais no deck (diversidade de tipo/ataques) do que na política** neste momento.

## Observação de teste: duração de partidas

Em partidas espelhadas (deck vs. ele mesmo), a duração variou de ~5 a ~95 turnos, com pelo menos um caso observado ultrapassando isso — variância normal de um jogo com aleatoriedade (coin flips, draws), não um bug (0 erros de política em todos os testes). Como ainda não confirmamos se há limite de tempo por partida/turno no ladder real (`06-riscos-questoes-abertas.md` item 5), isso fica como ponto de atenção, não bloqueador.

## Próximo passo real (fora do escopo até aqui)

`build/submission.tar.gz` está pronto e validado localmente, mas **ainda não foi submetido no Kaggle**. Submeter consome uma das 5 cotas diárias reportadas e expõe o resultado publicamente no ladder — ação que requer confirmação explícita antes de ser executada (ver seção de execução cautelosa nas diretrizes gerais).
