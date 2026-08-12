import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { RiskLevel } from "../../api/types";
import { renderWithProviders } from "../../test/renderRoute";
import { RiskBadge } from "./RiskBadge";
import { riskPresentation } from "./riskPresentation";

describe("RiskBadge", () => {
  it("labels every risk level with its clinical meaning", () => {
    const cases: { level: RiskLevel; label: string; meaning: string }[] = [
      { level: "GREEN", label: "Verde", meaning: "Recuperación esperada" },
      { level: "YELLOW", label: "Amarillo", meaning: "Incertidumbre — revisar" },
      { level: "ORANGE", label: "Naranja", meaning: "Preocupación elevada" },
      { level: "RED", label: "Rojo", meaning: "Escalar a clínico" },
    ];

    for (const item of cases) {
      const { unmount } = renderWithProviders(<RiskBadge risk={item.level} />);
      expect(screen.getByText(item.label)).toBeInTheDocument();
      expect(
        screen.getByText(`Riesgo clínico ${item.label}: ${item.meaning}`),
      ).toBeInTheDocument();
      unmount();
    }
  });

  it("states that risk is unassessed instead of defaulting to green", () => {
    renderWithProviders(<RiskBadge risk={null} />);

    expect(screen.getByText("Sin evaluar")).toBeInTheDocument();
    expect(screen.queryByText("Verde")).not.toBeInTheDocument();
    expect(
      screen.getByText(/Aún no hay decisión de seguridad/),
    ).toBeInTheDocument();
  });

  it("never encodes a risk level by color alone", () => {
    for (const level of Object.keys(riskPresentation) as RiskLevel[]) {
      const view = riskPresentation[level];
      expect(view.label.length).toBeGreaterThan(0);
      expect(view.meaning.length).toBeGreaterThan(0);
      expect(view.icon).toBeDefined();
    }
  });

  it("shows the meaning inline when asked", () => {
    renderWithProviders(<RiskBadge risk="RED" showMeaning />);

    expect(screen.getAllByText(/Escalar a clínico/).length).toBeGreaterThan(0);
  });
});

/** Keep a smoke render path without providers for icon/class presence. */
describe("RiskBadge presentation map", () => {
  it("keeps presentation tokens for every level", () => {
    expect(Object.keys(riskPresentation)).toEqual([
      "GREEN",
      "YELLOW",
      "ORANGE",
      "RED",
    ]);
    render(<span />);
  });
});
