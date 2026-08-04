"use client";

import { useRef, useState } from "react";

interface IncidentFileUploadProps {
  onFileSelected: (file: File) => void;
  disabled?: boolean;
}

export function IncidentFileUpload({ onFileSelected, disabled = false }: IncidentFileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  function handleFile(file: File | undefined) {
    if (!file || disabled) return;
    if (!file.name.toLowerCase().endsWith(".csv")) return;
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
        if (!disabled) setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setIsDragging(false);
        handleFile(event.dataTransfer.files[0]);
      }}
      onClick={() => !disabled && inputRef.current?.click()}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          if (!disabled) inputRef.current?.click();
        }
      }}
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-label="Upload incident CSV file"
    >
      <input
        ref={inputRef}
        type="file"
        accept=".csv,text/csv"
        className="sr-only"
        disabled={disabled}
        onChange={(event) => handleFile(event.target.files?.[0])}
      />
      <p className="text-lg font-medium text-slate-900">Drop your incident CSV here</p>
      <p className="mt-2 text-sm text-slate-600">or click to browse — UTF-8 comma-separated file</p>
      <p className="mt-4 text-xs text-slate-500">
        Patient Experience export format · Required columns include clinic_id, category, status, and
        patient_id
      </p>
    </div>
  );
}
