import * as RadixDialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "../../lib/cn";
import { IconButton } from "./IconButton";

type DrawerProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  children: ReactNode;
};

/** Right-side sheet. Below the desktop breakpoint the inspector column
 *  collapses into this (FRONTEND.md section 27). */
export function Drawer({ open, onOpenChange, title, children }: DrawerProps) {
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="motion-fade fixed inset-0 z-40 bg-[color-mix(in_oklab,var(--limen-bg-0)_66%,transparent)]" />
        <RadixDialog.Content
          className={cn(
            "fixed top-0 right-0 z-50 flex h-full w-[min(24rem,100vw)] flex-col",
            "border-l border-[var(--glass-border-strong)] bg-[var(--glass-inspector)]",
            "shadow-[var(--shadow-float)] backdrop-blur-[26px]",
          )}
        >
          <header className="flex shrink-0 items-center justify-between gap-3 border-b border-glass-border px-4 py-3">
            <RadixDialog.Title className="type-label m-0">
              {title}
            </RadixDialog.Title>
            <RadixDialog.Close asChild>
              <IconButton label="Close panel" icon={<X aria-hidden size={16} />} />
            </RadixDialog.Close>
          </header>
          <div className="limen-scroll min-h-0 flex-1 p-4">{children}</div>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
