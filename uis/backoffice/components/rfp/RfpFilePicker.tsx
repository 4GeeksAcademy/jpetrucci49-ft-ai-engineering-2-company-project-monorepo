"use client";

import { useRef, useState } from "react";

interface RfpFilePickerProps {
  disabled?: boolean;
  onFileSelected: (file: File) => void;
}

function isPdfFile(file: File): boolean {
  const name = (file.name || "").toLowerCase();
  const type = (file.type || "").toLowerCase();
  return name.endsWith(".pdf") || type === "application/pdf" || type === "application/x-pdf";
}

export function RfpFilePicker({ disabled = false, onFileSelected }: RfpFilePickerProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);

  function takeFile(file: File | undefined) {
    if (!file || disabled) {
      return;
    }
    if (!isPdfFile(file)) {
      return;
    }
    setFileName(file.name);
    onFileSelected(file);
  }

  return (
    <div
      className={`rounded-xl border-2 border-dashed p-8 text-center transition-colors ${
        isDragging
          ? "border-teal-500 bg-teal-50"
          : "border-slate-300 bg-white hover:border-slate-400"
      } ${disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer"}`}
      onDragOver={(event) => {
        event.preventDefault();
        if (!disabled) {
          setIsDragging(true);
        }
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setIsDragging(false);
        takeFile(event.dataTransfer.files[0]);
      }}
      onClick={() => {
        if (!disabled) {
          inputRef.current?.click();
        }
      }}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          if (!disabled) {
            inputRef.current?.click();
          }
        }
      }}
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-label="Choose an RFP PDF"
    >
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        className="sr-only"
        disabled={disabled}
        onChange={(event) => {
          takeFile(event.target.files?.[0]);
        }}
      />
      <p className="text-lg font-medium text-slate-900">Drop your RFP PDF here</p>
      <p className="mt-2 text-sm text-slate-600">or click to browse</p>
      {fileName ? <p className="mt-4 text-sm font-medium text-slate-800">Selected: {fileName}</p> : null}
    </div>
  );
}
