import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { RiskLevel } from "../../api/types";
import { RiskBadge } from "./RiskBadge";
import { riskMeaning, riskPresentation } from "./riskPresentation";

describe("RiskBadge", () => {
  it("labels every risk level with its clinical meaning", () => {
    const levels: RiskLevel[] = ["GREEN", "YELLOW", "ORANGE", "RED"];

    for (const level of levels) {
      const { unmount } = render(<RiskBadge risk={level} />);
      expect(screen.getByText(level)).toBeInTheDocument();
      expect(
        screen.getByText(`Clinical risk ${level}: ${riskMeaning(level)}`),
      ).toBeInTheDocument();
      unmount();
    }
  });

  it("states that risk is unassessed instead of defaulting to GREEN", () => {
    render(<RiskBadge risk={null} />);

    expect(screen.getByText("NOT ASSESSED")).toBeInTheDocument();
    expect(screen.queryByText("GREEN")).not.toBeInTheDocument();
    expect(
      screen.getByText(/No safety decision recorded/),
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

    expect(screen.getAllByText(/Escalate to clinician/).length).toBeGreaterThan(0);
  });
});
