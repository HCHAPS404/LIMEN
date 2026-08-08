import { Upload } from "lucide-react";
import { useId, useRef, useState, type DragEvent } from "react";

import { Button } from "../../components/primitives/Button";
import { cn } from "../../lib/cn";

/** Drag/drop plus file picker (FRONTEND.md section 24). Progress reflects the
 *  request lifecycle only; readiness comes from the backend document status. */
export function UploadDropzone({
  onFiles,
  busy,
  disabled,
  disabledReason,
}: {
  onFiles: (files: File[]) => void;
  busy?: boolean;
  disabled?: boolean;
  disabledReason?: string;
}) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const accept = (files: FileList | null) => {
    if (!files || files.length === 0 || disabled) return;
    onFiles(Array.from(files));
  };

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    accept(event.dataTransfer.files);
  };

  return (
    <div
      onDragOver={(event) => {
        event.preventDefault();
        if (!disabled) setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      className={cn(
        "flex flex-col items-center gap-5 rounded-md border border-dashed px-7 py-9 text-center",
        "transition-colors duration-[var(--motion-fast)] ease-[var(--motion-ease)]",
        dragging
          ? "border-[color-mix(in_oklab,var(--limen-cyan)_50%,transparent)] bg-[color-mix(in_oklab,var(--limen-cyan)_8%,transparent)]"
          : "border-glass-border",
        disabled && "opacity-60",
      )}
    >
      <Upload aria-hidden size={19} strokeWidth={1.5} className="text-text-3" />
      <div className="flex flex-col gap-2">
        <label htmlFor={inputId} className="type-h3 m-0 text-ice">
          Add clinical source
        </label>
        <p className="type-body m-0 max-w-[44ch] text-text-2">
          Drop a PDF here, or choose a file. Scanned pages fall back to OCR during
          ingestion.
        </p>
      </div>
      <input
        id={inputId}
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf,.txt,.md"
        multiple
        className="sr-only"
        disabled={disabled}
        onChange={(event) => {
          accept(event.target.files);
          event.target.value = "";
        }}
      />
      <Button
        variant="inverse"
        size="sm"
        loading={busy}
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
      >
        Choose file
      </Button>
      {disabled && disabledReason && (
        <p className="type-body-s m-0 text-amber">{disabledReason}</p>
      )}
    </div>
  );
}
