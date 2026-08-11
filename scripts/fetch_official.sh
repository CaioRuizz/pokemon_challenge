#!/usr/bin/env bash
# Baixa o material oficial da competição (engine + sample_submission) via Kaggle API
# e organiza em vendor/ (gitignorado — ver docs/06-riscos-questoes-abertas.md item 3).
#
# Requer: `pip install kaggle` e ~/.kaggle/kaggle.json (ou ~/.kaggle/access_token) configurado.
# Requer: ter aceitado as regras da competição em kaggle.com/competitions/pokemon-tcg-ai-battle.
set -euo pipefail

COMPETITION="pokemon-tcg-ai-battle"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENDOR_DIR="$ROOT_DIR/vendor"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

mkdir -p "$VENDOR_DIR/cg"

# Detecta qual binário nativo baixar conforme a plataforma atual.
case "$(uname -s)-$(uname -m)" in
  Linux-x86_64)  LIB_FILE="libcg.so" ;;
  Linux-aarch64|Linux-arm64) LIB_FILE="libcg-arm64.so" ;;
  Darwin-*) LIB_FILE="libcg.dylib" ;;
  *) echo "Plataforma não reconhecida: $(uname -s)-$(uname -m). Ajuste LIB_FILE manualmente." >&2; exit 1 ;;
esac

FILES=(
  "sample_submission/sample_submission/main.py"
  "sample_submission/sample_submission/deck.csv"
  "sample_submission/sample_submission/cg/__init__.py"
  "sample_submission/sample_submission/cg/api.py"
  "sample_submission/sample_submission/cg/game.py"
  "sample_submission/sample_submission/cg/sim.py"
  "sample_submission/sample_submission/cg/utils.py"
  "sample_submission/sample_submission/cg/${LIB_FILE}"
)

for f in "${FILES[@]}"; do
  echo "Baixando: $f"
  kaggle competitions download -c "$COMPETITION" -f "$f" -p "$TMP_DIR" --force -q
done

cp "$TMP_DIR"/__init__.py "$TMP_DIR"/api.py "$TMP_DIR"/game.py "$TMP_DIR"/sim.py "$TMP_DIR"/utils.py "$VENDOR_DIR/cg/"
cp "$TMP_DIR/$LIB_FILE" "$VENDOR_DIR/cg/"
cp "$TMP_DIR/deck.csv" "$VENDOR_DIR/deck_sample_placeholder.csv"

echo "OK — vendor/cg/ atualizado (lib: $LIB_FILE)."
echo "Lembrete: este material tem licença restrita à competição, nunca commitar (ver .gitignore)."
