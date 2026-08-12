import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Link } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { Button } from "./Button";
import { IconButton } from "./IconButton";
import { Select } from "./Select";
import { TextField } from "./TextField";
import { Toggle } from "./Toggle";

describe("Button", () => {
  it("renders an icon alongside a slotted link child", () => {
    render(
      <MemoryRouter>
        <Button asChild icon={<span data-testid="icon" />}>
          <Link to="/call">Enter workspace</Link>
        </Button>
      </MemoryRouter>,
    );

    const link = screen.getByRole("link", { name: /enter workspace/i });
    expect(link).toHaveAttribute("href", "/call");
    expect(screen.getByTestId("icon")).toBeInTheDocument();
  });

  it("keeps the inverse label legible on teal glass when slotted", () => {
    render(
      <MemoryRouter>
        <Button asChild variant="inverse">
          <Link to="/call">Enter workspace</Link>
        </Button>
      </MemoryRouter>,
    );

    // Slot merges the variant classes onto the link. Teal glass + ink-on-accent
    // stays legible in both themes; avoid arbitrary text-[var(...)] utilities.
    const link = screen.getByRole("link", { name: /enter workspace/i });
    expect(link).toHaveClass(
      "bg-action-glass",
      "text-ink-on-accent",
      "backdrop-blur-[18px]",
    );
    expect(link.className).not.toMatch(/text-\[var\(/);
  });

  it("blocks interaction and announces work while loading", () => {
    const onClick = vi.fn();
    render(
      <Button loading onClick={onClick}>
        Delete source
      </Button>,
    );

    const button = screen.getByRole("button", { name: /delete source/i });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");

    fireEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });
});

describe("IconButton", () => {
  it("requires an accessible name for an icon-only control", () => {
    render(<IconButton label="Collapse navigation" icon={<span />} />);

    expect(
      screen.getByRole("button", { name: "Collapse navigation" }),
    ).toBeInTheDocument();
  });
});

describe("TextField", () => {
  it("keeps the label visible and links it to the input", () => {
    render(<TextField label="Retrieval probe" placeholder="Ask something" />);

    const input = screen.getByLabelText("Retrieval probe");
    expect(input).toHaveAttribute("placeholder", "Ask something");
  });

  it("reports errors as text, not color alone", () => {
    render(<TextField label="Query" error="Enter at least one term." />);

    const input = screen.getByLabelText("Query");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Enter at least one term.")).toBeInTheDocument();
  });
});

describe("Select", () => {
  it("exposes the current value under a visible label", () => {
    render(
      <Select
        label="Runtime model"
        value="stub"
        options={[
          { value: "stub", label: "Stub" },
          { value: "ollama", label: "Ollama" },
        ]}
        onValueChange={() => {}}
      />,
    );

    expect(
      screen.getByRole("combobox", { name: "Runtime model" }),
    ).toHaveTextContent("Stub");
  });
});

describe("Toggle", () => {
  it("reports its checked state and reacts to clicks", () => {
    const onCheckedChange = vi.fn();
    render(
      <Toggle
        label="Evaluation mode"
        checked={false}
        onCheckedChange={onCheckedChange}
      />,
    );

    const toggle = screen.getByRole("switch", { name: "Evaluation mode" });
    expect(toggle).toHaveAttribute("aria-checked", "false");

    fireEvent.click(toggle);
    expect(onCheckedChange).toHaveBeenCalledWith(true);
  });

  it("stays inert when disabled", () => {
    const onCheckedChange = vi.fn();
    render(
      <Toggle
        label="Danger switch"
        checked
        disabled
        onCheckedChange={onCheckedChange}
      />,
    );

    fireEvent.click(screen.getByRole("switch", { name: "Danger switch" }));
    expect(onCheckedChange).not.toHaveBeenCalled();
  });
});
