/** constants.js: fixed lists used by filters and forms (geography and UI choices, not policy data). */

// Must match BUILD in backend/config.py. If they differ, the app tells you to restart the backend.
export const BUILD = "2026-10-31-e";

export const INDIAN_STATES = [
  "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat",
  "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh",
  "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
  "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh",
  "Uttarakhand", "West Bengal",
  "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
  "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
];

// value = what we send to the backend, label = what the user sees
export const BENEFICIARIES = [
  { value: "", label: "All citizens" },
  { value: "students", label: "Students" },
  { value: "farmers", label: "Farmers" },
  { value: "parents", label: "Parents" },
  { value: "seniors", label: "Senior citizens" },
  { value: "other", label: "Other beneficiaries" },
];

export const DATE_OPTIONS = [
  { value: "", label: "Any publication date" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
  { value: "90d", label: "Last 3 months" },
  { value: "365d", label: "Last year" },
];

export const OFFICIAL_SITES = [
  { label: "India Code", url: "https://www.indiacode.nic.in" },
  { label: "e-Gazette", url: "https://egazette.gov.in" },
  { label: "mySchemes", url: "https://www.myscheme.gov.in" },
  { label: "PIB", url: "https://pib.gov.in" },
];
