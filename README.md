# ◈ LIMEN

**Seguimiento postoperatorio por voz en el navegador** — Tech Sphere Challenge 2026.

LIMEN conversa en español con el paciente, mantiene un **estado clínico explícito**,
consulta **conocimiento vivo con procedencia**, y escala con un **Safety Governor
determinista**. El LLM (Phi-3.5) **no puede bajar** una decisión de seguridad más fuerte.

> **No es un dispositivo médico.** No sustituye a un clínico.

**Repositorio:** https://github.com/HCHAPS404/LIMEN · **Licencia:** [MIT](LICENSE)

## Entregables (Tech Sphere)

| Entregable | Enlace |
| --- | --- |
| Informe final | [`docs/submission/FINAL_REPORT.md`](docs/submission/FINAL_REPORT.md) |
| Diagrama de arquitectura | [`docs/submission/ARCHITECTURE.md`](docs/submission/ARCHITECTURE.md) |
| Flujo de decisión | [`docs/submission/DECISION_FLOW.md`](docs/submission/DECISION_FLOW.md) |
| **Video demo** (YouTube oculto) | **https://youtu.be/PEGAR_ID_AQUI** |

Cuando el corte final esté listo: sustituye `PEGAR_ID_AQUI` por el ID del video
(YouTube → Compartir → no listado). El mismo marcador está en el informe y en
`docs/submission/VIDEO_SHOT_LIST.md`.

**LLM y voz (runtime de competencia):** Ollama **Phi-3.5** · STT **Faster-Whisper small** ·
TTS **Piper** `es_MX-claude-high`. RAG: **multilingual-e5-small** + Qdrant + FTS5.

---

## Empieza aquí (elige tu camino)

| Nivel | Tiempo orientativo | Qué obtienes | Ir a |
| --- | --- | --- | --- |
| **0 · Solo leer** | 5 min | Qué es LIMEN y cómo está armado | [Qué es](#qué-es) · [Arquitectura](#arquitectura-en-30-segundos) |
| **1 · Demo local (stubs)** | ~10 min | UI + API sin GPU ni Ollama | [Nivel 1](#nivel-1--demo-local-con-stubs) |
| **2 · Recorrido de producto** | ~15 min | Login → conocimiento → llamada → TRAZA | [docs/OPERATOR_WALKTHROUGH.md](docs/OPERATOR_WALKTHROUGH.md) |
| **3 · Runtime de competencia (G2)** | **≤15 min** | STT/TTS/LLM/RAG reales | [G2 · cronómetro](#g2--levantamiento-15-minutos) |
| **4 · Evaluaciones** | variable | Tests y artefactos generados | [Nivel 4](#nivel-4--calidad-y-evaluaciones) |
| **Docs completas** | — | Índice de toda la documentación | [docs/README.md](docs/README.md) |

Medición G2 previa (camino largo, caches calientes): **293.85 s** —
[`docs/G2_BOOTSTRAP.generated.md`](docs/G2_BOOTSTRAP.generated.md). El camino
documentado ahora es `make lift` (sin `PULL=1`, sin verify duplicado, sin fixtures
de eval). Primera descarga de modelos = prerrequisito de host, no del cronómetro.

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

### Sistemas operativos soportados

| Plataforma | Nivel 1 (stubs) | Nivel 3 (challenge / voz real) |
| --- | --- | --- |
| **Linux** (Ubuntu/Debian, Fedora, Arch, …) | Soportado | Soportado (CUDA NVIDIA recomendada) |
| **macOS** (Apple Silicon / Intel) | Soportado | Soportado; STT suele ir por CPU |
| **Windows vía WSL2** (Ubuntu) | **Camino recomendado en Windows** | Igual que Linux en WSL |
| Windows nativo (cmd/PowerShell) | Best-effort (Git Bash + Make) | No recomendado para voz/CUDA |

Herramientas comunes: **Git**, **GNU Make**, **Python 3.11+**, **Node.js 20+**.  
En Windows usa **WSL2** para el mismo flujo `make …` que en Linux.

| | Nivel 1 (stubs) | Nivel 3 (challenge) |
| --- | --- | --- |
| Red | Para instalar deps | + descargas HF / Ollama |
| GPU NVIDIA | No | Recomendada (STT CUDA en Linux/WSL) |
| Ollama | No | Sí (`phi3.5`) |
| Docker | No | No |

**Diagnóstico:** `make doctor` → imprime `READY_STUBS=TRUE/FALSE`.  
**Humo con servidores arriba:** `make smoke-local`.

---

## Nivel 1 — Demo local con stubs

Objetivo: que **cualquiera** clone el repo y vea la app en minutos, sin GPU.

### 1. Clonar e instalar

```bash
git clone https://github.com/HCHAPS404/LIMEN.git
cd LIMEN
cp .env.example .env          # Windows cmd: copy .env.example .env
make doctor                   # opcional pero útil en máquina nueva
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

### 3. Verificar humo

```bash
make smoke-local
# SMOKE_LOCAL=PASS  → API :8000 y web :5173 responden
```

Abre **http://127.0.0.1:5173/**

### 4. Entrar

| Campo | Valor (demo local) |
| --- | --- |
| Email | `demo@limen.local` |
| Password | `limen-demo-2026` |

Esos valores son **solo demo local**, no credenciales de producción.

### 5. Qué probar en stubs

- Landing + login / registro  
- `/knowledge` — consola de documentos (ciclo de vida según providers stub)  
- `/call` — UI de sesión (STT/TTS stub: no esperes latencia real de voz)  
- `/sessions` y `/trace/:callId` — auditoría  

Guía paso a paso ampliada: [`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md) ·
recorrido de producto: [`docs/OPERATOR_WALKTHROUGH.md`](docs/OPERATOR_WALKTHROUGH.md)

### Si algo falla (Nivel 1)

| Síntoma | Qué mirar |
| --- | --- |
| No sabes qué falta | `make doctor` |
| UI carga pero login falla / “no conecta” | ¿`make run` activo? `make smoke-local` |
| Proxy Vite `ECONNREFUSED :8000` | Arranca la API **antes** o reinicia `make dev-web` |
| `make bootstrap` falla | Python 3.11+, Node 20+, Make, red; borra `.venv` y reintenta |
| Windows: `make` no existe | Usa **WSL2** o instala Make + Git Bash |
| Puerto ocupado | Cambia `APP_PORT` o libera 8000/5173 |

---

## Nivel 2 — Recorrido de producto (demo humana)

Sigue el guion operativo (español, ~15 min):

→ **[`docs/OPERATOR_WALKTHROUGH.md`](docs/OPERATOR_WALKTHROUGH.md)**

Guion de video de competencia:

→ [`docs/submission/DEMO_SCRIPT.md`](docs/submission/DEMO_SCRIPT.md) ·
[`VIDEO_SHOT_LIST.md`](docs/submission/VIDEO_SHOT_LIST.md)

Video (YouTube oculto, sustituir ID): **https://youtu.be/PEGAR_ID_AQUI**

---

## G2 — Levantamiento ≤15 minutos

Este es el **único procedimiento que el jurado debe cronometrar**.

Abre **http://127.0.0.1:5173/** · login `demo@limen.local` / `limen-demo-2026`.

### Antes del cronómetro (host)

Instala una vez, como el sistema operativo — **no cuenta** en los 15 minutos:

- Python **3.11+**, Node.js **20+**, Git, GNU Make
- **Ollama** instalado, `ollama serve` en marcha, y **`ollama pull phi3.5`** ya hecho
- Drivers NVIDIA si usarás STT en CUDA (Linux/WSL)
- Windows: **WSL2 + Ubuntu** ya listo
- Opcional: primera descarga Hugging Face de Whisper/Piper (`make prepare-voice`) para no pagar HF dentro del reloj

### Dentro del cronómetro

```bash
git clone https://github.com/HCHAPS404/LIMEN.git
cd LIMEN
cp .env.example .env
make lift
```

`make lift` = `bootstrap` + assets de voz (sin fixtures de eval) + chequeo de Phi
(sin `ollama pull`) + `run-challenge`. El preflight corre **una sola vez** al arrancar.

Listo cuando respondan:

- API: http://127.0.0.1:8000/health
- UI: http://127.0.0.1:5173/

Medición previa del camino más largo (incluye verify duplicado y fixtures): **293.85 s**
([`docs/G2_BOOTSTRAP.generated.md`](docs/G2_BOOTSTRAP.generated.md)) — ya **< 15 min**.
El camino `lift` recorta ese procedimiento; no se inventa un tiempo nuevo aquí.

Corpus oficial y `make prepare-knowledge` **no** forman parte de G2.

---

## Nivel 3 — Runtime de competencia (detalle)

Stack real: Faster-Whisper + Piper + Ollama Phi-3.5 + embeddings E5 + Qdrant local.

Detalle: [`docs/CHALLENGE_RUNTIME.md`](docs/CHALLENGE_RUNTIME.md) ·
[`docs/VOICE_RUNTIME.md`](docs/VOICE_RUNTIME.md)

Si `make lift` ya dejó el stack arriba, no hace falta repetir nada. Comandos sueltos:

```bash
make prepare-knowledge             # semilla RAG (después de G2 / para demo)
# make prepare-official-knowledge  # PDFs oficiales (LIMEN_DATASET_PATH)
make smoke-local                   # API+web ya corriendo
```

Preflight de voz: `make verify-voice-environment` · API con libs CUDA: `make dev-api-voice`.

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
| Tokens in/out | Por turno si Ollama/el provider los reporta; a menudo `null` |
| Llamadas LLM / consultas RAG | Instrumentadas por turno (TRAZA) |
| Coste API local | **$0** medido (Ollama + Whisper + Piper en máquina) |
| Coste equivalente API (extrapolación) | Ver [presupuesto de tokens](#presupuesto-de-tokens-y-contexto) — `FINAL_EVIDENCE_REQUIRED:COST_CALL` hasta fijar fuente de precio en el informe |

Proxies “TTS-ready” en servidor **no** son la latencia oficial del challenge.

---

## Presupuesto de tokens y contexto

LIMEN **no** manda el transcript entero al modelo. La continuidad es un
`ConversationContext` acotado (estado clínico + seguridad + últimos turnos),
no una ventana de chat ilimitada. Cada cuenta ve solo **sus** llamadas
(`account_id`); el historial vive en `runtime/` (gitignored) y un clon arranca vacío.

### Límites de runtime (código / `.env.example`)

| Recurso | Valor | Dónde |
| --- | --- | --- |
| Ventana reciente al LLM | **6** turnos (`CONVERSATION_RECENT_TURNS`) | Continuidad; cada turno se recorta a ~240 caracteres |
| Presupuesto de contexto conversacional | **1800** tokens (`CONVERSATION_CONTEXT_TOKEN_BUDGET`) | Configurado; el recorte efectivo hoy es por nº de turnos |
| Completions por turno (paciente) | **`max_tokens=320`** | `limen/conversation/response.py` |
| Default Ollama `num_predict` | **256** (`LLM_MAX_TOKENS`) | Settings; el turno de voz usa 320 |
| Evidencia RAG por turno | hasta **5** chunks (`FINAL_TOP_K`) | Híbrido E5 + FTS5 + RRF |
| Duración máxima de llamada | **15 min** | Cierre por `max_duration` |
| Idle | aviso ~**150 s**, cuelga ~**90 s** después | Ciclo de vida de la sesión |
| Contexto nativo Phi-3.5 (Ollama) | **131 072** tokens | Capacidad del modelo; LIMEN **no** la usa entera |

STT/TTS **no** consumen tokens de LLM. Safety Governor y plantillas degradadas
pueden responder **sin** invocación al modelo.

### Consumo teórico de LLM por llamada (Phi-3.5, challenge)

Estimación de **prompt + completion** a partir de los techos anteriores
(system prompt ~0.6–0.9 k tokens + estado + 6 turnos cortos + ≤5 chunks).
No es una medición de sesión; TRAZA registra el uso real cuando el provider lo envía.

| Escenario | Turnos LLM | Tokens entrada (aprox.) | Tokens salida (aprox.) | Total (aprox.) |
| --- | ---: | ---: | ---: | ---: |
| Mínimo (saludo + 1 pregunta; o turno en plantilla) | 0–1 | 0–1 200 | 0–120 | **0–1 300** |
| Típico demo (4–8 turnos con RAG) | 4–8 | 5 000–12 000 | 400–1 600 | **6 000–14 000** |
| Techo de sesión (15 min, ~12–18 turnos con evidencia) | 12–18 | 15 000–28 000 | 1 500–4 000 | **~18 000–32 000** |

Una llamada RED puede ser **más corta** (escala y cierra) y a la vez más
barata en tokens que un seguimiento largo GREEN/YELLOW.

### Coste equivalente si el mismo volumen corriera en API

Runtime de competencia: **local → coste de API = $0**.  
Para comparar con un despliegue cloud, extrapolación con precios públicos
**GPT-4o mini** (OpenAI, ago 2026, USD / 1M tokens: input **0.15**, output **0.60**).
Fuente a verificar en el informe; no es una factura de LIMEN.

| Escenario | Tokens (aprox.) | Equivalente API (USD / llamada) |
| --- | --- | ---: |
| Mínimo | ~1 000 in + 80 out | **~$0.0002** |
| Típico demo | ~8 000 in + 800 out | **~$0.0017** |
| Techo 15 min | ~24 000 in + 2 500 out | **~$0.005** |

A **1 000 llamadas/mes** en el escenario típico: **~$1.7** solo de LLM
(sin STT/TTS cloud). Hardware local (GPU/CPU) es el coste real del challenge.

Cuando Ollama reporta `prompt_tokens` / `completion_tokens`, TRAZA los guarda
por turno. Números de esta sección son **presupuesto de diseño**, no P50 medido.

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
