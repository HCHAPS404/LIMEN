# ◈ LIMEN

**Seguimiento postoperatorio por voz en el navegador** — Tech Sphere Challenge 2026.

LIMEN conversa en español con el paciente, mantiene un **estado clínico explícito**,
consulta **conocimiento vivo con procedencia**, y escala con un **Safety Governor
determinista**. El LLM (Phi-3.5) **no puede bajar** una decisión de seguridad más fuerte.

> **No es un dispositivo médico.** No sustituye a un clínico.

**Repositorio:** https://github.com/HCHAPS404/LIMEN · **Licencia:** [MIT](LICENSE)

---

## Empieza aquí (elige tu camino)

| Nivel | Tiempo orientativo | Qué obtienes | Ir a |
| --- | --- | --- | --- |
| **0 · Solo leer** | 5 min | Qué es LIMEN y cómo está armado | [Qué es](#qué-es) · [Arquitectura](#arquitectura-en-30-segundos) |
| **1 · Demo local (stubs)** | ~10–15 min | UI + API sin GPU ni Ollama | [Nivel 1](#nivel-1--demo-local-con-stubs) |
| **2 · Recorrido de producto** | ~15 min | Login → conocimiento → llamada → TRAZA | [docs/OPERATOR_WALKTHROUGH.md](docs/OPERATOR_WALKTHROUGH.md) |
| **3 · Runtime de competencia** | 30–90+ min* | STT/TTS/LLM/RAG reales | [Nivel 3](#nivel-3--runtime-de-competencia) |
| **4 · Evaluaciones** | variable | Tests y artefactos generados | [Nivel 4](#nivel-4--calidad-y-evaluaciones) |
| **Docs completas** | — | Índice de toda la documentación | [docs/README.md](docs/README.md) |

\*Primera vez con descargas de modelos; luego más rápido. Medición G2 (worktree limpio, caches calientes): **293.85 s** — [`docs/G2_BOOTSTRAP.generated.md`](docs/G2_BOOTSTRAP.generated.md). Clon estricto en máquina fría: aún `FINAL_EVIDENCE_REQUIRED:G2_STRICT_CLONE`.

---

## Qué es

Después de una cirugía, el paciente necesita seguimiento. LIMEN ofrece una
llamada de voz en el navegador que:

1. Escucha y transcribe (STT).
2. Actualiza un **estado clínico tipado** (`KNOWN_*`, `UNKNOWN`, `CONFLICTING`).
3. Recupera evidencia del corpus del cliente (RAG híbrido + procedencia).
4. Evalúa riesgo con el **Safety Governor** (autoridad).
5. Responde en voz (TTS) sin inventar protocolos.
6. Deja **TRAZA** auditable (turnos, seguridad, evidencia, tiempos).

Principio no negociable: **`unknown != normal`**. Lo no dicho permanece `UNKNOWN`.

---

## Arquitectura en 30 segundos

Monolito modular: **React (Vite)** + **FastAPI** + paquetes de dominio en `limen/`.

```text
Navegador (micrófono, VAD, reproducción)
  → WebSocket de voz
  → Faster-Whisper STT          (stub en Nivel 1)
  → ClinicalState + Uncertainty
  → RAG híbrido (E5 + Qdrant + FTS5 + RRF)
  → Safety Governor (autoritativo)
  → Phi-3.5 / plantillas deterministas
  → Piper TTS → navegador       (stub en Nivel 1)
  → TRAZA + métricas en SQLite
```

Diagramas de entrega: [`docs/submission/ARCHITECTURE.md`](docs/submission/ARCHITECTURE.md) ·
[`DECISION_FLOW.md`](docs/submission/DECISION_FLOW.md) ·
[`KNOWLEDGE_FLOW.md`](docs/submission/KNOWLEDGE_FLOW.md) ·
[`TRAZA.md`](docs/submission/TRAZA.md)

Fuentes de verdad de ingeniería: [`ARCHITECTURE.md`](ARCHITECTURE.md) ·
[`BACKEND.md`](BACKEND.md) · [`FRONTEND.md`](FRONTEND.md)

**¿Hay que desplegar en Vercel + otro host?** No es requisito del diseño de
competencia. El camino canónico es **clonar y correr en local** (`make bootstrap`,
`make run` / `make run-challenge`). Un deploy cloud es opcional y no sustituye el
runtime local de voz/modelos.

---

## Requisitos previos

| | Nivel 1 (stubs) | Nivel 3 (challenge) |
| --- | --- | --- |
| OS | Linux / macOS / WSL2 | Mismo |
| Python | **3.11+** | 3.11+ |
| Node | **20+** | 20+ |
| Red | Para instalar deps | + descargas HF / Ollama |
| GPU NVIDIA | No | Recomendada (STT CUDA) |
| Ollama | No | Sí (`phi3.5`) |
| Docker | No | No |

---

## Nivel 1 — Demo local con stubs

Objetivo: que **cualquiera** clone el repo y vea la app en minutos, sin GPU.

### 1. Clonar e instalar

```bash
git clone https://github.com/HCHAPS404/LIMEN.git
cd LIMEN
cp .env.example .env
make bootstrap
```

`make bootstrap` crea `.venv`, instala dependencias Python/JS y deja la cuenta
demo lista (ver `.env.example`).

### 2. Arrancar API y web (dos terminales)

```bash
# Terminal A — API :8000
make run

# Terminal B — UI :5173
make dev-web
```

Abre **http://127.0.0.1:5173/**

### 3. Entrar

| Campo | Valor (demo local) |
| --- | --- |
| Email | `demo@limen.local` |
| Password | `limen-demo-2026` |

Esos valores son **solo demo local**, no credenciales de producción.

### 4. Qué probar en stubs

- Landing + login / registro  
- `/knowledge` — consola de documentos (ciclo de vida según providers stub)  
- `/call` — UI de sesión (STT/TTS stub: no esperes latencia real de voz)  
- `/sessions` y `/trace/:callId` — auditoría  

Guía paso a paso ampliada: [`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md) ·
recorrido de producto: [`docs/OPERATOR_WALKTHROUGH.md`](docs/OPERATOR_WALKTHROUGH.md)

### Si algo falla (Nivel 1)

| Síntoma | Qué mirar |
| --- | --- |
| UI carga pero login falla / “no conecta” | ¿`make run` está activo? `curl http://127.0.0.1:8000/health` |
| Proxy Vite `ECONNREFUSED :8000` | Arranca la API **antes** o reinicia `make dev-web` cuando la API ya escuche |
| `make bootstrap` falla | Python 3.11+, Node 20+, red; borra `.venv` y reintenta |
| Puerto ocupado | Cambia `APP_PORT` o libera 8000/5173 |

---

## Nivel 2 — Recorrido de producto (demo humana)

Sigue el guion operativo (español, ~15 min):

→ **[`docs/OPERATOR_WALKTHROUGH.md`](docs/OPERATOR_WALKTHROUGH.md)**

Guion de video de competencia:

→ [`docs/submission/DEMO_SCRIPT.md`](docs/submission/DEMO_SCRIPT.md) ·
[`VIDEO_SHOT_LIST.md`](docs/submission/VIDEO_SHOT_LIST.md)

Estado de capturas/video: aún hay marcadores `FINAL_EVIDENCE_REQUIRED:DEMO_VIDEO`
(ver [`SCREENSHOT_REGISTER.md`](docs/submission/SCREENSHOT_REGISTER.md)).

---

## Nivel 3 — Runtime de competencia

Stack real: Faster-Whisper + Piper + Ollama Phi-3.5 + embeddings E5 + Qdrant local.

Detalle completo: [`docs/CHALLENGE_RUNTIME.md`](docs/CHALLENGE_RUNTIME.md) ·
[`docs/VOICE_RUNTIME.md`](docs/VOICE_RUNTIME.md)

```bash
cp .env.example .env
# Opcional corpus oficial:
# export LIMEN_DATASET_PATH=/ruta/absoluta/al/dataset

make bootstrap
make prepare-voice                 # Whisper + Piper
make prepare-llm-bench PULL=1      # ollama pull phi3.5
make prepare-knowledge             # semilla determinista
# make prepare-official-knowledge  # PDFs oficiales (si tienes dataset)
make verify-challenge-environment  # debe imprimir READY_FOR_CHALLENGE_RUNTIME=TRUE
make run-challenge                 # API + web con perfil challenge
```

Preflight de voz: `make verify-voice-environment` · API con libs CUDA: ver
`make dev-api-voice` / `scripts/run_voice_api.py`.

---

## Nivel 4 — Calidad y evaluaciones

```bash
make verify                     # lint + types + tests (embeddings stub en CI)
make verify-phase7              # E2E golden (ruta stub)
make verify-challenge-eval      # escenarios de challenge + artefactos
make verify-submission-evidence # busca FINAL_EVIDENCE_REQUIRED pendientes
make verify-rag-stub            # RAG determinista
```

Artefactos generados viven en `docs/*.generated.md` y `runtime/evals/`.
**Las métricas del README solo se actualizan desde esos scripts** — no se inventan.

---

## Cobertura de requisitos del challenge

| Requisito | LIMEN |
| --- | --- |
| Conversación de voz adaptativa | `/call` + WebSocket + ConversationContext |
| RAG | HybridEvidenceRetriever (E5 + FTS5 + RRF) |
| Upload en vivo | `/knowledge` + API de ciclo de vida |
| Borrado / olvido | Purga léxica + vectorial |
| Trazabilidad | UI TRAZA + `GET /api/traces/{id}` |
| Escalada | SafetyGovernor RED + artefacto |
| Resumen estructurado | Al finalizar la llamada |
| Español | UI + prompts paciente |
| Voz browser / API | Faster-Whisper + Piper (stubs en Nivel 1) |
| Repo público + MIT | Este repo |
| Setup reproducible | `Makefile` + `.env.example` |

---

## Seguridad (principio clave)

**El LLM no puede degradar la seguridad determinista.**  
`SafetyGovernor.enforce_floor` posee GREEN / YELLOW / RED y la escalada.

Benchmark **solo-modelo** (no es recall del sistema completo LIMEN):

| Modelo | Macro F1 | RED recall | RED FN |
| --- | ---: | ---: | ---: |
| llama3.2:1b | 0.303 | 0.000 | 24/24 |
| llama3.2:3b | 0.197 | 0.000 | 24/24 |
| **phi3.5** | **0.445** | **0.375** | **15/24** |

Fuente: [`docs/MODEL_SELECTION.md`](docs/MODEL_SELECTION.md).

---

## Métricas (honestas)

| Métrica | Estado |
| --- | --- |
| Voz P50 / P95 (speech-end → primer audio en browser) | **UNMEASURED** — `FINAL_EVIDENCE_REQUIRED:G4_P50` / `G4_P95` |
| Tokens in/out | Por turno si el provider reporta; a menudo null |
| Llamadas LLM / consultas RAG | Instrumentadas por turno |
| Coste / llamada | `FINAL_EVIDENCE_REQUIRED:COST_CALL` |

Proxies “TTS-ready” en servidor **no** son la latencia oficial del challenge.

---

## Estructura del repositorio

```text
apps/api/          FastAPI (HTTP + WebSocket)
apps/web/          React + Vite (Clinical Editorial Glass)
limen/             Dominios: clinical, safety, knowledge, conversation, voice, tracing…
evals/             Evaluaciones challenge / RAG / LLM / voz
tests/             unit · integration · safety
docs/              Onboarding, ADRs, métricas generadas, paquete submission/
scripts/           bootstrap, prepare-*, verify-*, measure-*
runtime/           DB, vectores, audio, logs (gitignored)
ARCHITECTURE.md    SoT arquitectura
BACKEND.md         SoT backend
FRONTEND.md        SoT frontend
```

Índice documental: **[`docs/README.md`](docs/README.md)**

---

## Conocimiento

| Acción | Cómo |
| --- | --- |
| Semilla determinista | `make prepare-knowledge` |
| PDFs oficiales | `LIMEN_DATASET_PATH=… make prepare-official-knowledge` |
| UI en vivo | `/knowledge` (upload / list / delete / forget) |

Descubiertos **107** PDFs en corpus oficial; smoke indexado **8** (no 107/107) —
`FINAL_EVIDENCE_REQUIRED:OFFICIAL_CORPUS_FULL`.  
Evidencia G5 UI: [`docs/G5_LIVE_KNOWLEDGE.generated.md`](docs/G5_LIVE_KNOWLEDGE.generated.md).

---

## Entrega / submission

Paquete de competencia: [`docs/submission/`](docs/submission/)  
Checklist: [`docs/submission/SUBMISSION_CHECKLIST.md`](docs/submission/SUBMISSION_CHECKLIST.md)  
Informe: [`docs/submission/FINAL_REPORT.md`](docs/submission/FINAL_REPORT.md)  
Cola de polish: [`docs/FINAL_POLISH_REGISTER.md`](docs/FINAL_POLISH_REGISTER.md)

```bash
make verify-submission-evidence
python scripts/phase9_secret_scan.py
```

---

## Limitaciones

- No es dispositivo médico; sin validación clínica formal de hackathon.
- Límites de modelos locales (idioma / alucinación contenida por safety + RAG).
- P50/P95 de voz en browser aún sin medir.
- Ingestión completa 107/107 del corpus oficial no verificada.
- Calidad del conocimiento depende del corpus del cliente.

---

## Licencia y atribución

MIT — [`LICENSE`](LICENSE).  
Modelos y herramientas de terceros: [`docs/submission/ATTRIBUTION.md`](docs/submission/ATTRIBUTION.md).

---

## Ayuda rápida de Make

```bash
make help
```

Targets más usados: `bootstrap`, `run`, `dev-web`, `run-challenge`,
`verify-challenge-environment`, `verify`, `prepare-knowledge`, `prepare-voice`.
