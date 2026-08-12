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
    risk: {
      label: {
        green: "Green",
        yellow: "Yellow",
        orange: "Orange",
        red: "Red",
        unassessed: "Unassessed",
      },
      meaning: {
        green: "Expected recovery",
        yellow: "Uncertain — review",
        orange: "Elevated concern",
        red: "Escalate to clinician",
        unassessed: "No safety decision yet",
      },
      sr: "Clinical risk {{label}}: {{meaning}}",
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
      home: "Go to LIMEN landing",
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
      copyright: "LIMEN",
      columns: {
        product: "Product",
        access: "Access",
        legal: "Legal",
      },
      links: {
        howItWorks: "How it works",
        security: "Data and security",
        status: "Current state",
        signIn: "Sign in",
        signUp: "Create account",
        enter: "Enter workspace",
        license: "MIT license",
      },
      note: {
        title: "LIMEN",
        handle: "clinical workspace",
        body: "Voice, provenance-backed evidence, and deterministic escalation in one decision record.",
      },
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
    callNotFound: "Call {{callId}} was not found.",
    escalated: "Escalated",
    emptyInspectTitle: "No step selected",
    emptyInspectBody:
      "Pick a timeline step to see what happened, which evidence was used, and any measurements for that step.",
    sequence: "Step {{sequence}} · {{time}}",
    statusOk: "OK",
    statusError: "Error",
    statusSkipped: "Skipped",
    sections: {
      whatHappened: "What happened",
      detail: "Detail",
      safety: "Safety decision",
      escalated: "Human clinical attention was requested.",
      reasons: "Activated rules",
      evidence: "Cited evidence",
      measurements: "Measurements for this step",
      facts: "Step facts",
      noExtra:
        "This step has no cost metrics. The description and timestamp are the full record.",
    },
    evidence: {
      page: "p. {{page}}",
      pageUnknown: "page unknown",
      version: "v{{version}}",
      score: "score {{score}}",
    },
    metrics: {
      duration: "Duration",
      durationHint: "Time for this operation",
      latency: "Latency",
      latencyHint: "Turn round trip",
      clinical: "Clinical",
      clinicalHint: "State extraction",
      uncertainty: "Uncertainty",
      uncertaintyHint: "Certainty analysis",
      retrieval: "Retrieval",
      retrievalHint: "Evidence search",
      safety: "Safety",
      safetyHint: "Risk evaluation",
      generation: "Generation",
      generationHint: "Model response",
      dense: "Dense",
      denseHint: "Vector retrieval",
      lexical: "Lexical",
      lexicalHint: "Keyword retrieval",
      fusion: "Fusion",
      fusionHint: "Hybrid merge",
      llmCalls: "Model calls",
      llmCallsHint: "LLM invocations",
      inputTokens: "Input tokens",
      inputTokensHint: "Prompt tokens",
      outputTokens: "Output tokens",
      outputTokensHint: "Completion tokens",
      ragQueries: "RAG queries",
      ragQueriesHint: "Corpus searches",
      evidenceSelected: "Chunks",
      evidenceSelectedHint: "Selected evidence",
      estCost: "Est. cost",
      estCostHint: "Estimated from token usage",
      voiceLatency: "Voice latency",
      voiceLatencyHint: "Audio response",
      stt: "Transcription",
      sttHint: "STT duration",
      tts: "Speech synthesis",
      ttsHint: "TTS duration",
      notMeasured: "Not measured on this step",
    },
    facts: {
      provider: "Provider",
      model: "Model",
      persona: "Voice persona",
      voice_id: "Voice id",
      assistant_display_name: "Assistant name",
      patient_alias: "Patient alias",
      turn_seq: "Turn number",
      turn_id: "Turn id",
      bytes: "Audio bytes",
      audio_bytes: "Audio bytes",
      confidence: "Confidence",
      stt_confidence: "Transcription confidence",
      transcript_preview: "Transcript preview",
      fallback_reason: "Fallback reason",
      error: "Error",
      message: "Message",
      finding_count: "Findings",
      chunk_count: "Chunks",
      selected_chunk_ids: "Selected chunks",
      intent: "Intent",
      question: "Pending question",
      answer_preview: "Answer preview",
      true: "Yes",
      false: "No",
    },
    categories: {
      call: "Call",
      patient: "Patient",
      clinical: "Clinical",
      uncertainty: "Uncertainty",
      retrieval: "Evidence",
      safety: "Safety",
      response: "Response",
      escalation: "Escalation",
      error: "Error",
      voice: "Voice",
      transcription: "Transcription",
      speechSynthesis: "Speech synthesis",
      conversation: "Conversation",
      reasoning: "Reasoning",
      knowledge: "Knowledge",
      step: "Step",
    },
    events: {
      call_started: {
        title: "Call started",
        summary: "The follow-up session opened and is ready to capture voice.",
      },
      call_completed: {
        title: "Call ended",
        summary: "The session closed. Final risk and escalation stay on record.",
      },
      turn_received: {
        title: "Patient spoke",
        summary: "A patient voice or text turn was received.",
      },
      turn_processing_started: {
        title: "Turn processing started",
        summary: "The system is analyzing what was said to update clinical state.",
      },
      turn_completed: {
        title: "Turn completed",
        summary: "This listen–reason–respond cycle finished.",
      },
      clinical_extraction_started: {
        title: "Clinical extraction in progress",
        summary: "Findings are being read from what the patient said.",
      },
      clinical_extraction_completed: {
        title: "Clinical extraction ready",
        summary: "Clinical state was updated with detected findings.",
      },
      clinical_state_updated: {
        title: "Clinical state updated",
        summary: "The session clinical chart changed (findings and certainty).",
      },
      clinical_uncertainty_completed: {
        title: "Uncertainty analysis",
        summary: "What is clear, unknown, or conflicting was marked.",
      },
      retrieval_started: {
        title: "Evidence search started",
        summary: "The client clinical corpus was queried to support the reply.",
      },
      retrieval_dense_completed: {
        title: "Vector search ready",
        summary: "Semantic similarity retrieval finished.",
      },
      retrieval_lexical_completed: {
        title: "Keyword search ready",
        summary: "Lexical (keyword) retrieval finished.",
      },
      retrieval_fusion_completed: {
        title: "Evidence fusion ready",
        summary: "Dense and lexical results were combined.",
      },
      retrieval_evidence_selected: {
        title: "Evidence selected",
        summary: "Corpus excerpts were chosen to ground the reply.",
      },
      safety_evaluation_completed: {
        title: "Safety evaluation",
        summary: "The safety governor set risk level and whether to escalate.",
      },
      response_generation_started: {
        title: "Generating reply",
        summary: "The assistant is composing the spoken reply.",
      },
      response_generation_completed: {
        title: "Assistant reply",
        summary: "The reply that plays to the patient is ready.",
      },
      response_fallback: {
        title: "Fallback reply",
        summary: "A deterministic reply was used because generation was unavailable.",
      },
      voice_mic_requested: {
        title: "Microphone requested",
        summary: "The browser asked for permission to capture patient voice.",
      },
      voice_mic_granted: {
        title: "Microphone granted",
        summary: "Microphone permission is available; the session can listen.",
      },
      voice_speech_started: {
        title: "Patient started speaking",
        summary: "Voice was detected on the microphone.",
      },
      voice_speech_ended: {
        title: "Patient stopped speaking",
        summary: "The voice segment ended; the turn can be sent.",
      },
      voice_audio_upload_completed: {
        title: "Audio uploaded",
        summary: "The patient audio segment reached the server.",
      },
      voice_playback_started: {
        title: "Playback started",
        summary: "The patient begins hearing the assistant reply.",
      },
      voice_playback_completed: {
        title: "Playback finished",
        summary: "The assistant reply finished playing.",
      },
      voice_interrupted: {
        title: "Reply interrupted",
        summary: "The patient spoke while the assistant was answering.",
      },
      voice_patient_cutoff: {
        title: "Patient voice cut off",
        summary: "The patient voice segment ended early.",
      },
      voice_false_barge_in: {
        title: "False interruption discarded",
        summary: "Noise or a false positive was not treated as a real barge-in.",
      },
      stt_started: {
        title: "Transcription started",
        summary: "Patient audio is being converted to text.",
      },
      stt_completed: {
        title: "Transcription ready",
        summary: "The patient turn is text and ready for clinical reasoning.",
      },
      tts_started: {
        title: "Speech synthesis started",
        summary: "The assistant reply is being converted to audio.",
      },
      tts_first_audio: {
        title: "First reply audio",
        summary: "The first audible fragment of the reply arrived.",
      },
      tts_completed: {
        title: "Speech synthesis ready",
        summary: "Full reply audio is available.",
      },
      conversation_context_built: {
        title: "Conversation context built",
        summary: "Context for this turn was prepared for the assistant.",
      },
      conversation_pending_question: {
        title: "Pending question",
        summary: "The assistant left an open question for the next turn.",
      },
      conversation_question_answered: {
        title: "Question answered",
        summary: "The patient answered a pending question.",
      },
      conversation_response_interrupted: {
        title: "Conversational reply interrupted",
        summary: "The in-progress reply was cut by an interruption.",
      },
      conversation_intent_pending: {
        title: "Intent under analysis",
        summary: "What the patient intends to communicate is being interpreted.",
      },
      conversation_intent_completed: {
        title: "Intent determined",
        summary: "Detected intent for this turn is clear.",
      },
      escalation_artifact_persisted: {
        title: "Escalation record saved",
        summary: "The escalation artifact was persisted for clinical follow-up.",
      },
      provider_error: {
        title: "Provider error",
        summary: "An external service failed; details stay on this step.",
      },
      patient_statement: {
        title: "Patient statement",
        summary: "Patient text or voice for this turn.",
      },
      clinical_extraction: {
        title: "Clinical extraction",
        summary: "Findings were extracted from the patient turn.",
      },
      uncertainty: {
        title: "Clinical uncertainty",
        summary: "Certainty, unknowns, and conflicts were evaluated.",
      },
      retrieval: {
        title: "Evidence retrieval",
        summary: "The client clinical corpus was queried.",
      },
      safety_evaluation: {
        title: "Safety evaluation",
        summary: "Risk and escalation need were set.",
      },
      response: {
        title: "Reply",
        summary: "Assistant reply for this turn.",
      },
      escalation: {
        title: "Escalation",
        summary: "A clinical escalation was triggered or recorded.",
      },
      session_end: {
        title: "Session end",
        summary: "The follow-up call was closed.",
      },
      unknown: {
        title: "Recorded step",
        summary: "Audit event without a specific label yet.",
      },
    },
    reasons: {
      noRule: "No alert rule triggered",
      noYellowFindings: "No yellow findings in state",
      generativeDefault: "Assisted reply (safety floor)",
      expectedRecovery: "Expected recovery",
      yellowFever: "Text pattern: fever",
      yellowNausea: "Text pattern: nausea",
      yellowPattern: "Caution pattern (yellow)",
      redPattern: "Urgency pattern (red)",
      stateFinding: "State finding: {{detail}}",
      overrideBlocked: "Generation cannot lower severity",
    },
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
