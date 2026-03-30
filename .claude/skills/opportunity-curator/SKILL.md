---
name: opportunity-curator
description: "GovCon opportunity curation and scoring toolkit. When Claude needs to: (1) Score and filter government contracting opportunities against company capabilities, (2) Ingest opportunities from SAM.gov, eBuy, or manual entry into the proposals database, (3) Assess NAICS alignment, past performance relevance, and competitive positioning, (4) Recommend pursue/pass/monitor decisions with rationale, (5) Trigger RFP shredding for qualified opportunities. Use BEFORE the bid-no-bid skill — this identifies which opportunities are worth a full bid/no-bid analysis."
---

# Opportunity Curator

## Overview

This skill curates and scores government contracting opportunities to identify the most promising pursuits before committing proposal resources. It operates as the **first gate** in the proposal pipeline.

**Key Capabilities**:
- Score opportunities against company NAICS codes and capability keywords
- Assess competitive landscape (set-aside type, incumbent status, # of bidders)
- Ingest opportunities from SAM.gov, manual entry, or structured data
- Recommend pursue/pass/monitor with scored rationale
- Advance qualified opportunities to the `qualifying` pipeline stage
- Trigger shredding skill for RFP analysis on pursuits

## Workflow Position

```
[Opportunity Sources] → opportunity-curator → qualifying → [bid-no-bid]
```

## Quick Start

### Score a New Opportunity

Provide opportunity details and get a pursue/pass recommendation:

```
User: "We received an RFP — FA8612-26-R-0001, AFRL, AI/ML Research, $5M FFP, SDVOSB set-aside, due April 15. Should we pursue?"

Claude runs opportunity-curator to:
1. Load company capability profile from .env (COMPANY_NAICS_CODES)
2. Score NAICS 541715 alignment
3. Check SDVOSB eligibility
4. Assess past performance match
5. Output scored recommendation with rationale
```

### Ingest from SAM.gov

```
User: "Pull today's SAM.gov opportunities matching our NAICS codes"

Claude runs opportunity-curator to:
1. Query SAM.gov API with company NAICS codes
2. Filter by set-aside types, agency, and value thresholds
3. Score each opportunity
4. Return ranked list with pursue/pass/monitor recommendations
```

## Scoring Model

### NAICS Alignment (30 points)
- Primary NAICS match: 30 pts
- Secondary NAICS match: 20 pts
- Adjacent NAICS match: 10 pts
- No match: 0 pts

### Competitive Position (25 points)
- SDVOSB set-aside + company is SDVOSB: 25 pts
- 8(a) set-aside + company is 8(a): 25 pts
- Small business set-aside: 15 pts
- Full and open (large business competition): 5 pts

### Past Performance (25 points)
- Direct agency past performance: 25 pts
- Adjacent agency or similar work: 15 pts
- Related domain experience: 10 pts
- No relevant past performance: 0 pts

### Strategic Factors (20 points)
- Customer relationship / prior interaction: 10 pts
- Incumbent advantage: -10 pts (if we are NOT the incumbent)
- Incumbent advantage: +10 pts (if we ARE the incumbent)
- Partnership opportunity with incumbent: +5 pts

### Recommendation Thresholds
- **Pursue** (≥70): Full bid/no-bid analysis warranted
- **Monitor** (50-69): Watch for re-release or amendment
- **Pass** (<50): Document rationale and file

## Implementation

This skill invokes `proposal/opportunity_scorer.py` (to be built in P1-1):

```python
# proposal/opportunity_scorer.py
from proposal.models import Proposal, PipelineStage
from proposal.database import create_proposal, run_migration
import uuid, os
from datetime import datetime

def score_opportunity(data: dict) -> dict:
    """Score an opportunity and return recommendation."""
    # ... scoring logic
```

## Output Format

```json
{
  "solicitation_number": "FA8612-26-R-0001",
  "title": "AI/ML Research Support",
  "agency": "AFRL",
  "score": 78,
  "recommendation": "PURSUE",
  "breakdown": {
    "naics_alignment": 30,
    "competitive_position": 25,
    "past_performance": 15,
    "strategic": 8
  },
  "rationale": "Strong NAICS match (541715), SDVOSB set-aside eligible, similar AFRL work on FA8612-23-P-0042. Recommend bid/no-bid review.",
  "next_action": "Run /bid-no-bid to complete full assessment",
  "proposal_id": "uuid-created-in-db"
}
```

## Integration with Shredding

After a pursue decision, automatically trigger shredding:
1. Create proposal record in `opportunities.db`
2. Advance to `qualifying` stage
3. Invoke `shredding` skill on attached RFP documents
4. Store shred_analysis_id in proposal record

## Configuration

All configuration via `.env`:
```
COMPANY_NAICS_CODES=541715,541330,541990
COMPANY_NAME=Your Company LLC
COMPANY_CAGE_CODE=XXXXX
BID_THRESHOLD=70
```

## Notes for Improvement

After each proposal cycle, update the scoring model based on win/loss patterns.
The hotwash skill feeds lessons learned back to refine weights here.
