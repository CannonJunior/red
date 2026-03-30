---
name: cost-estimator
description: "Government proposal cost/price volume toolkit. When Claude needs to: (1) Build a cost volume spreadsheet with labor categories, rates, and wrap rates, (2) Calculate fully-burdened labor costs with fringe, overhead, G&A, and fee, (3) Generate Section B price schedule for FFP or T&M contracts, (4) Consolidate subcontractor cost inputs, (5) Draft cost narrative explaining the pricing approach, (6) Import rates from Unanet or rate files. Uses claude-sonnet-4-6 with extended thinking for financial accuracy. Use DURING active proposal phase, in parallel with document-drafter."
---

# Cost Estimator

## Overview

This skill builds the **cost/price volume** for government proposals — the most technically rigorous section where errors can disqualify or lose a bid. It handles labor category rates, wrap rate calculations, and Section B price schedule generation.

**Key Capabilities**:
- Labor category (LCAT) rate table management
- Fully-burdened rate calculation (fringe → overhead → G&A → fee)
- Period-by-period labor spread by task/CLIN
- Subcontractor cost roll-up
- Section B price schedule generation (.xlsx)
- Cost narrative draft (.docx)
- Historical rate file import/export
- Unanet labor rate import support

**Model**: `claude-sonnet-4-6` with extended thinking (financial accuracy critical)

## Workflow Position

```
[proposal-setup] → cost-estimator → [document-drafter (cost narrative)]
                                  → [crm-sync (update value estimate)]
```

## Quick Start

### Build Cost Volume

```
User: "Build the cost volume for FA8612-26-R-0001, 24-month base + 2 OY, starting Oct 2026"

Claude runs cost-estimator to:
1. Load proposal (contract type, period of performance, scope)
2. Load company rate structure from rates.json (or prompt for input)
3. Map SOW tasks to CLINs from shredding analysis
4. Build labor mix by CLIN and period
5. Calculate fully-burdened costs
6. Generate Section B price schedule (.xlsx)
7. Draft cost narrative (.docx)
8. Save to outputs/proposal/FA8612-26-R-0001/03_working/vol_3_cost/
```

### Rate Structure Configuration

Rates are stored in `data/rates/current_rates.json` (never hardcoded):

```json
{
  "effective_date": "2026-01-01",
  "company_name": "Your Company LLC",
  "wrap_rates": {
    "fringe_rate": 0.32,
    "overhead_rate": 0.45,
    "ga_rate": 0.12,
    "fee_rate": 0.08
  },
  "labor_categories": [
    {
      "lcat": "Program Manager",
      "grade": "Senior",
      "base_salary": 145000,
      "hours_per_year": 2080,
      "description": "15+ years experience, PMP required"
    },
    {
      "lcat": "Senior Engineer",
      "grade": "Senior",
      "base_salary": 135000,
      "hours_per_year": 2080,
      "description": "10+ years engineering, clearance required"
    }
  ]
}
```

### Rate Calculation Example

```
Base Salary:        $145,000 / 2,080 hrs = $69.71/hr
+ Fringe (32%):     + $22.31
= Fringe'd Rate:    $92.02/hr
+ Overhead (45%):   + $41.41
= OH Rate:          $133.43/hr
+ G&A (12%):        + $16.01
= Burdened Rate:    $149.44/hr
+ Fee (8%):         + $11.96
= Billable Rate:    $161.40/hr
```

## Section B Price Schedule (Excel Output)

```
FA8612-26-R-0001_section_b_price_schedule_2026-04-01.xlsx

Sheet 1: Summary
  CLIN | Description | Period | Quantity | Unit | Unit Price | Total
  0001 | Base Period  | 24 mo  |        1 |  LOT |            | $X,XXX,XXX

Sheet 2: Cost Detail
  Task | Labor Category | Hours (Base) | Hours (OY1) | Rate | Cost
  1.1  | Program Manager|          480 |         480 | $XXX | $XXX,XXX

Sheet 3: Subcontractor Roll-up
  Sub Name | Period | Labor | ODC | Subtotal | G&A | Total to Prime

Sheet 4: Rate Crosswalk
  LCAT | Base Rate | Burdened Rate | Billing Rate | Source
```

## Cost Narrative Template

```
This proposal presents a [FFP/T&M] cost proposal for [title].
The period of performance consists of a 24-month base period
commencing [start date] and two 12-month option years.

SECTION 1: BASIS OF ESTIMATE
All labor costs are based on [Company]'s [Year] Approved
Forward Pricing Rate Agreement (FPRA/FPRP). Wrap rates are:
- Fringe: XX%  - Overhead: XX%  - G&A: XX%  - Fee: XX%

SECTION 2: LABOR MIX
[Labor category table with hour distributions]

SECTION 3: SUBCONTRACTOR COSTS
[Subcontractor cost narrative]

SECTION 4: OTHER DIRECT COSTS
[Travel, materials, equipment if applicable]
```

## Unanet Rate Import

If the company uses Unanet for timekeeping, import approved billing rates:
```
User: "Import current rates from Unanet for the cost volume"

Claude pulls labor category rates from Unanet API:
GET {UNANET_BASE_URL}/rest/laborCategory?effective_date=2026-01-01
```

## Notes for Improvement

- After award, compare proposed rates to actual rates (if available)
- Track which LCATs are most often substituted during negotiations
- Update wrap rate calculations when forward pricing agreements change
- Build in escalation factors for multi-year contracts
