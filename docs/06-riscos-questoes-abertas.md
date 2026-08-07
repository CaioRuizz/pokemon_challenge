# 06 · Riscos e Questões Abertas

## 1. Sem acesso oficial aos dados/regras da competição (bloqueante)

As páginas do Kaggle (`/overview`, `/data`, `/rules`) são renderizadas via JavaScript (SPA) e exigem login + aceite das regras para baixar dataset/engine/starter notebook. Este ambiente não tem essas credenciais.

**O que isso significa na prática**: todo o conteúdo de `01-definicao-problema.md` (contrato do agente, formato de submissão, schema de observação/ação) é **inferido de repositórios de terceiros que já competem**, não da fonte oficial. Pode estar desatualizado, incompleto ou simplesmente errado em detalhes.

**Ação necessária (fora do escopo deste ambiente)**: alguém com acesso precisa:
- Entrar nas duas competições e aceitar as regras.
- Baixar o starter notebook oficial e o SDK/engine `cabt`.
- Colar/anexar o conteúdo relevante (ou rodar este repo em um ambiente com acesso ao Kaggle) para validarmos `01-definicao-problema.md`.

## 2. Datas de deadline não confirmadas na fonte primária

As datas em `00-visao-geral.md` e `04-roadmap.md` vêm de matérias de imprensa (PokeBeach, Dexerto, TalkEsport, etc.) que **divergem ligeiramente entre si** (ex.: 09/08 vs 16/08 para o fim da trilha Simulation em fontes diferentes). Antes de qualquer decisão crítica de cronograma, confirmar a aba "Timeline" oficial de cada competição no Kaggle.

## 3. Licenciamento de assets

Cartas, textos, arte e o próprio engine `cabt` são propriedade da The Pokémon Company. Precisamos confirmar os termos de uso antes de:
- Versionar (`git add`) qualquer asset baixado do Kaggle neste repositório.
- Publicar o repositório publicamente, se for o caso.

## 4. Ambiguidade nas fontes técnicas de terceiros

Repositórios de terceiros usados como referência (ver `07-referencias.md`) descrevem o sistema de rating de formas diferentes (um menciona "Elo", outro menciona "TrueSkill / μ, σ"). Isso não afeta a estratégia de alto nível, mas afeta como interpretamos "rating" nas nossas próprias avaliações — precisa ser confirmado.

## 5. Risco de cronograma

A trilha Simulation tem uma janela curta a partir de hoje (07/08) até o deadline reportado (~16/08). Se a Fase 0 (acesso oficial) atrasar, todo o roadmap desliza. Mitigação: priorizar a Fase 0 imediatamente e ter a Fase 1 (baseline trivial) pronta o quanto antes, mesmo antes de otimizar qualquer heurística.

## 6. Escopo de "vencer" não está definido por nós

Não sabemos ainda os critérios exatos de corte para a trilha Strategy (o que faz um relatório competitivo) além de "explicar a lógica do agente". Isso deve ser esclarecido lendo a rubrica oficial (se publicada) assim que houver acesso.
