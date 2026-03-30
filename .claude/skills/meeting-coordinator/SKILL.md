---
name: meeting-coordinator
description: "Proposal meeting coordination and notes management toolkit. When Claude needs to: (1) Generate meeting agendas for kickoff, pink/red/gold team reviews, orals prep, or weekly syncs, (2) Record and structure meeting notes with action items, (3) Create Confluence pages from meeting notes, (4) Track action items with owners and due dates, (5) Distribute meeting summaries, (6) Schedule the next meeting based on proposal timeline. Use throughout the active proposal phase for all proposal-related meetings."
---

# Meeting Coordinator

## Overview

This skill handles the **full meeting lifecycle** for proposal teams — from agenda generation through action item tracking. Every major review type has a purpose-built template.

**Key Capabilities**:
- Generate meeting agendas by type (kickoff, color teams, orals, weekly)
- Record structured meeting notes with action items and owners
- Create Confluence pages for each meeting automatically
- Track action items across meetings with status updates
- Produce meeting summary documents (.docx)
- Alert on overdue action items

## Workflow Position

```
[proposal-setup] → meeting-coordinator (kickoff)
[document-drafter] → meeting-coordinator (color team reviews)
[submitted] → meeting-coordinator (hotwash setup)
```

## Meeting Types

### Kickoff Meeting
**Timing**: Day 1 of active proposal (45+ days before due)
**Duration**: 2 hours
**Agenda**:
1. Opportunity Overview & Win Strategy (15 min)
2. Proposal Structure & Volume Assignments (20 min)
3. Schedule, Milestones & Color Team Dates (15 min)
4. Tools, Folder Access & Process (15 min)
5. Team Introductions & Subcontractor Roles (20 min)
6. Q&A & Action Items (15 min)

### Pink Team Review
**Timing**: ~28 days before due
**Purpose**: Review storyboards/outlines — is the approach right?
**Duration**: 3-4 hours
**Agenda**:
1. Review Purpose & Scoring Context (15 min)
2. Technical Volume Walk-Through (90 min)
3. Management Volume Walk-Through (30 min)
4. Cost Strategy Discussion (20 min)
5. Reviewer Feedback & Scoring (30 min)
6. Action Items (15 min)

### Red Team Review
**Timing**: ~15 days before due
**Purpose**: Full draft review — compliance and quality
**Duration**: Full day
**Agenda**:
1. Proposal Compliance Check (30 min)
2. Technical Volume Review (2 hr)
3. Management Volume Review (1 hr)
4. Past Performance Review (30 min)
5. Cost Volume Review (30 min)
6. Overall Score & Feedback (30 min)
7. Priority Action Items (30 min)

### Gold Team Review
**Timing**: ~5 days before due
**Purpose**: Executive review — final approval
**Duration**: 2-3 hours
**Agenda**:
1. Summary of Changes Since Red Team (15 min)
2. Key Risk Areas Review (30 min)
3. Executive Summary Review (30 min)
4. Cost/Price Final Review (20 min)
5. Approval or Hold (15 min)

### Weekly Sync
**Duration**: 30-45 minutes
**Recurring**: Every Monday during active proposal

## Quick Start

### Create Kickoff Agenda

```
User: "Create the kickoff meeting agenda for FA8612-26-R-0001, scheduled March 30 at 10 AM"

Claude runs meeting-coordinator to:
1. Load proposal from database
2. Generate kickoff agenda with proposal-specific details
3. Output: outputs/proposal/FA8612-26-R-0001/_admin/kickoff_agenda_2026-03-30.docx
4. Create Confluence page (if configured)
5. Return agenda for review and distribution
```

### Record Meeting Notes

```
User: "Record notes from the Pink Team review of FA8612-26-R-0001"
Claude: [Asks for attendees, date, notes, action items]

Claude runs meeting-coordinator to:
1. Create ProposalMeeting record in database
2. Structure notes with action items (owner + due date)
3. Generate meeting summary .docx
4. Create Confluence child page under "Meeting Notes"
5. Return action item list for distribution
```

### Check Action Items

```
User: "What action items are open for FA8612-26-R-0001?"

Claude runs meeting-coordinator to:
1. Load all meetings for the proposal
2. Aggregate action items across meetings
3. Filter by status = open
4. Sort by due date
5. Flag overdue items

Output:
OVERDUE:
  ✗ "Update past performance refs" — Jane Smith — was due 2026-03-25

DUE THIS WEEK:
  ⚠ "Get subcontractor LOC" — Bob Jones — due 2026-03-31
  ⚠ "Finalize org chart" — Jane Smith — due 2026-04-01

OPEN:
  □ "Technical approach revision" — Mike Chen — due 2026-04-05
```

## Output Files

```
outputs/proposal/{solicitation}/_admin/
  kickoff_agenda_{date}.docx
  pink_team_notes_{date}.docx
  red_team_notes_{date}.docx
  gold_team_notes_{date}.docx
  action_items_open_{date}.docx
```

## Confluence Integration

When CONFLUENCE_* env vars are configured:
- Each meeting creates a child page under "Meeting Notes"
- Action items are formatted as a task list in Confluence
- Pages are linked back from the Proposal Schedule page
- Search across all meeting notes for past decisions

## Notes for Improvement

- After proposals: Track which action items consistently recur → fix the process
- Identify which meeting types have the most overdue items → schedule earlier
- Track color team review quality scores over time
