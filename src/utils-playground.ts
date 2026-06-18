import type { Appointment, Claim, Clinician, Location } from "./entities";
import {
  collections,
  search,
  transformations,
  validations,
} from "./utils";
import { locations, claims, appointments, clinicians } from "../tests/utils/fixtures";

console.log("Filtered claims (BlueCross):", collections.filterClaims(claims, { payerName: "BlueCross" }));
console.log("Find claim CLM-000002:", search.findClaimById(claims, "CLM-000002"));
console.log("Overall denial rate:", transformations.calculateDenialRate(claims), "%");
console.log("No-show cost for week ending 2025-03-11:", transformations.calculateNoShowCost(appointments, locations[0], "2025-03-11"));
console.log("CME report:", transformations.generateCMEReport(clinicians, "2025-06-30"));
console.log("Claim validation:", validations.validateClaim(claims[1], ["us-tx-001", "us-fl-001"]));