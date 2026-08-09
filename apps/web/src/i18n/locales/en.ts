import type { es } from "./es";

/** English mirrors the Spanish key tree exactly; the type binding makes a missing
 *  or renamed key a compile error instead of a runtime fallback. */
type Resources = {
  readonly [Namespace in keyof typeof es]: DeepMirror<(typeof es)[Namespace]>;
};

type DeepMirror<Value> = Value extends string
  ? string
  : { readonly [Key in keyof Value]: DeepMirror<Value[Key]> };

export const en: Resources = {
  common: {
    theme: {
      label: "Theme",
      dark: "Dark",
      light: "Light",
      toDark: "Switch to dark theme",
      toLight: "Switch to light theme",
    },
    language: {
      label: "Language",
      es: "Español",
      en: "English",
      switchTo: "Switch language to {{language}}",
    },
    actions: {
      retry: "Retry",
      cancel: "Cancel",
      close: "Close",
    },
  },

  shell: {
    workspace: "Workspace",
    nav: {
      call: "Call",
      knowledge: "Knowledge",
      trace: "Trace",
      sessions: "Sessions",
      settings: "Settings",
    },
    rail: {
      collapse: "Collapse navigation",
      expand: "Expand navigation",
    },
    routes: {
      call: {
        title: "Voice call",
        subtitle: "Postoperative follow-up session",
      },
      knowledge: {
        title: "Knowledge base",
        subtitle: "Clinical corpus and retrieval lifecycle",
      },
      trace: {
        title: "TRAZA",
        subtitle: "Decision and evidence audit",
      },
      sessions: {
        title: "Sessions",
        subtitle: "Completed follow-up calls",
      },
      settings: {
        title: "Settings",
        subtitle: "Preferences for your session in this browser",
      },
      notFound: { title: "Not found" },
      fallback: { title: "Workspace" },
    },
    account: {
      menuLabel: "Account",
      signedInAs: "Signed in as",
      preferences: "Preferences",
      signOut: "Sign out",
      signingOut: "Signing out…",
      deleteAccount: "Delete account",
      deleteAccountTitle: "Delete this account?",
      deleteAccountBody:
        "Access with this email will be removed. You will need a new account to sign in again.",
      deleteAccountConfirm: "Delete account",
      deletingAccount: "Deleting account…",
    },
    preferences: {
      title: "Your preferences",
      lead: "Choose how LIMEN looks on this device and manage your session.",
      hint: "Theme and language are stored in this browser, not on the server.",
      account: "Account",
      themeHint: "Dark is the default for the clinical workspace.",
      languageHint:
        "Changes interface labels. The patient voice loop stays in Spanish.",
      voice: "Assistant voice",
      voiceHint:
        "Choose the voice persona. In chat this only changes grammatical gender and how the assistant introduces itself. Change the voice, then start a new call.",
      microphone: "Microphone",
      microphoneHint: "Check permission and input level before a call.",
      diagnostics: "Runtime diagnostics",
      diagnosticsHint: "Verification only: what the backend reports right now.",
      sessionActions: "Session",
      sessionActionsHint:
        "Sign out keeps the account. Delete account is permanent.",
    },
  },

  landing: {
    nav: {
      howItWorks: "How it works",
      security: "Data and security",
      signIn: "Sign in",
      signUp: "Create account",
      enter: "Enter workspace",
      enterShort: "Enter",
      home: "LIMEN home",
    },
    hero: {
      headline: "Postoperative follow-up by voice, with the doubt kept visible.",
      support:
        "LIMEN talks with the patient at home, answers only from the clinical documents you uploaded, and hands the call to a clinician when safety requires it.",
      enableMic: "Enable microphone",
    },
    problem: {
      eyebrow: "The problem",
      title: "Discharge is not the end of the risk",
      body: "Complications appear at home, when nobody is listening anymore. Manual follow-up calls do not scale, and forms miss what the patient cannot yet name.",
    },
    pillars: {
      eyebrow: "The system",
      title: "Four surfaces, one decision record",
      lead: "Each pillar is a real workspace screen. The same session moves through all of them.",
      voice: {
        name: "Voice",
        body: "Spanish conversation inside the browser, with natural barge-in: two voices never overlap.",
      },
      evidence: {
        name: "Evidence",
        body: "Every clinical statement points to a document, a page, and a version you uploaded.",
      },
      safety: {
        name: "Safety",
        body: "A deterministic governor decides escalation. No generative model can soften it.",
      },
      traza: {
        name: "TRAZA",
        body: "The decision chain, activated rules, latency, and measured cost stay inspectable.",
      },
    },
    steps: {
      eyebrow: "How it works",
      title: "The path of one session",
      lead: "A closed loop that runs from knowledge to voice and ends in audit.",
      one: {
        title: "Load your clinical sources",
        body: "Upload protocols and discharge instructions. The index reports available only once retrieval is ready.",
      },
      two: {
        title: "Run the voice session",
        body: "The patient speaks in Spanish. LIMEN updates clinical state, retrieves evidence, and answers out loud.",
      },
      three: {
        title: "Audit the decision",
        body: "TRAZA keeps every turn, safety floor, citation, and cost once the call ends.",
      },
    },
    security: {
      eyebrow: "Data and security",
      title: "Every account works on its own corpus",
      lead: "Entering the workspace requires an account. Documents, calls, and traces belong to the client that created them.",
      isolation: {
        title: "Per-client isolation",
        body: "No corpus is shared by default: retrieval only sees the sources in your account.",
      },
      session: {
        title: "httpOnly cookie session",
        body: "Passwords are stored hashed and the session token is never exposed to JavaScript.",
      },
      deletion: {
        title: "Real deletion",
        body: "Deleting a document removes it from the index and from later answers, not just from a list.",
      },
    },
    status: {
      eyebrow: "Current state",
      title: "What already works today",
      body: "Browser microphone, voice activity detection, and barge-in are operational. Transcription, clinical reasoning, and spoken replies depend on the voice backend: no screen simulates a result that does not exist.",
    },
    voice: {
      caption: "Voice field",
      patient: "Patient",
      agent: "Agent",
      legend: "Blue reacts to the patient. Orange marks the agent.",
      liveHint: "Speak: the field turns blue with your voice.",
    },
    cta: {
      title: "Open the threshold.",
      body: "Create an account, upload a protocol, and listen to the first follow-up session.",
    },
    footer: {
      tagline:
        "Voice-first postoperative follow-up with explicit uncertainty, evidence provenance, and deterministic escalation.",
      license: "MIT licensed",
    },
  },

  auth: {
    brandLine: "Access to the clinical workspace",
    aside: {
      title: "Your sources, your corpus, your trace.",
      body: "The account exists to separate each client's data: documents, calls, and decisions stay under your session.",
    },
    fields: {
      email: "Email",
      password: "Password",
      displayName: "Name",
      emailPlaceholder: "you@clinic.com",
      passwordHint: "At least 10 characters.",
    },
    login: {
      title: "Sign in",
      subtitle: "Enter the workspace with your organisation account.",
      submit: "Sign in",
      submitting: "Checking…",
      noAccount: "No account yet?",
      createAccount: "Create an account",
    },
    register: {
      title: "Create your account",
      subtitle: "One account per client. Its corpus is isolated from the first document.",
      submit: "Create account",
      submitting: "Creating account…",
      hasAccount: "Already have an account?",
      signIn: "Sign in",
    },
    errors: {
      required: "Fill in this field.",
      email: "Enter a valid email address.",
      passwordLength: "The password needs at least 10 characters.",
      invalidCredentials: "Wrong email or password.",
      emailTaken: "An account with this email already exists.",
      unreachable:
        "The LIMEN backend is not responding. Start it with `make dev-api` and try again.",
      generic: "The operation could not be completed. Try again.",
    },
    guard: {
      checking: "Checking the session…",
      redirect: "Sign in to open the workspace.",
    },
  },

  call: {
    stage: "Call",
    transport: {
      idle: "No voice link",
      connecting: "Connecting voice…",
      open: "Voice linked",
      closed: "Voice closed",
      error: "Voice error",
    },
    start: "Start call",
    end: "End session",
    hangUp: "Hang up",
    pause: "Pause call",
    resume: "Resume",
    controls: "Call controls",
    pausedBadge: "paused",
    pausedHint: "Call paused. Resume to keep talking with LIMEN.",
    liveContext: "Live context",
    transcript: "Transcript",
    turns_one: "{{count}} turn",
    turns_other: "{{count}} turns",
    silenceTitle: "No turns yet",
    silenceBody:
      "Patient and agent turns appear here as the session progresses.",
    hint: "Blue reacts to your voice. Orange marks the agent. Speak, then pause to send the turn.",
    voiceActive: "Voice: {{name}}",
    blocked: "Voice session blocked",
    retryMic: "Request microphone again",
    live: {
      safetyDecision: "Safety decision",
      safetyPending: "The Safety Governor has not evaluated a turn yet.",
      escalated: "Human escalation requested.",
      openUnknowns: "Open unknowns",
      openUnknownsHint: "Findings without a resolved answer",
      sourcesCited: "Sources cited",
      sourcesCitedHint: "Distinct evidence chunks this turn",
      clinicalState: "Clinical state",
      evidence: "Evidence",
      noEvidenceTitle: "No evidence retrieved",
      noEvidenceBody:
        "Retrieved chunks appear here with document, page, and version provenance.",
    },
    clinical: {
      emptyTitle: "No clinical state yet",
      emptyBody:
        "Findings appear as the patient answers. Nothing is assumed normal before it is reported.",
      openQuestions: "Unresolved questions",
      findings: {
        pain: "Pain",
        painSeverity: "Pain severity",
        wound: "Wound",
        woundHeat: "Wound heat",
        fever: "Fever",
        bleeding: "Bleeding",
        breathing: "Breathing",
        nausea: "Nausea",
      },
      certainty: {
        knownNormal: "Known normal",
        knownAbnormal: "Known abnormal",
        improving: "Improving",
        unknown: "Unknown",
        conflicting: "Conflicting",
      },
    },
    risk: {
      meaning: {
        green: "Expected recovery",
        yellow: "Uncertain — review",
        orange: "Elevated concern",
        red: "Escalate to clinician",
      },
    },
    phases: {
      IDLE: { label: "Idle", description: "No active session. Start a call to open the microphone." },
      REQUESTING_MIC: { label: "Requesting microphone", description: "Waiting for browser microphone permission." },
      LISTENING: { label: "Listening", description: "You can speak. The field reacts to your voice." },
      PROCESSING_STT: { label: "Transcribing", description: "Converting the last patient turn to text." },
      THINKING: { label: "Reasoning", description: "Updating clinical state, retrieving evidence, evaluating safety." },
      SPEAKING: { label: "Speaking", description: "Playing the agent response. Speak to interrupt." },
      INTERRUPTED: { label: "Interrupted", description: "Playback stopped because you started speaking." },
      ERROR: { label: "Error", description: "The session cannot continue until the problem is resolved." },
      ENDED: { label: "Ended", description: "Session closed. Open Sessions or TRAZA to review what was recorded." },
    },
  },

  knowledge: {
    title: "Knowledge base",
    selectedSource: "Selected source",
    availableCount_one: "{{count}} available",
    availableCount_other: "{{count}} available",
    refresh: "Refresh document list",
    openSelected: "Open selected source",
    upload: {
      title: "Add clinical source",
      body: "Drop a PDF here, or choose a file. Scanned pages fall back to OCR during ingestion.",
      choose: "Choose file",
      disabled501:
        "Knowledge ingestion is marked not implemented (HTTP 501).",
    },
    uploadFailed: "Upload failed",
    dismiss: "Dismiss",
    loading: "Loading sources",
    emptyApiTitle: "Knowledge API not implemented",
    loadError: "Could not load sources",
    emptyEyebrow: "Empty",
    emptyTitle: "No clinical sources yet",
    emptyBody:
      "Add a protocol or discharge instruction PDF. The agent can only cite documents that reach AVAILABLE.",
    emptyApi: "Could not load knowledge",
    notFound: "Document not found",
    inspector: {
      emptyEyebrow: "Threshold",
      emptyTitle: "No source selected",
      emptyBody:
        "Choose a document to inspect its provenance, ingestion state, and retrieval behavior.",
      probeLabel: "Retrieval probe",
      probePlaceholder: "Ask what this source should answer",
      probeHint:
        "Runs a real retrieval query. After deletion it should return no chunks from this source.",
      verify: "Verify retrieval",
      delete: "Delete source",
      deleteTitle: "Delete this source?",
      deleteBody:
        "{{name}} and all of its chunks and embeddings will be removed. The clinical agent will no longer retrieve anything from it.",
      keep: "Keep source",
      deleteNamed: "Delete {{name}}",
      deleteFailed: "Deletion failed",
      probeUnavailable: "Retrieval probe unavailable",
      noChunks:
        "No chunks returned for this query. This source contributes no evidence right now.",
    },
  },

  trace: {
    timeline: "Timeline",
    inspector: "Inspector",
    pickTitle: "Choose a call to audit",
    pickBody:
      "Every decision, retrieval, and safety evaluation is recorded per call.",
    browseSessions: "Browse sessions",
    recent: "Recent calls",
    emptyEvents: "No recorded steps",
    loadError: "Could not load trace",
    escalated: "Escalated",
    emptyInspectTitle: "No step selected",
    emptyInspectBody:
      "Pick a timeline step to see the decision, the evidence behind it, and the measured cost of that turn.",
  },

  sessions: {
    title: "Completed calls",
    emptyTitle: "No calls recorded",
    emptyBody:
      "Follow-up calls appear here with final risk, escalation, and a link to TRAZA.",
    startCall: "Start a call",
    loadError: "Could not load sessions",
    headers: {
      call: "Call",
      patient: "Patient",
      procedure: "Procedure",
      pod: "POD",
      started: "Started",
      risk: "Risk",
      escalated: "Escalated",
      duration: "Duration",
    },
    unknown: "Unknown",
    yes: "Yes",
    no: "No",
    openTrace: "Trace",
    openSummary: "Summary",
  },

  connection: {
    connected: "API up",
    connecting: "Connecting",
    disconnected: "API down",
    unavailable: "Unavailable",
  },
};
