import * as RadixTooltip from "@radix-ui/react-tooltip";
import type { ReactNode } from "react";

export function TooltipProvider({ children }: { children: ReactNode }) {
  return (
    <RadixTooltip.Provider delayDuration={280} skipDelayDuration={120}>
      {children}
    </RadixTooltip.Provider>
  );
}

type TooltipProps = {
  content: ReactNode;
  side?: "top" | "right" | "bottom" | "left";
  children: ReactNode;
};

export function Tooltip({ content, side = "right", children }: TooltipProps) {
  return (
    <RadixTooltip.Root>
      <RadixTooltip.Trigger asChild>{children}</RadixTooltip.Trigger>
      <RadixTooltip.Portal>
        <RadixTooltip.Content
          side={side}
          sideOffset={8}
          className="glass-2 motion-fade z-50 max-w-[16rem] rounded-xs px-2.5 py-1.5 text-[0.8125rem] text-ice"
        >
          {content}
        </RadixTooltip.Content>
      </RadixTooltip.Portal>
    </RadixTooltip.Root>
  );
}
