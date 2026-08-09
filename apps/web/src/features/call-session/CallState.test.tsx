import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { CallPhase } from "../../api/types";
import { renderWithProviders } from "../../test/renderRoute";
import { CallState } from "./CallState";
import { phasePresentation } from "./callPhase";

const phases = Object.keys(phasePresentation) as CallPhase[];

describe("CallState", () => {
  it("gives every voice phase its own label and explanation", () => {
    const labels = new Set<string>();
    const descriptions = new Set<string>();

    for (const phase of phases) {
      labels.add(phasePresentation[phase].label);
      descriptions.add(phasePresentation[phase].description);
    }

    expect(labels.size).toBe(phases.length);
    expect(descriptions.size).toBe(phases.length);
  });

  it("announces the phase politely for assistive technology", () => {
    const { container } = renderWithProviders(<CallState phase="LISTENING" />);
    const region = container.querySelector("[aria-live='polite']");

    expect(region).not.toBeNull();
    expect(screen.getByTestId("call-phase-label")).toHaveTextContent(
      /escuchando|listening/i,
    );
  });

  it("explains a blocked session rather than showing a bare spinner", () => {
    renderWithProviders(<CallState phase="ERROR" />);

    expect(
      screen.getByText(/no puede continuar|cannot continue/i),
    ).toBeInTheDocument();
  });
});
