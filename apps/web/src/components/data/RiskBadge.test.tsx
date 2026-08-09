import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { RiskLevel } from "../../api/types";
import { RiskBadge } from "./RiskBadge";
import { riskMeaning, riskPresentation, riskView } from "./riskPresentation";

describe("RiskBadge", () => {
  it("labels every risk level with its clinical meaning", () => {
    const levels: RiskLevel[] = ["GREEN", "YELLOW", "ORANGE", "RED"];

    for (const level of levels) {
      const { unmount } = render(<RiskBadge risk={level} />);
      const view = riskView(level);
      expect(screen.getByText(view.label)).toBeInTheDocument();
      expect(
        screen.getByText(`Riesgo clínico ${view.label}: ${view.meaning}`),
      ).toBeInTheDocument();
      unmount();
    }
  });

  it("states that risk is unassessed instead of defaulting to GREEN", () => {
    render(<RiskBadge risk={null} />);

    expect(screen.getByText("SIN EVALUAR")).toBeInTheDocument();
    expect(screen.queryByText("VERDE")).not.toBeInTheDocument();
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
    render(<RiskBadge risk="RED" showMeaning />);

    expect(screen.getAllByText(/Escalar a clínico/).length).toBeGreaterThan(0);
    expect(riskMeaning("RED")).toMatch(/Escalar/i);
  });
});
