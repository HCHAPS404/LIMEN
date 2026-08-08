import * as RadixDialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "../../lib/cn";
import { IconButton } from "./IconButton";

type DialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: ReactNode;
  children?: ReactNode;
  footer?: ReactNode;
};

/** Level 3 material — used sparingly for destructive confirmation. */
export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
}: DialogProps) {
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="motion-fade fixed inset-0 z-40 bg-[color-mix(in_oklab,var(--limen-bg-0)_72%,transparent)] backdrop-blur-[2px]" />
        <RadixDialog.Content
          className={cn(
            "motion-rise fixed top-1/2 left-1/2 z-50 w-[min(30rem,calc(100vw-2rem))]",
            "-translate-x-1/2 -translate-y-1/2 rounded-lg border border-[var(--glass-border-strong)]",
            "bg-[var(--glass-modal)] p-6 shadow-[var(--shadow-float)] backdrop-blur-[30px]",
          )}
        >
          <div className="flex items-start justify-between gap-4">
            <RadixDialog.Title className="type-h3 m-0 text-white-ice">
              {title}
            </RadixDialog.Title>
            <RadixDialog.Close asChild>
              <IconButton label="Close dialog" icon={<X aria-hidden size={16} />} />
            </RadixDialog.Close>
          </div>
          {description && (
            <RadixDialog.Description className="type-body mt-2 text-text-2">
              {description}
            </RadixDialog.Description>
          )}
          {children && <div className="mt-4">{children}</div>}
          {footer && (
            <div className="mt-6 flex justify-end gap-2">{footer}</div>
          )}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
