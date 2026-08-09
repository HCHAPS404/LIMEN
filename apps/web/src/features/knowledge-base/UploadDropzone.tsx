import { Upload } from "lucide-react";
import { useId, useRef, useState, type DragEvent } from "react";
import { useTranslation } from "react-i18next";

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
  const { t } = useTranslation("knowledge");
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
        "flex flex-col gap-4 rounded-md px-1 py-1",
        "transition-colors duration-[var(--motion-fast)] ease-[var(--motion-ease)]",
        dragging &&
          "bg-[color-mix(in_oklab,var(--limen-cyan)_7%,transparent)]",
        disabled && "opacity-60",
      )}
    >
      <div className="flex items-start gap-3">
        <Upload
          aria-hidden
          size={18}
          strokeWidth={1.5}
          className={cn(
            "mt-0.5 shrink-0",
            dragging ? "text-cyan" : "text-text-3",
          )}
        />
        <div className="flex min-w-0 flex-1 flex-col gap-1.5">
          <label htmlFor={inputId} className="type-h3 m-0 text-ice">
            {t("upload.title")}
          </label>
          <p className="type-body-s m-0 max-w-[48ch] text-text-2">
            {t("upload.body")}
          </p>
        </div>
        <Button
          variant="inverse"
          size="sm"
          loading={busy}
          disabled={disabled}
          onClick={() => inputRef.current?.click()}
          className="shrink-0"
        >
          {t("upload.choose")}
        </Button>
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
      {disabled && disabledReason && (
        <p className="type-body-s m-0 text-amber">{disabledReason}</p>
      )}
      <div
        aria-hidden
        className={cn(
          "h-px w-full",
          dragging
            ? "bg-[color-mix(in_oklab,var(--limen-cyan)_40%,transparent)]"
            : "bg-[color-mix(in_oklab,var(--glass-border)_55%,transparent)]",
        )}
      />
    </div>
  );
}
