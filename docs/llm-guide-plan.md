# LLM Guide Implementation Plan

---

# 1. Current Scope

Current MVP implementation scope:

- OCR medication parsing
- OCR → schedule_table mapping
- usage_time generation
- medication guide generation
- lifestyle guide generation
- NOT_FOUND fallback handling
- OCR confidence handling

---

# 2. Current API Flow

```text
POST /api/v1/guides/generate
→ polling
→ result retrieval
```

## Current Flow Description

1. OCR result or medication information is received
2. guide generation request is created
3. async guide generation job starts
4. frontend polls generation status
5. generated guide result is retrieved

---

# 3. MVP Principles

* Preserve OCR original meaning as much as possible
* Avoid excessive automated medical judgment
* Do not generate exact medication administration times
* Use 식약처 CSV itemName matching as primary source
* Keep usage_time as free-text information
* Restrict lifestyle guide generation to predefined whitelist diseases only
* Do not automatically determine a representative disease
* Distinguish public-data-based information from general LLM-generated information

---

# 4. Current Guide Input Fields

## Current Planned Input Fields

* medication_name
* generic_name (optional)
* dosage
* frequency
* timing
* usage_time
* warnings
* disease_codes
* confidence_score
* confidence_level

---

# 5. Current OCR Mapping Direction

## Core Mapping Principles

* Preserve OCR frequency/timing original text
* Generate usage_time as user-facing free text
* Use time_of_day only for lightweight UI schedule slot rendering
* Do not generate exact HH:MM administration times

---

## Limited UI Schedule Slot Normalization

Limited UI-level normalization is allowed for simple frequency patterns:

| OCR frequency | Allowed UI slot  |
| ------------- | ---------------- |
| 1일 3회         | ["아침","점심","저녁"] |
| 1일 2회         | ["아침","저녁"]      |
| 1일 1회 + 아침 식후 | ["아침"]           |

This normalization is intended only for frontend schedule UI rendering and does not represent exact medical administration times.

If a frequency pattern is not explicitly defined in the normalization table,
time_of_day should not be generated automatically.
---

# 6. Current Fallback Policy

1. 식약처 CSV itemName matching first
2. generic_name may be used as optional supplementary information
3. General LLM explanation allowed only when CSV NOT_FOUND
4. Non-public-data disclaimer must be displayed for LLM fallback responses

---

# 7. Current Safety Policy

The system must NOT:

* Generate exact medication administration times (HH:MM)
* Generate OCR information that does not exist
* Confirm diseases
* Recommend medication changes
* Modify treatment plans
* Arbitrarily normalize ambiguous OCR instructions
* Automatically determine representative diseases

---

# 8. Current Disease Guide Policy

## Disease Source Priority

1. Prescription disease codes
2. Pharmacy bag disease symbols
3. User-input disease information

---

## Current Whitelist Candidate Diseases

* Hypertension
* Diabetes
* Hyperlipidemia
* Gastritis
* GERD
* Constipation
* Osteoarthritis
* Allergic rhinitis

---

## Multi-Disease Handling

* Multiple disease codes are allowed
* Representative disease auto-selection is prohibited
* Lifestyle guides may be generated separately for whitelist diseases
* Frontend may limit displayed sections for MVP simplicity

---

# 9. Current Frontend Display Policy

* usage_time should be displayed as the primary medication instruction text
* schedule cards should use lightweight normalized time_of_day slots only
* free-text usage_time should be displayed when slot normalization is unavailable
* low OCR confidence requires user confirmation UI

---

# 10. Current DTO / Integration TODO

## Implementation Note

Current guide API is still based on `medication_names: list[str]`.

The OCR-integrated request schema described in this document is a target structure for the next implementation phase.

DTO changes for:
- `GenerateGuideRequest`
- `MedicationItem`
- `ScheduleEntry`

are required before full OCR integration.

---

## Planned Future Updates

* Expand GenerateGuideRequest schema to support OCR medication structures
* Add OCR confidence-related fields to API DTOs
* Connect disease_codes to actual OCR/patient input sources
* Replace temporary hardcoded disease context logic
* Align schedule_table DTO structure with mapping policy