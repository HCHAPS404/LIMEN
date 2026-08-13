#!/usr/bin/env bash
# prepare_demo_recording.sh — deja LIMEN listo para grabar el video de entrega.
# Uso (desde la raíz del repo):
#   chmod +x scripts/prepare_demo_recording.sh
#   ./scripts/prepare_demo_recording.sh
#
# Requisitos de host (ANTES de este script / fuera del reloj G2):
#   Python 3.11+, Node 20+, Make, Ollama corriendo, GPU NVIDIA recomendada.
# Windows: ejecuta dentro de WSL2 Ubuntu.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== LIMEN · preparación para grabación de demo ==="
echo "root: $ROOT"
echo ""

if [[ ! -f .env ]]; then
  echo "→ Creando .env desde .env.example"
  cp .env.example .env
else
  echo "→ .env ya existe"
fi

echo "→ make doctor"
make doctor || true

echo ""
echo "→ make bootstrap (puede tardar la primera vez)"
make bootstrap

echo ""
echo "→ prepare-voice + llm + knowledge seed"
make prepare-voice
make prepare-llm-bench PULL=1
make prepare-knowledge

if [[ -n "${LIMEN_DATASET_PATH:-}" ]] || [[ -d dataset ]] || [[ -d data/challenge ]]; then
  echo "→ corpus oficial detectado — prepare-official-knowledge (opcional, puede tardar)"
  make prepare-official-knowledge || echo "AVISO: ingest oficial falló; la demo G5 usa el .txt sintético igual."
else
  echo "→ sin LIMEN_DATASET_PATH — OK para demo (G5 usa docs/submission/demo_evidence/)"
fi

echo ""
echo "→ preflight challenge"
if ! make verify-challenge-environment; then
  echo ""
  echo "ERROR: READY_FOR_CHALLENGE_RUNTIME no es TRUE."
  echo "  - ¿Ollama está arriba?  ollama serve"
  echo "  - ¿phi3.5?             ollama pull phi3.5"
  echo "  - ¿prepare-voice OK?"
  exit 1
fi

EVIDENCE="$ROOT/docs/submission/demo_evidence/LIMEN_PROTOCOLO_DEMO_AZUL7491.txt"
if [[ ! -f "$EVIDENCE" ]]; then
  echo "ERROR: falta el archivo de evidencia: $EVIDENCE"
  exit 1
fi

echo ""
echo "=== LISTO PARA GRABAR ==="
echo ""
echo "1. En una terminal:"
echo "     make run-challenge"
echo ""
echo "2. Abre http://127.0.0.1:5173  → login demo@limen.local / limen-demo-2026"
echo ""
echo "3. Guion: docs/submission/DEMO_GUION_ES.md"
echo "   Evidencia G5 (subir en /knowledge):"
echo "     $EVIDENCE"
echo ""
echo "4. OBS: captura pantalla + mic + audio del sistema"
echo "   Instalar OBS (Arch):  sudo pacman -S obs-studio"
echo ""
echo "5. Humo rápido (con API+web ya arriba):"
echo "     make smoke-local"
echo ""
echo "¡Éxitos con la toma!"
