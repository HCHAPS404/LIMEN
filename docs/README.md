# Documentación LIMEN

Índice canónico. Empieza por el nivel que necesites; no leas todo de golpe.

## Capas de lectura

| Capa | Para quién | Documentos |
| --- | --- | --- |
| **Presentación** | Juez, clonador nuevo, demo | [README raíz](../README.md) · [GETTING_STARTED](GETTING_STARTED.md) · [OPERATOR_WALKTHROUGH](OPERATOR_WALKTHROUGH.md) |
| **Competencia** | Entrega Tech Sphere | [submission/](submission/) · [CHALLENGE_RUNTIME](CHALLENGE_RUNTIME.md) · [SUBMISSION_CHECKLIST](submission/SUBMISSION_CHECKLIST.md) |
| **Arquitectura** | Ingeniería | [ARCHITECTURE.md](../ARCHITECTURE.md) · [BACKEND.md](../BACKEND.md) · [FRONTEND.md](../FRONTEND.md) · [ADRs](adr/) |
| **Voz / LLM / RAG** | Runtime real | [VOICE_RUNTIME](VOICE_RUNTIME.md) · [MODEL_SELECTION](MODEL_SELECTION.md) · artefactos `*.generated.md` |
| **Evidencia generada** | Métricas (no inventar) | Ver sección [Artefactos generados](#artefactos-generados) |

---

## Onboarding local

1. **[GETTING_STARTED.md](GETTING_STARTED.md)** — Clonar, bootstrap, stubs, troubleshooting.  
2. **[OPERATOR_WALKTHROUGH.md](OPERATOR_WALKTHROUGH.md)** — Recorrido de producto de 15 minutos.  
3. **[CHALLENGE_RUNTIME.md](CHALLENGE_RUNTIME.md)** — Perfil `challenge`, modelos reales, G2.  
4. **[VOICE_RUNTIME.md](VOICE_RUNTIME.md)** — STT/TTS, CUDA, preflight de voz.

---

## Paquete de submission

| Documento | Contenido |
| --- | --- |
| [submission/README.md](submission/README.md) | Entrada del paquete |
| [submission/SUBMISSION_CHECKLIST.md](submission/SUBMISSION_CHECKLIST.md) | Checklist de entrega + gates |
| [submission/FINAL_REPORT.md](submission/FINAL_REPORT.md) | Informe final (borrador) |
| [submission/DEMO_SCRIPT.md](submission/DEMO_SCRIPT.md) | Guion de demo / video |
| [submission/VIDEO_SHOT_LIST.md](submission/VIDEO_SHOT_LIST.md) | Lista de planos |
| [submission/SCREENSHOT_REGISTER.md](submission/SCREENSHOT_REGISTER.md) | Registro de capturas |
| [submission/ARCHITECTURE.md](submission/ARCHITECTURE.md) | Diagrama de arquitectura (Mermaid) |
| [submission/DECISION_FLOW.md](submission/DECISION_FLOW.md) | Flujo de decisión clínica |
| [submission/KNOWLEDGE_FLOW.md](submission/KNOWLEDGE_FLOW.md) | Flujo de conocimiento vivo |
| [submission/TRAZA.md](submission/TRAZA.md) | Explicación TRAZA |
| [submission/PROMPTS_APPENDIX.md](submission/PROMPTS_APPENDIX.md) | Apéndice de prompts |
| [submission/ATTRIBUTION.md](submission/ATTRIBUTION.md) | Atribución terceros |

Cola post-paquete: [FINAL_POLISH_REGISTER.md](FINAL_POLISH_REGISTER.md)

---

## Decisiones de arquitectura (ADRs)

| ADR | Tema |
| --- | --- |
| [ADR-0001](adr/ADR-0001-modular-monolith.md) | Monolito modular |
| [ADR-0002](adr/ADR-0002-sqlite-local-runtime.md) | SQLite local |
| [ADR-0003](adr/ADR-0003-provider-contracts.md) | Contratos de providers |
| [ADR-0004](adr/ADR-0004-client-auth.md) | Auth por cliente |
| [ADR-0005](adr/ADR-0005-persistence-vector-strategy.md) | Persistencia / vectores |

También: [architecture/dependency-flow.md](architecture/dependency-flow.md)

---

## Modelo, prompts, eval

| Documento | Contenido |
| --- | --- |
| [MODEL_SELECTION.md](MODEL_SELECTION.md) | Por qué Phi-3.5 + Governor |
| [PROMPT_CHANGELOG.md](PROMPT_CHANGELOG.md) | Historial de prompts |
| [EVAL_RESULTS.md](EVAL_RESULTS.md) | Resultados de evaluación (índice) |
| [PHASE7_GATE_MATRIX.md](PHASE7_GATE_MATRIX.md) | Matriz de gates PHASE 7 |

---

## Artefactos generados

Estos archivos **se generan con scripts**; no editar a mano para “mejorar” números.

| Artefacto | Origen típico |
| --- | --- |
| `G2_BOOTSTRAP.generated.md` | `make measure-g2-bootstrap` |
| `G4_VOICE_GATE.generated.md` | verificación de voz |
| `G5_LIVE_KNOWLEDGE.generated.md` | conocimiento en vivo |
| `CHALLENGE_GATE_EVAL.generated.md` | `make verify-challenge-eval` |
| `LLM_BENCHMARK*.generated.md` | benches LLM |
| `VOICE_BENCHMARK.generated.md` | bench de voz |
| `OFFICIAL_CORPUS.generated.md` | corpus oficial |
| `PHASE9_GATE_STATUS.generated.md` | estado PHASE 9 |

Marcadores pendientes: buscar `FINAL_EVIDENCE_REQUIRED` con
`make verify-submission-evidence`.

---

## Reglas de documentación (equipo)

- El README describe **lo que existe**. Lo futuro se etiqueta **Planned** / **In Progress**.  
- Las métricas se **generan**, no se adivinan.  
- Los diagramas de submission deben corresponder al código.  
- Secretos, `.env`, pesos, audio de paciente y DB runtime **nunca** van a git.

Ver también la carta de ingeniería: [`AGENTS.md`](../AGENTS.md).
