"use client";

import { useRef, useState } from "react";
import { statusOptions, stageOptions } from "@/lib/labels";
import { Field, SelectInput, TextInput } from "@/components/ui/Field";

export interface CandidateFilterValues {
  status: string;
  stage: string;
  search: string;
}

interface CandidateFiltersProps {
  values: CandidateFilterValues;
  onChange: (next: Partial<CandidateFilterValues>) => void;
}

export function CandidateFilters({ values, onChange }: CandidateFiltersProps) {
  const [searchDraft, setSearchDraft] = useState(values.search);
  const searchTimerRef = useRef<number | undefined>(undefined);

  const handleSearchChange = (value: string) => {
    setSearchDraft(value);
    window.clearTimeout(searchTimerRef.current);
    searchTimerRef.current = window.setTimeout(() => onChange({ search: value }), 300);
  };

  return (
    <section className="grid gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm md:grid-cols-3">
      <Field label="Search" htmlFor="search">
        <TextInput
          id="search"
          type="search"
          placeholder="Name or email"
          value={searchDraft}
          onChange={(event) => handleSearchChange(event.target.value)}
        />
      </Field>

      <Field label="Status" htmlFor="status-filter">
        <SelectInput
          id="status-filter"
          value={values.status}
          onChange={(event) => onChange({ status: event.target.value })}
        >
          <option value="">All statuses</option>
          {statusOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </SelectInput>
      </Field>

      <Field label="Stage" htmlFor="stage-filter">
        <SelectInput
          id="stage-filter"
          value={values.stage}
          onChange={(event) => onChange({ stage: event.target.value })}
        >
          <option value="">All stages</option>
          {stageOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </SelectInput>
      </Field>
    </section>
  );
}
