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
        subtitle: "Preferences and runtime diagnostics",
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
    },
    preferences: {
      title: "Preferences",
      hint: "Stored in this browser, not on the server.",
      account: "Account",
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
};
