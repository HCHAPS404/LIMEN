import "@testing-library/jest-dom/vitest";
import { beforeEach } from "vitest";

/** jsdom has no layout engine, so responsive behavior is driven by an explicit
 *  viewport width that tests can change with `setViewportWidth`. */
const DEFAULT_VIEWPORT_WIDTH = 1440;
let viewportWidth = DEFAULT_VIEWPORT_WIDTH;

const listeners = new Set<() => void>();

function toPixels(value: string): number {
  const numeric = Number.parseFloat(value);
  return value.trim().endsWith("rem") ? numeric * 16 : numeric;
}

function evaluate(query: string): boolean {
  const min = /min-width:\s*([\d.]+(?:px|rem))/.exec(query);
  if (min && viewportWidth < toPixels(min[1])) return false;

  const max = /max-width:\s*([\d.]+(?:px|rem))/.exec(query);
  if (max && viewportWidth > toPixels(max[1])) return false;

  return Boolean(min || max);
}

export function setViewportWidth(width: number): void {
  viewportWidth = width;
  for (const listener of listeners) listener();
}

window.matchMedia = (query: string): MediaQueryList => {
  const handlers = new Set<(event: MediaQueryListEvent) => void>();
  const list = {
    get matches() {
      return evaluate(query);
    },
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: (_: string, handler: (event: MediaQueryListEvent) => void) => {
      handlers.add(handler);
      listeners.add(notify);
    },
    removeEventListener: (
      _: string,
      handler: (event: MediaQueryListEvent) => void,
    ) => {
      handlers.delete(handler);
    },
    dispatchEvent: () => false,
  };

  function notify() {
    for (const handler of handlers) {
      handler({ matches: evaluate(query), media: query } as MediaQueryListEvent);
    }
  }

  return list as unknown as MediaQueryList;
};

class NoopObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords() {
    return [];
  }
}

globalThis.ResizeObserver ??= NoopObserver as unknown as typeof ResizeObserver;
globalThis.IntersectionObserver ??=
  NoopObserver as unknown as typeof IntersectionObserver;

beforeEach(() => {
  viewportWidth = DEFAULT_VIEWPORT_WIDTH;
  listeners.clear();
});
