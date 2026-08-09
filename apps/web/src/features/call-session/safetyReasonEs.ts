/** Map raw Safety Governor reason codes to short Spanish labels for operators. */

const EXACT: Record<string, string> = {
  no_rule_triggered: "Sin regla de alerta",
  state_no_yellow_findings: "Sin hallazgos amarillos en estado",
  generative_default: "Respuesta asistida (piso de seguridad)",
  Expected_recovery: "Recuperación esperada",
};

export function humanizeSafetyReason(reason: string): string {
  if (EXACT[reason]) return EXACT[reason];
  if (reason === "Expected recovery" || reason.toLowerCase() === "expected recovery") {
    return "Recuperación esperada";
  }
  if (reason.startsWith("yellow_pattern:")) {
    if (reason.includes("fiebre")) return "Patrón textual: fiebre";
    if (reason.includes("nause")) return "Patrón textual: náuseas";
    return "Patrón de precaución (amarillo)";
  }
  if (reason.startsWith("red_pattern:")) return "Patrón de urgencia (rojo)";
  if (reason.startsWith("state_finding:")) {
    const body = reason.slice("state_finding:".length);
    return `Hallazgo de estado: ${body.replace(/:/g, " · ")}`;
  }
  if (reason.includes("generative_override_blocked")) {
    return "La generación no puede bajar la severidad";
  }
  return reason
    .replaceAll("_", " ")
    .replaceAll("\\b", "")
    .replaceAll("\\", "");
}
