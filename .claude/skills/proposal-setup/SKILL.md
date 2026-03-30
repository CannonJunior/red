---
name: proposal-setup
description: "Proposal kickoff and infrastructure setup toolkit. When Claude needs to: (1) Create the standard local proposal folder structure under outputs/proposal/, (2) Generate a proposal schedule and color team review timeline, (3) Set up the Confluence knowledge space for a new proposal, (4) Create the kickoff meeting agenda, (5) Assign the proposal team and volumes, (6) Generate a proposal compliance checklist from the shredding analysis. Use AFTER a bid decision is made to stand up all proposal infrastructure before kickoff."
---

# Proposal Setup

## Overview

This skill **kicks off an active proposal** by creating all infrastructure needed for the team to begin work immediately: local folders, proposal schedule, Confluence space, kickoff agenda, and compliance checklist.

**Key Capabilities**:
- Create local proposal folder structure (`outputs/proposal/{solicitation}/`)
- Generate proposal schedule with milestones (based on due date working backwards)
- Create Confluence proposal space with standard page structure
- Generate kickoff meeting agenda
- Create compliance matrix from shredding analysis output
- Assign team members and volume leads
- Advance proposal to `active` pipeline stage

## Workflow Position

```
[bid-no-bid → BID decision] → proposal-setup → [document-drafter]
                                              → [meeting-coordinator (kickoff)]
```

## Quick Start

### Full Proposal Setup

```
User: "Set up the proposal for FA8612-26-R-0001, due April 15, capture manager Jane Smith"

Claude runs proposal-setup to:
1. Load the proposal from database (must already exist from opportunity-curator)
2. Validate bid decision = "bid"
3. Create local folder structure
4. Generate proposal schedule working backwards from April 15
5. Create Confluence space (if configured)
6. Generate kickoff agenda
7. Create compliance matrix from shredding output (if available)
8. Update proposal record: advance to 'active', set proposal_manager
9. Return setup summary with all paths and links
```

### Local Folder Structure Created

```
outputs/proposal/
└── FA8612-26-R-0001/
    ├── 00_rfp/                     ← Place original solicitation here
    ├── 01_analysis/
    │   └── shredding/              ← Shredding outputs (auto-linked)
    ├── 02_bid_no_bid/              ← B/NB slide and worksheet
    ├── 03_working/
    │   ├── vol_1_technical/        ← Technical volume drafts
    │   ├── vol_2_management/       ← Management volume drafts
    │   ├── vol_3_cost/             ← Cost volume drafts
    │   └── vol_4_past_performance/ ← PP narratives
    ├── 04_reviews/
    │   ├── pink_team/
    │   ├── red_team/
    │   └── gold_team/
    ├── 05_final/
    │   ├── internal/
    │   └── submission/
    └── _admin/
        ├── proposal_schedule.xlsx  ← Auto-generated
        ├── kickoff_agenda.docx     ← Auto-generated
        ├── compliance_matrix.xlsx  ← From shredding (if available)
        └── team_assignments.docx   ← Auto-generated
```

### Generated Proposal Schedule

Working backwards from proposal due date, auto-generating:

| Milestone | Days Before Due | Notes |
|-----------|----------------|-------|
| Kickoff Meeting | -45 | Launch proposal effort |
| Storyboard Complete | -35 | Outlines approved |
| Pink Team Draft | -28 | First full draft |
| Pink Team Review | -25 | Review session |
| Red Team Draft | -18 | Revised draft |
| Red Team Review | -15 | Review session |
| Gold Team Draft | -7 | Final content |
| Gold Team Review | -5 | Executive review |
| Production Complete | -2 | Print/assemble |
| Proposal Due | 0 | Submit by 4:00 PM local |

## Output Documents

### Kickoff Agenda (auto-generated .docx)
```
Proposal Kickoff Meeting — {title}
Date: {kickoff_date} | Duration: 2 hours

1. Opportunity Overview (15 min)
   - Solicitation summary, customer background
   - Competitive landscape and win strategy

2. Proposal Structure (20 min)
   - Volume structure and page limits
   - Compliance matrix review (from shredding)

3. Schedule & Milestones (15 min)
   - Color team dates, proposal due date
   - Key dependencies and risks

4. Team Assignments (20 min)
   - Volume lead introductions
   - Subcontractor contributions
   - Key personnel identified

5. Tools & Process (15 min)
   - SharePoint folder walkthrough
   - Confluence space introduction
   - Style guide and templates

6. Open Questions & Action Items (15 min)
```

### Compliance Matrix (from shredding output)
- Pre-populated with all extracted requirements
- Volume assignment column
- Status column (compliant/partial/non-compliant/TBD)
- Page/section reference column
- Reviewer column

## Confluence Space Created

Automatically creates (if CONFLUENCE_* env vars configured):
- Space key: `PROPFA8612` (derived from solicitation number)
- All standard pages with kickoff content pre-filled
- Meeting Notes parent page
- Proposal Schedule page with milestone table

## Configuration

```bash
# In .env — these drive the schedule generation
COMPANY_NAME=Your Company LLC
PROPOSAL_TEAM_EMAIL=proposals@yourcompany.com
```

## Notes for Improvement

- Adjust schedule offsets based on historical color team performance
- Add agency-specific checklist items (FAR/DFARS clauses)
- Include past performance mapping from similar past proposals
