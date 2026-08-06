export type SupplierCountry = "USA" | "UK";
export type SupplierCurrency = "USD" | "GBP";
export type SupplierStatus = "active" | "suspended";
export type ComplianceAgreement = "BAA" | "DPA" | "both";

export interface Supplier {
  id: number;
  name: string;
  country: SupplierCountry;
  categories: string[];
  monthly_rate: number;
  currency: SupplierCurrency;
  status: SupplierStatus;
  compliance_agreement: ComplianceAgreement | null;
  contract_renewal_date: string | null;
  contact_email: string | null;
  notes: string | null;
  updated_at: string;
}

export interface SupplierCreatePayload {
  name: string;
  country: SupplierCountry;
  categories: string[];
  monthly_rate: number;
  currency: SupplierCurrency;
  status: SupplierStatus;
  compliance_agreement?: ComplianceAgreement | null;
  contract_renewal_date?: string | null;
  contact_email?: string | null;
  notes?: string | null;
}

export interface SupplierRateUpdatePayload {
  monthly_rate: number;
}

export interface SupplierStatusUpdatePayload {
  status: SupplierStatus;
}

export interface SupplierListFilters {
  country?: SupplierCountry;
  category?: string;
}

export class SuppliersApiError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message);
    this.name = "SuppliersApiError";
  }
}

export const SUPPLIER_CATEGORIES = [
  "medical_supplies",
  "laboratory_services",
  "pharmaceutical",
  "clinical_software",
  "it_infrastructure",
  "hr_and_payroll_software",
  "cleaning_and_facilities",
  "patient_communication",
  "billing_and_coding_software",
  "training_platforms",
] as const;

export type SupplierCategory = (typeof SUPPLIER_CATEGORIES)[number];

export const SUPPLIER_CATEGORY_LABELS: Record<SupplierCategory, string> = {
  medical_supplies: "Medical supplies",
  laboratory_services: "Laboratory services",
  pharmaceutical: "Pharmaceutical",
  clinical_software: "Clinical software",
  it_infrastructure: "IT infrastructure",
  hr_and_payroll_software: "HR and payroll software",
  cleaning_and_facilities: "Cleaning and facilities",
  patient_communication: "Patient communication",
  billing_and_coding_software: "Billing and coding software",
  training_platforms: "Training platforms",
};

export const COUNTRY_CURRENCY: Record<SupplierCountry, SupplierCurrency> = {
  USA: "USD",
  UK: "GBP",
};
