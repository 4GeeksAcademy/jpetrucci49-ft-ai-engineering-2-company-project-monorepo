const form = document.getElementById("patient-form");

if (form) {
  function getCurrentLang() {
    return document.documentElement.getAttribute("data-current-lang") === "es" ? "es" : "en";
  }

  const messages = {
    en: {
      first_name: "First name must contain only letters and be at least 2 characters",
      last_name: "Last name must contain only letters and be at least 2 characters",
      date_of_birth: "Enter a valid date of birth. Patient must be between 0 and 120 years old",
      email: "Enter a valid email address (example: name@provider.com)",
      phone: "Phone must include a country code (example: +1 305 555 0191)",
      preferred_language: "Select your preferred language",
      preferred_clinic: "Select the clinic you would like to visit",
      preferred_date: "Select a date at least 1 business day from today and no more than 60 days ahead",
      preferred_time: "Select your preferred time of day",
      service_type: "Select the type of care you are looking for",
      paediatric: "Paediatric Care is available for patients under 18. Please check the date of birth or select a different service.",
      new_patient: "Please indicate whether this is your first visit to HealthCore",
      has_insurance: "Please indicate whether you have health insurance",
      insurance_provider: "Please enter your insurance provider name",
      insurance_member_id: "Member ID must be between 6 and 20 alphanumeric characters",
      health_concern: "Please describe your health concern in at least 20 characters (%X% characters remaining)",
      contact_consent: "You must consent to being contacted before submitting this form",
      patient_id: "Patient ID must match format HC-XXXXXX (letters and numbers)",
      timeClinicWarning:
        "Evening requests are valid for this clinic, but slots may be limited because it closes before 8pm."
    },
    es: {
      first_name: "El nombre debe contener solo letras y tener al menos 2 caracteres",
      last_name: "El apellido debe contener solo letras y tener al menos 2 caracteres",
      date_of_birth: "Ingresa una fecha de nacimiento valida. El paciente debe tener entre 0 y 120 anos",
      email: "Ingresa un correo valido (ejemplo: nombre@proveedor.com)",
      phone: "El telefono debe incluir codigo de pais (ejemplo: +34 612 345 678)",
      preferred_language: "Selecciona tu idioma preferido",
      preferred_clinic: "Selecciona la clinica que deseas visitar",
      preferred_date: "Selecciona una fecha con al menos 1 dia habil desde hoy y no mas de 60 dias",
      preferred_time: "Selecciona tu horario preferido",
      service_type: "Selecciona el tipo de atencion que buscas",
      paediatric:
        "La atencion pediatrica esta disponible para pacientes menores de 18 anos. Verifica la fecha de nacimiento o elige otro servicio.",
      new_patient: "Indica si es tu primera visita a HealthCore",
      has_insurance: "Indica si tienes seguro medico",
      insurance_provider: "Ingresa el nombre de tu proveedor de seguro",
      insurance_member_id: "El ID de miembro debe tener entre 6 y 20 caracteres alfanumericos",
      health_concern: "Describe tu motivo de consulta con al menos 20 caracteres (%X% caracteres restantes)",
      contact_consent: "Debes dar consentimiento para que podamos contactarte antes de enviar",
      patient_id: "El ID de paciente debe tener formato HC-XXXXXX (letras y numeros)",
      timeClinicWarning:
        "Las solicitudes en horario nocturno son validas para esta clinica, pero puede haber menos disponibilidad porque cierra antes de las 8pm."
    }
  };

  const clinicClosingHour = {
    "HealthCore Austin Central": 20,
    "HealthCore Austin North": 19,
    "HealthCore San Antonio": 18,
    "HealthCore Miami": 20,
    "HealthCore Orlando": 18,
    "HealthCore Atlanta": 19
  };

  const fields = {
    first_name: document.getElementById("first_name"),
    last_name: document.getElementById("last_name"),
    date_of_birth: document.getElementById("date_of_birth"),
    email: document.getElementById("email"),
    phone: document.getElementById("phone"),
    preferred_language: document.getElementById("preferred_language"),
    preferred_clinic: document.getElementById("preferred_clinic"),
    preferred_date: document.getElementById("preferred_date"),
    preferred_time: document.getElementById("preferred_time"),
    service_type: document.getElementById("service_type"),
    insurance_provider: document.getElementById("insurance_provider"),
    insurance_member_id: document.getElementById("insurance_member_id"),
    patient_id: document.getElementById("patient_id"),
    health_concern: document.getElementById("health_concern"),
    contact_consent: document.getElementById("contact_consent")
  };

  const newPatientRadios = document.querySelectorAll('input[name="new_patient"]');
  const hasInsuranceRadios = document.querySelectorAll('input[name="has_insurance"]');
  const insuranceFieldsWrapper = document.getElementById("insurance-fields");
  const patientIdWrapper = document.getElementById("patient-id-wrapper");
  const healthCounter = document.getElementById("health-counter");
  const warningTimeClinic = document.getElementById("warning-time-clinic");
  const successMessage = document.getElementById("success-message");
  const clearButton = document.getElementById("clear-form");

  const alphaRegex = /^[A-Za-zÀ-ÖØ-öø-ÿ]{2,50}$/u;
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const phoneRegex = /^\+\d{1,3}(?:[\s-]?\d){6,20}$/;
  const memberIdRegex = /^[A-Za-z0-9]{6,20}$/;
  const patientIdRegex = /^HC-[A-Za-z0-9]{6}$/;

  function text(key) {
    return messages[getCurrentLang()][key];
  }

  function getErrorElement(fieldName) {
    return document.getElementById(`error-${fieldName}`);
  }

  function setError(fieldName, message) {
    const errorElement = getErrorElement(fieldName);
    if (!errorElement) return;
    errorElement.textContent = message;
    errorElement.classList.remove("hidden");
  }

  function clearError(fieldName) {
    const errorElement = getErrorElement(fieldName);
    if (!errorElement) return;
    errorElement.textContent = "";
    errorElement.classList.add("hidden");
  }

  function getRadioValue(name) {
    const selected = document.querySelector(`input[name="${name}"]:checked`);
    return selected ? selected.value : "";
  }

  function startOfDay(date) {
    const value = new Date(date);
    value.setHours(0, 0, 0, 0);
    return value;
  }

  function calculateAge(dateString) {
    const dob = new Date(dateString);
    const today = new Date();
    let age = today.getFullYear() - dob.getFullYear();
    const monthDifference = today.getMonth() - dob.getMonth();
    if (monthDifference < 0 || (monthDifference === 0 && today.getDate() < dob.getDate())) {
      age -= 1;
    }
    return age;
  }

  function addBusinessDays(baseDate, businessDays) {
    const result = new Date(baseDate);
    let added = 0;
    while (added < businessDays) {
      result.setDate(result.getDate() + 1);
      const day = result.getDay();
      if (day !== 0 && day !== 6) {
        added += 1;
      }
    }
    return result;
  }

  function validateName(fieldName) {
    const value = fields[fieldName].value.trim();
    if (!alphaRegex.test(value)) {
      setError(fieldName, text(fieldName));
      return false;
    }
    clearError(fieldName);
    return true;
  }

  function validateDateOfBirth() {
    const value = fields.date_of_birth.value;
    const dob = new Date(value);
    const today = startOfDay(new Date());
    if (!value || Number.isNaN(dob.getTime())) {
      setError("date_of_birth", text("date_of_birth"));
      return false;
    }

    const normalizedDob = startOfDay(dob);
    const age = calculateAge(value);

    if (normalizedDob > today || age < 0 || age > 120) {
      setError("date_of_birth", text("date_of_birth"));
      return false;
    }

    clearError("date_of_birth");
    return true;
  }

  function validateEmail() {
    const value = fields.email.value.trim();
    if (!emailRegex.test(value)) {
      setError("email", text("email"));
      return false;
    }
    clearError("email");
    return true;
  }

  function validatePhone() {
    const value = fields.phone.value.trim();
    if (!phoneRegex.test(value)) {
      setError("phone", text("phone"));
      return false;
    }
    clearError("phone");
    return true;
  }

  function validateRequiredSelect(fieldName) {
    const value = fields[fieldName].value;
    if (!value) {
      setError(fieldName, text(fieldName));
      return false;
    }
    clearError(fieldName);
    return true;
  }

  function validatePreferredDate() {
    const value = fields.preferred_date.value;
    const selected = new Date(value);
    if (!value || Number.isNaN(selected.getTime())) {
      setError("preferred_date", text("preferred_date"));
      return false;
    }

    const today = startOfDay(new Date());
    const minDate = startOfDay(addBusinessDays(today, 1));
    const maxDate = startOfDay(new Date(today.getFullYear(), today.getMonth(), today.getDate() + 60));
    const normalizedSelected = startOfDay(selected);

    if (normalizedSelected < minDate || normalizedSelected > maxDate) {
      setError("preferred_date", text("preferred_date"));
      return false;
    }

    clearError("preferred_date");
    return true;
  }

  function validateServiceType() {
    const value = fields.service_type.value;
    if (!value) {
      setError("service_type", text("service_type"));
      return false;
    }

    const age = calculateAge(fields.date_of_birth.value);
    if (value === "Paediatric Care" && (!fields.date_of_birth.value || Number.isNaN(age) || age >= 18)) {
      setError("service_type", text("paediatric"));
      return false;
    }

    clearError("service_type");
    return true;
  }

  function updateTimeClinicWarning() {
    const time = fields.preferred_time.value;
    const clinic = fields.preferred_clinic.value;
    warningTimeClinic.classList.add("hidden");
    warningTimeClinic.textContent = "";

    if (time !== "Evening" || !clinic) {
      return;
    }

    const closingHour = clinicClosingHour[clinic];
    if (!closingHour || closingHour <= 17) {
      setError("preferred_time", text("preferred_time"));
      return;
    }

    if (closingHour < 20) {
      warningTimeClinic.textContent = text("timeClinicWarning");
      warningTimeClinic.classList.remove("hidden");
    }
  }

  function validateNewPatient() {
    const value = getRadioValue("new_patient");
    if (!value) {
      setError("new_patient", text("new_patient"));
      return false;
    }

    clearError("new_patient");

    if (value === "No") {
      patientIdWrapper.classList.remove("hidden");
    } else {
      patientIdWrapper.classList.add("hidden");
      fields.patient_id.value = "";
      clearError("patient_id");
    }

    return true;
  }

  function validatePatientId() {
    const isReturning = getRadioValue("new_patient") === "No";
    const value = fields.patient_id.value.trim();

    if (!isReturning || value.length === 0) {
      clearError("patient_id");
      return true;
    }

    if (!patientIdRegex.test(value)) {
      setError("patient_id", text("patient_id"));
      return false;
    }

    clearError("patient_id");
    return true;
  }

  function validateHasInsurance() {
    const value = getRadioValue("has_insurance");
    if (!value) {
      setError("has_insurance", text("has_insurance"));
      return false;
    }

    clearError("has_insurance");

    if (value === "Yes") {
      insuranceFieldsWrapper.classList.remove("hidden");
      fields.insurance_provider.required = true;
      fields.insurance_member_id.required = true;
    } else {
      insuranceFieldsWrapper.classList.add("hidden");
      fields.insurance_provider.required = false;
      fields.insurance_member_id.required = false;
      fields.insurance_provider.value = "";
      fields.insurance_member_id.value = "";
      clearError("insurance_provider");
      clearError("insurance_member_id");
    }

    return true;
  }

  function validateInsuranceFields() {
    if (getRadioValue("has_insurance") !== "Yes") {
      clearError("insurance_provider");
      clearError("insurance_member_id");
      return true;
    }

    let valid = true;
    const provider = fields.insurance_provider.value.trim();
    const memberId = fields.insurance_member_id.value.trim();

    if (!provider || provider.length > 100) {
      setError("insurance_provider", text("insurance_provider"));
      valid = false;
    } else {
      clearError("insurance_provider");
    }

    if (!memberIdRegex.test(memberId)) {
      setError("insurance_member_id", text("insurance_member_id"));
      valid = false;
    } else {
      clearError("insurance_member_id");
    }

    return valid;
  }

  function updateHealthCounter() {
    const value = fields.health_concern.value;
    healthCounter.textContent = `${value.length} / 500`;
  }

  function validateHealthConcern() {
    const value = fields.health_concern.value.trim();
    updateHealthCounter();

    if (value.length < 20 || value.length > 500) {
      const remaining = Math.max(0, 20 - value.length);
      const errorMessage = text("health_concern").replace("%X%", String(remaining));
      setError("health_concern", errorMessage);
      return false;
    }

    clearError("health_concern");
    return true;
  }

  function validateConsent() {
    if (!fields.contact_consent.checked) {
      setError("contact_consent", text("contact_consent"));
      return false;
    }
    clearError("contact_consent");
    return true;
  }

  function validateForm() {
    const checks = [
      validateName("first_name"),
      validateName("last_name"),
      validateDateOfBirth(),
      validateEmail(),
      validatePhone(),
      validateRequiredSelect("preferred_language"),
      validateRequiredSelect("preferred_clinic"),
      validatePreferredDate(),
      validateRequiredSelect("preferred_time"),
      validateServiceType(),
      validateNewPatient(),
      validatePatientId(),
      validateHasInsurance(),
      validateInsuranceFields(),
      validateHealthConcern(),
      validateConsent()
    ];

    updateTimeClinicWarning();
    return checks.every(Boolean);
  }

  fields.first_name.addEventListener("input", () => validateName("first_name"));
  fields.last_name.addEventListener("input", () => validateName("last_name"));
  fields.date_of_birth.addEventListener("change", () => {
    validateDateOfBirth();
    validateServiceType();
  });
  fields.email.addEventListener("input", validateEmail);
  fields.phone.addEventListener("input", validatePhone);
  fields.preferred_language.addEventListener("change", () => validateRequiredSelect("preferred_language"));
  fields.preferred_clinic.addEventListener("change", () => {
    validateRequiredSelect("preferred_clinic");
    updateTimeClinicWarning();
  });
  fields.preferred_date.addEventListener("change", validatePreferredDate);
  fields.preferred_time.addEventListener("change", () => {
    validateRequiredSelect("preferred_time");
    updateTimeClinicWarning();
  });
  fields.service_type.addEventListener("change", validateServiceType);

  newPatientRadios.forEach((radio) => {
    radio.addEventListener("change", () => {
      validateNewPatient();
      validatePatientId();
    });
  });

  hasInsuranceRadios.forEach((radio) => {
    radio.addEventListener("change", () => {
      validateHasInsurance();
      validateInsuranceFields();
    });
  });

  fields.insurance_provider.addEventListener("input", validateInsuranceFields);
  fields.insurance_member_id.addEventListener("input", validateInsuranceFields);
  fields.patient_id.addEventListener("input", validatePatientId);
  fields.health_concern.addEventListener("input", validateHealthConcern);
  fields.contact_consent.addEventListener("change", validateConsent);

  form.addEventListener("submit", (event) => {
    event.preventDefault();

    if (validateForm()) {
      successMessage.classList.remove("hidden");
      form.reset();
      updateHealthCounter();
      insuranceFieldsWrapper.classList.add("hidden");
      patientIdWrapper.classList.add("hidden");
      warningTimeClinic.classList.add("hidden");
    } else {
      successMessage.classList.add("hidden");
    }
  });

  clearButton.addEventListener("click", () => {
    form.reset();
    successMessage.classList.add("hidden");
    insuranceFieldsWrapper.classList.add("hidden");
    patientIdWrapper.classList.add("hidden");
    warningTimeClinic.classList.add("hidden");
    Object.keys(fields).forEach((key) => clearError(key));
    clearError("new_patient");
    clearError("has_insurance");
    updateHealthCounter();
  });

  updateHealthCounter();
}
