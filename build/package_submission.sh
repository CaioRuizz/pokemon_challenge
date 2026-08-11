#!/usr/bin/env bash
# Empacota agent/{main.py,fallback.py,policy_baseline.py,deck.csv} + vendor/cg/
# no formato submission.tar.gz esperado pela competição (main.py + deck.csv + cg/ na raiz).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGENT_DIR="$ROOT_DIR/agent"
VENDOR_CG="$ROOT_DIR/vendor/cg"
OUT_FILE="${1:-$ROOT_DIR/build/submission.tar.gz}"

for f in main.py fallback.py policy_baseline.py deck.csv; do
  if [[ ! -f "$AGENT_DIR/$f" ]]; then
    echo "ERRO: $AGENT_DIR/$f não existe." >&2
    exit 1
  fi
done
if [[ ! -d "$VENDOR_CG" ]]; then
  echo "ERRO: $VENDOR_CG não existe. Rode scripts/fetch_official.sh primeiro." >&2
  exit 1
fi

DECK_LINES="$(wc -l < "$AGENT_DIR/deck.csv" | tr -d ' ')"
if [[ "$DECK_LINES" -ne 60 ]]; then
  echo "ERRO: agent/deck.csv tem $DECK_LINES linhas, esperado 60." >&2
  exit 1
fi

STAGE_DIR="$(mktemp -d)"
trap 'rm -rf "$STAGE_DIR"' EXIT

cp "$AGENT_DIR/main.py" "$AGENT_DIR/fallback.py" "$AGENT_DIR/policy_baseline.py" "$AGENT_DIR/deck.csv" "$STAGE_DIR/"
cp -r "$VENDOR_CG" "$STAGE_DIR/cg"

find "$STAGE_DIR" -name "__pycache__" -type d -exec rm -rf {} +

mkdir -p "$(dirname "$OUT_FILE")"
tar -czf "$OUT_FILE" -C "$STAGE_DIR" .

echo "OK — submissão empacotada em: $OUT_FILE"
echo "Conteúdo:"
tar -tzf "$OUT_FILE"
