# Getting started — LIMEN en tu máquina

Guía detallada para clonar el proyecto y dejarlo corriendo.  
Si solo quieres el resumen: vuelve al [README](../README.md).

---

## 1. Qué vas a montar

LIMEN es un **monolito modular**:

| Pieza | Puerto por defecto | Rol |
| --- | --- | --- |
| `apps/api` (FastAPI) | `8000` | HTTP API + WebSocket de voz |
| `apps/web` (Vite + React) | `5173` | UI Clinical Glass; proxy a la API |

En **Nivel stubs** (recomendado al clonar):

- `LLM_PROVIDER=stub`, `STT_PROVIDER=stub`, `TTS_PROVIDER=stub`, `EMBEDDING_PROVIDER=stub`
- No necesitas GPU ni Ollama
- Sirve para UI, auth, rutas, y humo de integración

En **Nivel challenge** (después):

- Providers reales (Whisper, Piper, Ollama Phi-3.5, E5, Qdrant)
- Ver [CHALLENGE_RUNTIME.md](CHALLENGE_RUNTIME.md)

---

## 2. Requisitos del sistema

### Sistemas operativos

| OS | Stubs (Nivel 1) | Challenge (Nivel 3) | Notas |
| --- | --- | --- | --- |
| Linux (Ubuntu 22.04+/Debian, Fedora, Arch, …) | Sí | Sí | Camino canónico |
| macOS 13+ (Apple Silicon o Intel) | Sí | Sí | Whisper/Piper en CPU es lo habitual |
| Windows 10/11 **con WSL2** (Ubuntu) | Sí | Sí | **Recomendado en Windows** — mismo `make` que Linux |
| Windows nativo (cmd / PowerShell puro) | Best-effort | No recomendado | Make + rutas `.venv\Scripts`; voz/CUDA frágiles |

Scripts de diagnóstico (`scripts/doctor.py`, `scripts/smoke_local.py`) usan solo stdlib y
rutas `pathlib` (Linux / macOS / Windows). El `Makefile` detecta `.venv/bin` vs
`.venv/Scripts`.

### Obligatorios (Nivel 1)

- **Git**
- **GNU Make** (`make --version`)
- **Python 3.11+** (`python3 --version` · en Windows/WSL igual)
- **Node.js 20+** y **npm** (`node --version`)
- Espacio en disco para `.venv` y `node_modules` (orden de ~1–3 GB en stubs; mucho más con modelos)

### Opcionales (Nivel 3)

- **Ollama** instalado y corriendo (`ollama serve`)
- **NVIDIA GPU + drivers** para Faster-Whisper en CUDA (Linux/WSL)
- Red estable para primera descarga de modelos (Hugging Face, Ollama)
- Dataset oficial Tech Sphere montado vía `LIMEN_DATASET_PATH` (opcional; G5 no lo requiere)

### No requerido

- Docker
- Cuenta cloud
- Deploy en Vercel (el camino canónico es local)

### Windows — WSL2 en corto

1. Instala WSL2 + Ubuntu desde Microsoft Store / `wsl --install`.
2. Dentro de Ubuntu: instala `build-essential` (trae `make`), Python 3.11+, Node 20+.
3. Clona el repo **dentro del filesystem de WSL** (`~/Projects/...`), no desde `/mnt/c/...` si puedes evitarlo (I/O lento).
4. Sigue el mismo flujo Linux: `cp .env.example .env` → `make doctor` → `make bootstrap`.

---

## 3. Clonar

```bash
git clone https://github.com/HCHAPS404/LIMEN.git
cd LIMEN
```

Comprueba que estás en la rama que quieras usar (p. ej. `main`).

---

## 4. Variables de entorno

```bash
cp .env.example .env
# Windows cmd (nativo): copy .env.example .env
```

El `.env.example` ya trae defaults de **desarrollo con stubs**.  
**No subas** tu `.env` a git (está en `.gitignore`).

Cuenta demo (creada/asegurada por bootstrap):

| | |
| --- | --- |
| Email | `demo@limen.local` |
| Password | `limen-demo-2026` |

Definidas como `LIMEN_DEMO_EMAIL` / `LIMEN_DEMO_PASSWORD` en `.env.example`.  
Son **credenciales de demo local**, no de producción.

CORS por defecto incluye `http://localhost:5173` y `http://127.0.0.1:5173`.

---

## 5. Doctor + Bootstrap

```bash
make doctor      # READY_STUBS=TRUE/FALSE — qué falta en el host
make bootstrap
make doctor      # re-check tras instalar
```

`make bootstrap` suele:

1. Crear `.venv` si no existe (Linux/macOS: `.venv/bin`; Windows: `.venv/Scripts`)  
2. Instalar dependencias Python del proyecto  
3. Instalar deps del frontend (`apps/web`)  
4. Preparar runtime paths / cuenta demo  

Si `INSTALL_EMBEDDINGS=0 make bootstrap`, puedes omitir torch/sentence-transformers en el bootstrap (útil en máquinas muy justas; el Nivel 3 de embeddings real pedirá instalarlas después).

### Verificar el entorno mínimo

```bash
make doctor
# Linux/macOS/WSL:
.venv/bin/python --version
# Windows nativo (si aplica):
# .venv\Scripts\python.exe --version
```

Tras arrancar API + web: `make smoke-local` (debe imprimir `SMOKE_LOCAL=PASS`).

---

## 6. Arrancar en dos terminales

### Terminal A — API

```bash
cd /ruta/a/LIMEN
make run
# Linux/macOS/WSL:
# .venv/bin/python -m uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000
```

Espera a ver algo como: `Uvicorn running on http://127.0.0.1:8000`

Comprueba:

```bash
make smoke-local --skip-web   # si aún no levantaste la UI; o:
curl -sS http://127.0.0.1:8000/health | python -m json.tool
```

```bash
make smoke-local
# solo API:
make smoke-local ARGS='--skip-web'
```

Debes ver `"status": "ok"` y, en stubs, providers stub listados.

### Terminal B — Web

```bash
cd /ruta/a/LIMEN
make dev-web
# equivalente: cd apps/web && npm run dev
```

Abre: **http://127.0.0.1:5173/**

Vite hace proxy de `/api` y `/health` hacia `:8000`. Si la API no está arriba, verás errores de proxy (`ECONNREFUSED`) en la consola de Vite — **no es un bug de React**: arranca la API.

Luego:

```bash
make smoke-local
```

---

## 7. Primer login

1. Abre la landing.  
2. Entra con `demo@limen.local` / `limen-demo-2026`, o crea una cuenta nueva.  
3. Deberías llegar al workspace (Call / Knowledge / TRAZA / Sessions / Settings).

Siguiente: [OPERATOR_WALKTHROUGH.md](OPERATOR_WALKTHROUGH.md).

---

## 8. Comandos útiles día a día

```bash
make help                 # lista de targets
make doctor               # qué falta en el host
make smoke-local          # API+web ya corriendo
make verify               # lint + types + tests (ruta stub)
make prepare-knowledge    # semilla de documentos (útil antes de probar RAG real)
make run-challenge        # solo cuando el preflight challenge esté READY
```

Estructura que **no** debes commitear:

- `.env`
- `.venv/`
- `apps/web/node_modules/`
- `runtime/` (DB, audio, vectores, logs)
- pesos de modelos

---

## 9. Troubleshooting

### Login / “no me deja conectarme”

1. `curl http://127.0.0.1:8000/health` — si falla, la API no está.  
2. Reinicia `make run` y luego `make dev-web`.  
3. Hard refresh del navegador.  
4. Revisa que `CORS_ORIGINS` incluya el origen con el que abres la UI (`127.0.0.1` vs `localhost`).

### Puerto 8000 o 5173 ocupado

```bash
# Linux ejemplo
ss -tlnp | grep -E '8000|5173'
```

Cambia `APP_PORT` en `.env` o mata el proceso viejo.

### Bootstrap / pip falla

- Confirma Python 3.11+.  
- Borra `.venv` y vuelve a `make bootstrap`.  
- En redes restringidas, configura índices pip/npm según tu entorno.

### Frontend typecheck / tests

```bash
cd apps/web
npx tsc --noEmit
npm test -- --run
npm run lint
```

### Quiero voz real

No uses solo Nivel 1. Sigue:

1. [CHALLENGE_RUNTIME.md](CHALLENGE_RUNTIME.md)  
2. [VOICE_RUNTIME.md](VOICE_RUNTIME.md)  
3. `make prepare-voice` · `make verify-voice-environment` · `make verify-challenge-environment`  
4. `make run-challenge`

---

## 10. Mapa de documentación

Índice completo: [docs/README.md](README.md)

| Quiero… | Documento |
| --- | --- |
| Entender el dominio | [ARCHITECTURE.md](../ARCHITECTURE.md) |
| Cambiar API / safety / RAG | [BACKEND.md](../BACKEND.md) |
| Cambiar UI | [FRONTEND.md](../FRONTEND.md) |
| Entregar el challenge | [submission/SUBMISSION_CHECKLIST.md](submission/SUBMISSION_CHECKLIST.md) |
| Ver por qué Phi-3.5 | [MODEL_SELECTION.md](MODEL_SELECTION.md) |

---

## 11. Criterio de “ya funciona” (Nivel 1)

Marca esto antes de pasar a challenge:

- [ ] `GET /health` → `ok`  
- [ ] UI en `:5173`  
- [ ] Login con cuenta demo  
- [ ] Navegación Call / Knowledge / Sessions / Trace / Settings sin crash  
- [ ] `make verify` verde (opcional pero recomendado en tu máquina)

Cuando eso esté, el proyecto **ya es clonable y usable** en modo presentación.  
El stack de competencia es el Nivel 3, no el mínimo para entender el producto.
