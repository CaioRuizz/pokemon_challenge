#!/usr/bin/env bash
# Entrypoint do container de otimização contínua.
#
# Espera:
#   - Credenciais do Kaggle montadas em /root/.kaggle/kaggle.json (ou
#     /root/.kaggle/access_token) — necessário pra buscar o engine
#     licenciado (nunca embutido na imagem).
#   - Volume persistente montado em /app/data/ml (checkpoint sobrevive a
#     restart do container).
#   - Opcional: GIT_REMOTE + GIT_TOKEN como env vars, se quiser que o
#     container sincronize o checkpoint de volta pro repositório
#     periodicamente (só o arquivo de pesos, nunca vendor/cg/).
set -euo pipefail

echo "[entrypoint] buscando engine licenciado via Kaggle API..."
bash scripts/fetch_official.sh

echo "[entrypoint] iniciando loop de otimização evolutiva contínua..."
mkdir -p data/ml

GENERATIONS_PER_ROUND="${GENERATIONS_PER_ROUND:-50}"
GAMES_PER_ARCHETYPE="${GAMES_PER_ARCHETYPE:-8}"
POP_SIZE="${POP_SIZE:-12}"
DECK_ROTATION="${DECK_ROTATION:-agent/deck.csv}"  # pode listar vários decks separados por espaço

round=0
while true; do
  round=$((round + 1))
  echo "[entrypoint] rodada $round — $(date -u)"

  for deck in $DECK_ROTATION; do
    python3 scripts/evolve_policy.py \
      --generations "$GENERATIONS_PER_ROUND" \
      --pop-size "$POP_SIZE" \
      --games-per-archetype "$GAMES_PER_ARCHETYPE" \
      --deck "$deck" \
      --checkpoint data/ml/evolved_weights.json \
      --init-weights data/ml/evolved_weights.json 2>/dev/null || \
    python3 scripts/evolve_policy.py \
      --generations "$GENERATIONS_PER_ROUND" \
      --pop-size "$POP_SIZE" \
      --games-per-archetype "$GAMES_PER_ARCHETYPE" \
      --deck "$deck" \
      --checkpoint data/ml/evolved_weights.json
  done

  if [[ -n "${GIT_REMOTE:-}" && -n "${GIT_TOKEN:-}" ]]; then
    echo "[entrypoint] sincronizando checkpoint com $GIT_REMOTE..."
    git config user.email "evolve-bot@local"
    git config user.name "evolve-bot"
    git add data/ml/evolved_weights.json
    git commit -m "evolve: checkpoint automático rodada $round ($(date -u +%Y-%m-%dT%H:%M:%SZ))" || true
    git push "https://x-access-token:${GIT_TOKEN}@${GIT_REMOTE#https://}" HEAD:"${GIT_BRANCH:-main}" || \
      echo "[entrypoint] aviso: push falhou, continuando mesmo assim"
  fi
done
