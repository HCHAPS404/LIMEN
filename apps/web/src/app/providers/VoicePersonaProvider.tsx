import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

export type VoicePersonaId = "elena" | "nikolas" | "anikka" | "alex";

export type VoicePersonaOption = {
  id: VoicePersonaId;
  displayName: string;
  gender: "female" | "male";
  blurb: string;
};

export const VOICE_PERSONA_STORAGE_KEY = "limen.voice_persona";
export const DEFAULT_VOICE_PERSONA: VoicePersonaId = "elena";

export const VOICE_PERSONAS: VoicePersonaOption[] = [
  {
    id: "elena",
    displayName: "Elena",
    gender: "female",
    blurb: "Señora — voz femenina más natural (Sharvard F).",
  },
  {
    id: "nikolas",
    displayName: "Nikolas",
    gender: "male",
    blurb: "Señor — español de España.",
  },
  {
    id: "anikka",
    displayName: "Anikka",
    gender: "female",
    blurb: "Joven adulta (~25) — español latinoamericano.",
  },
  {
    id: "alex",
    displayName: "Alex",
    gender: "male",
    blurb: "Joven adulto (~26) — voz masculina más natural (Sharvard M).",
  },
];

type VoicePersonaContextValue = {
  personaId: VoicePersonaId;
  persona: VoicePersonaOption;
  setPersonaId: (id: VoicePersonaId) => void;
  personas: VoicePersonaOption[];
};

const VoicePersonaContext = createContext<VoicePersonaContextValue | null>(null);

function isPersonaId(value: string | null): value is VoicePersonaId {
  return (
    value === "elena" ||
    value === "nikolas" ||
    value === "anikka" ||
    value === "alex"
  );
}

export function readStoredVoicePersona(): VoicePersonaId {
  try {
    const stored = window.localStorage.getItem(VOICE_PERSONA_STORAGE_KEY);
    return isPersonaId(stored) ? stored : DEFAULT_VOICE_PERSONA;
  } catch {
    return DEFAULT_VOICE_PERSONA;
  }
}

function optionFor(id: VoicePersonaId): VoicePersonaOption {
  return VOICE_PERSONAS.find((p) => p.id === id) ?? VOICE_PERSONAS[0];
}

export function VoicePersonaProvider({ children }: { children: ReactNode }) {
  const [personaId, setPersonaId] = useState<VoicePersonaId>(readStoredVoicePersona);

  useEffect(() => {
    try {
      window.localStorage.setItem(VOICE_PERSONA_STORAGE_KEY, personaId);
    } catch {
      // Session-only when storage is blocked.
    }
  }, [personaId]);

  return (
    <VoicePersonaContext.Provider
      value={{
        personaId,
        persona: optionFor(personaId),
        setPersonaId,
        personas: VOICE_PERSONAS,
      }}
    >
      {children}
    </VoicePersonaContext.Provider>
  );
}

export function useVoicePersona(): VoicePersonaContextValue {
  const context = useContext(VoicePersonaContext);
  if (!context) {
    throw new Error("useVoicePersona must be used inside VoicePersonaProvider.");
  }
  return context;
}
