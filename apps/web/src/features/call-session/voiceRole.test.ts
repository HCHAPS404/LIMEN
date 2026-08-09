import { describe, expect, it } from "vitest";

import { voiceEnergy, voiceRoleFromPhase } from "./voiceRole";

describe("voiceRoleFromPhase", () => {
  it("maps patient turns to the blue voice field", () => {
    expect(voiceRoleFromPhase("LISTENING")).toBe("patient");
    expect(voiceRoleFromPhase("INTERRUPTED")).toBe("patient");
    expect(voiceRoleFromPhase("REQUESTING_MIC")).toBe("patient");
  });

  it("maps agent playback to the orange voice field", () => {
    expect(voiceRoleFromPhase("SPEAKING")).toBe("agent");
  });

  it("keeps idle and ended neutral", () => {
    expect(voiceRoleFromPhase("IDLE")).toBe("idle");
    expect(voiceRoleFromPhase("ENDED")).toBe("idle");
    expect(voiceRoleFromPhase("ERROR")).toBe("idle");
  });
});

describe("voiceEnergy", () => {
  it("amplifies quiet speech but soft-caps loud peaks so the sphere stays on canvas", () => {
    const quiet = voiceEnergy("patient", 0.06, 0);
    expect(quiet).toBeGreaterThan(0.3);
    expect(quiet).toBeLessThan(0.78);
    expect(voiceEnergy("patient", -1, 0)).toBe(0);
    expect(voiceEnergy("patient", 1, 0)).toBeLessThanOrEqual(0.78);
    expect(voiceEnergy("patient", 0.4, 0)).toBeLessThanOrEqual(0.78);
  });

  it("keeps agent energy above a resting floor without mic input", () => {
    expect(voiceEnergy("agent", 0, 0)).toBeGreaterThan(0.3);
  });
});
