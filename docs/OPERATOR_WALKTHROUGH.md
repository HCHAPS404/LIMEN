# Recorrido de operador — demo de producto (~15 min)

Guion para que **cualquier persona** (compañero, juez, tú mismo mañana)
demuestre LIMEN en local tras el [Getting Started](GETTING_STARTED.md).

**Modo:** Nivel 1 (stubs) basta para UI y flujo.  
**Modo challenge:** misma ruta; la voz y el RAG se sienten “de verdad”.

Cuenta demo: `demo@limen.local` / `limen-demo-2026`

---

## Preparación (2 min)

1. API: `make run` → `curl http://127.0.0.1:8000/health`  
2. Web: `make dev-web` → http://127.0.0.1:5173/  
3. Navegador con permiso de micrófono (solo necesario si hay STT real)

---

## Paso A — Landing y acceso (1 min)

**Objetivo:** mostrar la capa de presentación.

1. Abre `/` — brand LIMEN, claim, CTAs.  
2. Tema claro/oscuro e idioma ES/EN (nav).  
3. Entra al workspace (login demo o registro).

**Qué decir:** “Entrada comercial quieta; el producto crítico está detrás de cuenta.”

---

## Paso B — Conocimiento vivo (3–4 min)

**Ruta:** `/knowledge`

1. Lista documentos (semilla si corriste `make prepare-knowledge`).  
2. **Upload** de un PDF clínico de prueba (protocolo / alta).  
3. Espera estado disponible.  
4. (Opcional) sonda de retrieval / verificación.  
5. **Delete** y explica olvido: ya no debe recuperar ese origen.

**Qué decir:** “Corpus por cliente; borrar no es solo quitar de la lista.”

**Evidencia challenge:** G5 — ver `docs/G5_LIVE_KNOWLEDGE.generated.md` cuando exista confirmación generada.

---

## Paso C — Llamada de voz (4–5 min)

**Ruta:** `/call`

1. Elige persona de voz si aplica (preferencias / account).  
2. **Iniciar llamada** — concede micrófono.  
3. Habla en español como paciente postoperatorio (síntoma leve o duda).  
4. Observa fases: escuchar → transcribir/razonar → hablar.  
5. En stubs: la UX se ve; no exijas latencia real.  
6. En challenge: barge-in / interrupción si el guion lo pide.  
7. Cuelga / finaliza.

**Qué decir:** “Estado clínico explícito; seguridad determinista; el modelo no baja un RED.”

---

## Paso D — Sesiones y resumen (1–2 min)

**Ruta:** `/sessions`

1. Localiza la llamada terminada.  
2. Abre resumen si está disponible.  
3. Enlace a TRAZA.

---

## Paso E — TRAZA (3–4 min)

**Ruta:** `/trace/:callId`

1. Línea de tiempo: micrófono, voz, STT, extracción, retrieval, seguridad, respuesta.  
2. Selecciona varios pasos: el **inspector** debe mostrar texto humano (ES/EN), no solo `voice.speech.ended`.  
3. En evaluación de seguridad: riesgo + reglas.  
4. En retrieval: evidencia citada si hubo chunks.  
5. Si un paso no tiene métricas de coste: debe decirlo con honestidad, no inventar números.

**Qué decir:** “Auditoría sin chain-of-thought; procedencia y piso de seguridad visibles.”

---

## Paso F — Settings / honestidad (1 min)

**Ruta:** `/settings`

1. Salud de API / modelo reportado.  
2. Telemetría: valores no medidos se etiquetan como no medidos.

---

## Cierre sugerido (30 s)

> “LIMEN es reproducible en local: stubs para entrar rápido, perfil challenge para
> voz y RAG reales. Safety Governor manda; Phi-3.5 habla debajo del piso.
> TRAZA cierra el bucle de confianza.”

---

## Checklist anti-vergüenza

- [ ] No inventar P50/P95 si salen `UNMEASURED`  
- [ ] No mostrar `.env` ni claves  
- [ ] No afirmar “dispositivo médico”  
- [ ] Si stub: decir “modo desarrollo / stub”  
- [ ] Si challenge: confirmar `READY_FOR_CHALLENGE_RUNTIME=TRUE` antes

---

## Enlace al guion de video oficial

Para grabación de entrega: [submission/DEMO_SCRIPT.md](submission/DEMO_SCRIPT.md) ·
[VIDEO_SHOT_LIST.md](submission/VIDEO_SHOT_LIST.md)
