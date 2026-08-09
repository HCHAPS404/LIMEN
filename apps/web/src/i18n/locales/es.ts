/** Spanish is the product default: the patient-facing voice loop is Spanish.
 *  Clinical enum values that come from the backend (GREEN, UNKNOWN, …) are never
 *  translated here — only interface copy is. */
export const es = {
  common: {
    theme: {
      label: "Tema",
      dark: "Oscuro",
      light: "Claro",
      toDark: "Cambiar a tema oscuro",
      toLight: "Cambiar a tema claro",
    },
    language: {
      label: "Idioma",
      es: "Español",
      en: "English",
      switchTo: "Cambiar idioma a {{language}}",
    },
    actions: {
      retry: "Reintentar",
      cancel: "Cancelar",
      close: "Cerrar",
    },
  },

  shell: {
    workspace: "Espacio de trabajo",
    nav: {
      call: "Llamada",
      knowledge: "Conocimiento",
      trace: "Traza",
      sessions: "Sesiones",
      settings: "Ajustes",
    },
    rail: {
      collapse: "Contraer navegación",
      expand: "Expandir navegación",
    },
    routes: {
      call: {
        title: "Llamada de voz",
        subtitle: "Sesión de seguimiento postoperatorio",
      },
      knowledge: {
        title: "Base de conocimiento",
        subtitle: "Corpus clínico y ciclo de recuperación",
      },
      trace: {
        title: "TRAZA",
        subtitle: "Auditoría de decisión y evidencia",
      },
      sessions: {
        title: "Sesiones",
        subtitle: "Llamadas de seguimiento completadas",
      },
      settings: {
        title: "Ajustes",
        subtitle: "Preferencias de tu sesión en este navegador",
      },
      notFound: { title: "No encontrado" },
      fallback: { title: "Workspace" },
    },
    account: {
      menuLabel: "Cuenta",
      signedInAs: "Sesión iniciada como",
      preferences: "Preferencias",
      signOut: "Cerrar sesión",
      signingOut: "Cerrando sesión…",
      deleteAccount: "Borrar cuenta",
      deleteAccountTitle: "¿Borrar esta cuenta?",
      deleteAccountBody:
        "Se eliminará el acceso a LIMEN con este correo. Tendrás que crear una cuenta nueva para volver a entrar.",
      deleteAccountConfirm: "Borrar cuenta",
      deletingAccount: "Borrando cuenta…",
    },
    preferences: {
      title: "Tus preferencias",
      lead: "Elige cómo se ve LIMEN en este dispositivo y gestiona tu sesión.",
      hint: "Tema e idioma se guardan en este navegador, no en el servidor.",
      account: "Cuenta",
      themeHint: "Oscuro es el modo por defecto del workspace clínico.",
      languageHint: "Cambia las etiquetas de la interfaz. La voz del paciente sigue en español.",
      voice: "Voz del asistente",
      voiceHint:
        "Elige la persona de voz. En la conversación solo cambia el género gramatical y el nombre con el que se presenta. Cambia la voz y luego inicia una llamada nueva.",
      microphone: "Micrófono",
      microphoneHint:
        "Comprueba el permiso y el nivel de entrada antes de una llamada.",
      diagnostics: "Diagnóstico del runtime",
      diagnosticsHint:
        "Solo para verificación: lo que reporta el backend en este momento.",
      sessionActions: "Sesión",
      sessionActionsHint:
        "Cerrar sesión deja la cuenta intacta. Borrar cuenta es permanente.",
    },
  },

  landing: {
    nav: {
      howItWorks: "Cómo funciona",
      security: "Datos y seguridad",
      signIn: "Iniciar sesión",
      signUp: "Crear cuenta",
      enter: "Entrar al workspace",
      enterShort: "Entrar",
      home: "Inicio de LIMEN",
    },
    hero: {
      headline: "Seguimiento postoperatorio por voz, con la duda a la vista.",
      support:
        "LIMEN conversa en español con el paciente en casa, responde solo con lo que está en tus documentos clínicos y pasa la llamada a una persona cuando la seguridad lo exige.",
      enableMic: "Activar micrófono",
    },
    problem: {
      eyebrow: "El problema",
      title: "El alta no es el final del riesgo",
      body: "Las complicaciones aparecen en casa, cuando ya nadie escucha. Las llamadas manuales de seguimiento no escalan y los formularios no detectan lo que el paciente todavía no sabe nombrar.",
    },
    pillars: {
      eyebrow: "El sistema",
      title: "Cuatro superficies, un solo registro de decisión",
      lead: "Cada pilar es una pantalla real del workspace. La misma sesión las recorre todas.",
      voice: {
        name: "Voz",
        body: "Conversación en español dentro del navegador, con interrupción natural: nunca hablan dos voces a la vez.",
      },
      evidence: {
        name: "Evidencia",
        body: "Cada afirmación clínica apunta a un documento, una página y una versión que tú subiste.",
      },
      safety: {
        name: "Seguridad",
        body: "Un gobernador determinista decide la escalada. Ningún modelo generativo puede suavizarla.",
      },
      traza: {
        name: "TRAZA",
        body: "La cadena de decisión, las reglas activadas, la latencia y el coste medido quedan inspeccionables.",
      },
    },
    steps: {
      eyebrow: "Cómo funciona",
      title: "El recorrido de una sesión",
      lead: "Un bucle cerrado que va del conocimiento a la voz y termina en auditoría.",
      one: {
        title: "Carga tus fuentes clínicas",
        body: "Sube protocolos e instrucciones de alta. El índice se marca disponible solo cuando la recuperación está lista.",
      },
      two: {
        title: "Ejecuta la sesión de voz",
        body: "El paciente habla en español. LIMEN actualiza el estado clínico, recupera evidencia y responde en voz alta.",
      },
      three: {
        title: "Audita la decisión",
        body: "TRAZA conserva cada turno, el suelo de seguridad, las citas y el coste cuando la llamada termina.",
      },
    },
    security: {
      eyebrow: "Datos y seguridad",
      title: "Cada cuenta trabaja sobre su propio corpus",
      lead: "Entrar al workspace requiere cuenta. Documentos, llamadas y trazas quedan asociados al cliente que los creó.",
      isolation: {
        title: "Aislamiento por cliente",
        body: "Ningún corpus se comparte por defecto: la recuperación solo ve las fuentes de tu cuenta.",
      },
      session: {
        title: "Sesión en cookie httpOnly",
        body: "Las contraseñas se guardan con hash y el token de sesión nunca queda expuesto a JavaScript.",
      },
      deletion: {
        title: "Borrado real",
        body: "Eliminar un documento lo saca del índice y de las respuestas siguientes, no solo de la lista.",
      },
    },
    status: {
      eyebrow: "Estado actual",
      title: "Lo que ya funciona hoy",
      body: "Micrófono del navegador, detección de voz e interrupción están operativos. Transcripción, razonamiento clínico y respuesta hablada dependen del backend de voz: ninguna pantalla simula un resultado que no existe.",
    },
    voice: {
      caption: "Campo de voz",
      patient: "Paciente",
      agent: "Agente",
      legend: "El azul reacciona al paciente. El naranja marca al agente.",
      liveHint:
        "Habla: el campo se pone azul con tu voz.",
    },
    cta: {
      title: "Abre el umbral.",
      body: "Crea una cuenta, sube un protocolo y escucha la primera sesión de seguimiento.",
    },
    footer: {
      tagline:
        "Seguimiento postoperatorio por voz con incertidumbre explícita, procedencia de la evidencia y escalada determinista.",
      license: "Licencia MIT",
    },
  },

  auth: {
    brandLine: "Acceso al workspace clínico",
    aside: {
      title: "Tus fuentes, tu corpus, tu traza.",
      body: "La cuenta existe para separar los datos de cada cliente: documentos, llamadas y decisiones quedan bajo tu sesión.",
    },
    fields: {
      email: "Correo electrónico",
      password: "Contraseña",
      displayName: "Nombre",
      emailPlaceholder: "tu@clinica.com",
      passwordHint: "Mínimo 10 caracteres.",
    },
    login: {
      title: "Inicia sesión",
      subtitle: "Entra al workspace con la cuenta de tu organización.",
      submit: "Iniciar sesión",
      submitting: "Comprobando…",
      noAccount: "¿Todavía sin cuenta?",
      createAccount: "Crear una cuenta",
    },
    register: {
      title: "Crea tu cuenta",
      subtitle: "Una cuenta por cliente. Su corpus queda aislado desde el primer documento.",
      submit: "Crear cuenta",
      submitting: "Creando cuenta…",
      hasAccount: "¿Ya tienes cuenta?",
      signIn: "Iniciar sesión",
    },
    errors: {
      required: "Completa este campo.",
      email: "Escribe un correo válido.",
      passwordLength: "La contraseña necesita al menos 10 caracteres.",
      invalidCredentials: "Correo o contraseña incorrectos.",
      emailTaken: "Ya existe una cuenta con este correo.",
      unreachable:
        "El backend de LIMEN no responde. Arráncalo con `make dev-api` e inténtalo de nuevo.",
      generic: "No se pudo completar la operación. Inténtalo de nuevo.",
    },
    guard: {
      checking: "Comprobando la sesión…",
      redirect: "Inicia sesión para abrir el workspace.",
    },
  },

  call: {
    stage: "Llamada",
    transport: {
      idle: "Sin transporte",
      connecting: "Conectando voz…",
      open: "Voz conectada",
      closed: "Voz cerrada",
      error: "Voz con error",
    },
    start: "Iniciar llamada",
    end: "Terminar sesión",
    hangUp: "Colgar",
    pause: "Pausar llamada",
    resume: "Reanudar",
    controls: "Controles de llamada",
    pausedBadge: "en pausa",
    pausedHint: "Llamada en pausa. Reanude para seguir hablando con LIMEN.",
    liveContext: "Contexto en vivo",
    transcript: "Transcripción",
    turns_one: "{{count}} turno",
    turns_other: "{{count}} turnos",
    silenceTitle: "Sin turnos aún",
    silenceBody:
      "Los turnos del paciente y del agente aparecen aquí a medida que avanza la sesión.",
    hint: "El azul reacciona a tu voz. El naranja marca al agente. Habla y suelta para enviar el turno.",
    voiceActive: "Voz: {{name}}",
    blocked: "Sesión de voz bloqueada",
    retryMic: "Pedir micrófono de nuevo",
    live: {
      safetyDecision: "Decisión de seguridad",
      safetyPending: "El gobernador de seguridad aún no ha evaluado un turno.",
      escalated: "Se solicitó escalada humana.",
      openUnknowns: "Incógnitas abiertas",
      openUnknownsHint: "Hallazgos sin respuesta resuelta",
      sourcesCited: "Fuentes citadas",
      sourcesCitedHint: "Fragmentos de evidencia de este turno",
      clinicalState: "Estado clínico",
      evidence: "Evidencia",
      noEvidenceTitle: "Sin evidencia recuperada",
      noEvidenceBody:
        "Los fragmentos aparecen aquí con documento, página y proveniencia.",
    },
    clinical: {
      emptyTitle: "Aún no hay estado clínico",
      emptyBody:
        "Los hallazgos aparecen cuando el paciente responde. Nada se asume normal antes de reportarse.",
      openQuestions: "Preguntas pendientes",
      findings: {
        pain: "Dolor",
        painSeverity: "Intensidad del dolor",
        wound: "Herida",
        woundHeat: "Calor en la herida",
        fever: "Fiebre",
        bleeding: "Sangrado",
        breathing: "Respiración",
        nausea: "Náuseas",
      },
      certainty: {
        knownNormal: "Normal conocido",
        knownAbnormal: "Anormal conocido",
        improving: "Indicando mejoría",
        unknown: "Desconocido",
        conflicting: "En conflicto",
      },
    },
    risk: {
      meaning: {
        green: "Recuperación esperada",
        yellow: "Incertidumbre — revisar",
        orange: "Preocupación elevada",
        red: "Escalar a clínico",
      },
    },
    phases: {
      IDLE: { label: "En espera", description: "Sin sesión activa. Inicia una llamada para abrir el micrófono." },
      REQUESTING_MIC: { label: "Solicitando micrófono", description: "Esperando permiso del navegador." },
      LISTENING: { label: "Escuchando", description: "Puedes hablar. El campo reacciona a tu voz." },
      PROCESSING_STT: { label: "Transcribiendo", description: "Convirtiendo el último turno a texto." },
      THINKING: { label: "Razonando", description: "Actualizando estado clínico, recuperando evidencia y evaluando seguridad." },
      SPEAKING: { label: "Hablando", description: "Reproduciendo la respuesta del agente. Habla para interrumpir." },
      INTERRUPTED: { label: "Interrumpido", description: "La reproducción se detuvo porque empezaste a hablar." },
      ERROR: { label: "Error", description: "La sesión no puede continuar hasta resolver el problema." },
      ENDED: { label: "Finalizada", description: "Sesión cerrada. Revisa Sesiones o TRAZA para lo registrado." },
    },
  },

  knowledge: {
    title: "Base de conocimiento",
    selectedSource: "Fuente seleccionada",
    availableCount_one: "{{count}} disponible",
    availableCount_other: "{{count}} disponibles",
    refresh: "Actualizar lista de documentos",
    openSelected: "Abrir fuente seleccionada",
    upload: {
      title: "Añadir fuente clínica",
      body: "Suelta un PDF aquí o elige un archivo. Las páginas escaneadas usan OCR durante la ingestión.",
      choose: "Elegir archivo",
      disabled501:
        "La ingestión de conocimiento está marcada como no implementada (HTTP 501).",
    },
    uploadFailed: "Falló la subida",
    dismiss: "Descartar",
    loading: "Cargando fuentes",
    emptyApiTitle: "API de conocimiento no implementada",
    loadError: "No se pudieron cargar las fuentes",
    emptyEyebrow: "Vacío",
    emptyTitle: "Sin fuentes clínicas aún",
    emptyBody:
      "Añade un protocolo o una instrucción de alta en PDF. El agente solo puede citar documentos en estado AVAILABLE.",
    emptyApi: "No se pudo cargar el conocimiento",
    notFound: "Documento no encontrado",
    inspector: {
      emptyEyebrow: "Umbral",
      emptyTitle: "Ninguna fuente seleccionada",
      emptyBody:
        "Elige un documento para inspeccionar procedencia, estado de ingestión y recuperación.",
      probeLabel: "Sonda de recuperación",
      probePlaceholder: "Pregunta qué debería responder esta fuente",
      probeHint:
        "Ejecuta una consulta real. Tras borrarla no debe devolver fragmentos de esta fuente.",
      verify: "Verificar recuperación",
      delete: "Eliminar fuente",
      deleteTitle: "¿Eliminar esta fuente?",
      deleteBody:
        "{{name}} y todos sus fragmentos e embeddings se eliminarán. El agente clínico ya no recuperará nada de ella.",
      keep: "Conservar fuente",
      deleteNamed: "Eliminar {{name}}",
      deleteFailed: "Falló la eliminación",
      probeUnavailable: "Sonda de recuperación no disponible",
      noChunks:
        "No se devolvieron fragmentos para esta consulta. Esta fuente no aporta evidencia ahora.",
    },
  },

  trace: {
    timeline: "Línea de tiempo",
    inspector: "Inspector",
    pickTitle: "Elige una llamada para auditar",
    pickBody:
      "Cada decisión, recuperación y evaluación de seguridad se registra por llamada.",
    browseSessions: "Ver sesiones",
    recent: "Llamadas recientes",
    emptyEvents: "Sin pasos registrados",
    loadError: "No se pudo cargar la traza",
    escalated: "Escalada",
    emptyInspectTitle: "Ningún paso seleccionado",
    emptyInspectBody:
      "Elige un paso de la línea de tiempo para ver la decisión, la evidencia y el coste medido.",
  },

  sessions: {
    title: "Llamadas completadas",
    emptyTitle: "Sin llamadas registradas",
    emptyBody:
      "Las llamadas de seguimiento aparecen aquí con riesgo final, escalada y enlace a TRAZA.",
    startCall: "Iniciar una llamada",
    loadError: "No se pudieron cargar las sesiones",
    headers: {
      call: "Llamada",
      patient: "Paciente",
      procedure: "Procedimiento",
      pod: "DPO",
      started: "Inicio",
      risk: "Riesgo",
      escalated: "Escalada",
      duration: "Duración",
    },
    unknown: "Desconocido",
    yes: "Sí",
    no: "No",
    openTrace: "Traza",
    openSummary: "Resumen",
  },

  connection: {
    connected: "API activa",
    connecting: "Conectando",
    disconnected: "API caída",
    unavailable: "No disponible",
  },
} as const;
