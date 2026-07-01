"use client";

import { useState } from "react";
import { hasFieldErrors, validateRecordForm, type RecordFormValues } from "@/lib/validation";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Field, TextInput } from "@/components/ui/Field";

const emptyValues: RecordFormValues = {
  full_name: "",
  email: "",
  phone: "",
  position: "Executive Assistant",
  experience_years: 0,
  linkedin_url: "",
  cv_url: "",
};

interface CandidateFormProps {
  initialValues?: Partial<RecordFormValues>;
  submitLabel: string;
  onSubmit: (values: RecordFormValues) => Promise<boolean>;
  onCancel?: () => void;
}

export function CandidateForm({
  initialValues,
  submitLabel,
  onSubmit,
  onCancel,
}: CandidateFormProps) {
  const [values, setValues] = useState<RecordFormValues>({ ...emptyValues, ...initialValues });
  const [errors, setErrors] = useState<ReturnType<typeof validateRecordForm>>({});
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const updateField = <K extends keyof RecordFormValues>(key: K, value: RecordFormValues[K]) => {
    setValues((current) => ({ ...current, [key]: value }));
    setErrors((current) => ({ ...current, [key]: undefined }));
    setFeedback(null);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const nextErrors = validateRecordForm(values);
    setErrors(nextErrors);
    if (hasFieldErrors(nextErrors)) return;

    setIsSubmitting(true);
    setFeedback(null);
    const success = await onSubmit({
      ...values,
      full_name: values.full_name.trim(),
      email: values.email.trim(),
      phone: values.phone.trim(),
      position: values.position.trim(),
      linkedin_url: values.linkedin_url?.trim() || null,
      cv_url: values.cv_url?.trim() || null,
    });
    setIsSubmitting(false);

    if (success) {
      setFeedback({ type: "success", message: "Changes saved successfully." });
      if (!initialValues) setValues(emptyValues);
    } else {
      setFeedback({ type: "error", message: "Could not save candidate. Please try again." });
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {feedback ? <Alert variant={feedback.type}>{feedback.message}</Alert> : null}

      <div className="grid gap-4 md:grid-cols-2">
        <Field label="Full name" htmlFor="full_name" required error={errors.full_name}>
          <TextInput
            id="full_name"
            value={values.full_name}
            onChange={(event) => updateField("full_name", event.target.value)}
          />
        </Field>

        <Field label="Email" htmlFor="email" required error={errors.email}>
          <TextInput
            id="email"
            type="email"
            value={values.email}
            onChange={(event) => updateField("email", event.target.value)}
          />
        </Field>

        <Field label="Phone" htmlFor="phone" required error={errors.phone}>
          <TextInput
            id="phone"
            type="tel"
            value={values.phone}
            onChange={(event) => updateField("phone", event.target.value)}
          />
        </Field>

        <Field label="Position" htmlFor="position" required error={errors.position}>
          <TextInput
            id="position"
            value={values.position}
            onChange={(event) => updateField("position", event.target.value)}
          />
        </Field>

        <Field label="Years of experience" htmlFor="experience_years" required error={errors.experience_years}>
          <TextInput
            id="experience_years"
            type="number"
            min={0}
            step={1}
            value={values.experience_years}
            onChange={(event) => updateField("experience_years", Number(event.target.value))}
          />
        </Field>

        <Field label="LinkedIn URL" htmlFor="linkedin_url" error={errors.linkedin_url}>
          <TextInput
            id="linkedin_url"
            type="url"
            value={values.linkedin_url ?? ""}
            onChange={(event) => updateField("linkedin_url", event.target.value)}
          />
        </Field>

        <Field label="CV URL" htmlFor="cv_url" error={errors.cv_url} >
          <TextInput
            id="cv_url"
            type="url"
            value={values.cv_url ?? ""}
            onChange={(event) => updateField("cv_url", event.target.value)}
          />
        </Field>
      </div>

      <div className="flex flex-wrap gap-3">
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Saving..." : submitLabel}
        </Button>
        {onCancel ? (
          <Button type="button" variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
        ) : null}
      </div>
    </form>
  );
}
