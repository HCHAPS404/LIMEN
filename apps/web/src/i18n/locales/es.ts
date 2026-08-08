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
    workspace: "Workspace",
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
        subtitle: "Preferencias y diagnóstico del runtime",
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
    },
    preferences: {
      title: "Preferencias",
      hint: "Se guardan en este navegador, no en el servidor.",
      account: "Cuenta",
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
} as const;
