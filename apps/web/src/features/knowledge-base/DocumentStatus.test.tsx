import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { DocumentStatus as DocumentStatusValue } from "../../api/types";
import { DocumentStatus } from "./DocumentStatus";
import { documentStatusView } from "./documentStatusView";

describe("DocumentStatus", () => {
  it("renders a distinct label for every lifecycle state", () => {
    const statuses = Object.keys(documentStatusView) as DocumentStatusValue[];
    const labels = new Set<string>();

    for (const status of statuses) {
      const { unmount } = render(<DocumentStatus status={status} />);
      const label = documentStatusView[status].label;
      expect(screen.getByText(label)).toBeInTheDocument();
      labels.add(label);
      unmount();
    }

    expect(labels.size).toBe(statuses.length);
  });

  it("marks AVAILABLE with the evidence tone, not the clinical risk green", () => {
    expect(documentStatusView.AVAILABLE.tone).toBe("evidence");
    expect(documentStatusView.AVAILABLE.pending).toBe(false);
  });

  it("treats every pre-AVAILABLE state as pending and not retrievable", () => {
    for (const status of [
      "UPLOADING",
      "PROCESSING",
      "INDEXING",
      "REMOVING",
    ] as DocumentStatusValue[]) {
      expect(documentStatusView[status].pending).toBe(true);
    }
    expect(documentStatusView.PROCESSING.meaning).toMatch(/not retrievable/i);
    expect(documentStatusView.INDEXING.meaning).toMatch(/not retrievable/i);
  });

  it("explains that removal deletes all retrieval material", () => {
    render(<DocumentStatus status="REMOVED" />);

    expect(screen.getByTitle(/retrieval material for this document is gone/i))
      .toBeInTheDocument();
  });
});
