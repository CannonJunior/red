---
name: hotwash
description: "Post-proposal hotwash and lessons learned toolkit. When Claude needs to: (1) Facilitate a structured post-submission retrospective for a proposal team, (2) Capture what went well, what to improve, and lessons learned in a searchable database, (3) Generate a hotwash report document and Confluence page, (4) Extract process improvement action items, (5) Analyze patterns across multiple proposals (win rate by agency, common failures, team performance), (6) Feed lessons learned back to improve skill prompts and scoring models. Use AFTER proposal submission (win or loss) or after a no-bid decision."
---

# Hotwash — Post-Proposal Retrospective

## Overview

The hotwash is the **most important feedback loop** in the proposal process. Every completed proposal — win, loss, or no-bid — produces actionable lessons that improve future performance.

**Key Capabilities**:
- Structured facilitation of retrospective discussions
- Capture what went well / what to improve / lessons learned
- Process self-scoring (1-10 scale by category)
- Debrief request tracking (for agency feedback after award)
- Confluence knowledge base creation
- Pattern analysis across proposals (win/loss trends)
- Automatic skill prompt updates (improvement loop)
- Action items with owners and target dates

## Workflow Position

```
[submitted → awarded/lost] → hotwash → [lessons_learned_db]
[bid_decision → no_bid]    → hotwash     → [skill improvement]
```

## Quick Start

### Run a Hotwash

```
User: "Run the hotwash for FA8612-26-R-0001 — we lost"

Claude runs hotwash to:
1. Load proposal record (timeline, team, meetings)
2. Present structured retrospective framework
3. Collect responses to each category
4. Calculate process score (1-10)
5. Record in hotwash_events table
6. Generate hotwash report (.docx)
7. Create Confluence page in proposal space
8. Extract process improvement action items
9. Ask: "Should I analyze patterns from similar proposals?"
```

### Quick No-Bid Hotwash

```
User: "Quick hotwash for W81XWH-26-R-0025 — we passed on it, turned out we were right"

Claude runs hotwash to:
1. Load proposal record
2. Short-form retrospective (was the no-bid decision correct? why?)
3. Record in database
4. Update opportunity scoring weights if applicable
```

## Retrospective Framework

### Process Categories (scored 1-10)

**1. Opportunity Assessment**
- Did we accurately assess competitiveness? (score vs actual outcome)
- Was the B/NB decision process rigorous?
- Did we have adequate customer intel?

**2. Proposal Management**
- Was the schedule realistic and followed?
- Were color team reviews effective?
- Was action item tracking sufficient?

**3. Writing & Compliance**
- Were all Section L requirements addressed?
- Was the technical approach compelling?
- Did the proposal tell a coherent story?

**4. Cost Volume**
- Was our pricing competitive?
- Did we have accurate rate information?
- Was the cost narrative clear?

**5. Team Performance**
- Did team members deliver on time?
- Were subcontractors responsive?
- Was leadership engagement adequate?

### Standard Questions

**What went well?**
- [ ] Customer intel was strong
- [ ] Color team reviews were productive
- [ ] Subcontractor integration was smooth
- [ ] Schedule was realistic and followed
- [ ] Cost approach was competitive
- [ ] Writing quality was high
- [ ] Team collaboration was excellent
- (add custom items)

**What to improve?**
- [ ] Started too late — need earlier kickoff
- [ ] Key personnel not confirmed early enough
- [ ] Color team feedback not fully incorporated
- [ ] Cost was too high / low
- [ ] Past performance references were weak
- [ ] Section L compliance gaps
- [ ] Subcontractor coordination breakdown
- (add custom items)

**Lessons Learned** (free text — these feed the knowledge base)

## Output Documents

### Hotwash Report (.docx)
```
PROPOSAL HOTWASH REPORT
{Solicitation Number} — {Title}
{Agency}  |  Outcome: {WON/LOST/NO-BID}  |  Date: {date}

EXECUTIVE SUMMARY
[Brief paragraph on outcome and overall assessment]

PROPOSAL TIMELINE
Kickoff: {date}  |  Pink Team: {date}  |  Red Team: {date}
Gold Team: {date}  |  Submitted: {date}  |  Due: {date}
[Variance analysis: were we on schedule?]

CATEGORY SCORES
Process Area        Score  Notes
Opportunity Assess. 8/10   "Strong intel through PM contact"
Proposal Mgmt.      6/10   "Schedule slipped 3 days on Red Team"
Writing/Compliance  7/10   "Good technical, PP section thin"
Cost Volume         5/10   "Lost on price — 12% higher than award"
Team Performance    8/10   "Subs delivered on time"

WHAT WENT WELL
1. [Item]
2. [Item]

WHAT TO IMPROVE
1. [Item with root cause]
2. [Item with root cause]

LESSONS LEARNED
1. [Lesson → future action]
2. [Lesson → future action]

PROCESS IMPROVEMENT ACTION ITEMS
Owner | Item | Target Date | Status
```

## Pattern Analysis

After 3+ proposals, run pattern analysis:

```
User: "Analyze our proposal win/loss patterns"

Claude runs hotwash pattern analysis:
1. Load all hotwash events from database
2. Analyze by: agency, contract type, set-aside, value range
3. Identify: which categories score lowest? which teams perform best?
4. Correlate: bid/no-bid pwin scores vs. actual wins
5. Generate insights and recommendation updates
```

Example insight:
> "Cost volumes consistently score 4-5/10. Root cause: rates reviewed too late (Gold Team vs earlier). Recommendation: add 'Rate Review Complete' milestone to proposal schedule template at -20 days."

## Skill Improvement Loop

After each hotwash, automatically:
1. Flag which scoring criteria were most/least accurate in opportunity-curator
2. Update bid/no-bid weight suggestions based on outcome vs prediction
3. Add reusable "gold standard" paragraphs from high-scoring sections
4. Update proposal schedule milestones based on timeline performance

This is how the system gets smarter with every proposal.

## Debrief Tracking

For lost proposals, government agencies often provide debriefs:
- Log debrief request date and status
- Record debrief feedback verbatim
- Map debrief feedback to lesson categories
- Update competitive intelligence database
