---
name: crm-sync
description: "CRM and collaboration platform sync for GovCon proposals. When Claude needs to: (1) Push proposal data to Unanet CRM (create or update opportunity records), (2) Create SharePoint proposal folder structure with standard sub-directories, (3) Upload proposal documents to SharePoint document libraries, (4) Pull pipeline updates from Unanet back to local database, (5) Set up Microsoft 365 sharing links for external reviewers, (6) Generate sync status reports showing what is and isn't synced. Use AFTER bid-no-bid for active proposals, or at any stage to sync data."
---

# CRM Sync — Unanet & SharePoint Integration

## Overview

This skill provides **bidirectional synchronization** between the local proposals database and external platforms:
- **Unanet CRM**: Opportunity pipeline tracking
- **SharePoint**: Document library and folder management (Microsoft Graph API)
- **SharePoint → Future**: Will serve as SharePoint CRM when Unanet is retired

**Key Capabilities**:
- Create/update Unanet CRM opportunity records
- Create SharePoint proposal folder structures
- Upload documents to SharePoint
- Generate sharing links for external reviewers
- Pull Unanet pipeline updates to local DB
- Generate sync status dashboard

## Workflow Position

```
[bid-no-bid] → crm-sync (create CRM record + SP folder)
[proposal-setup] → crm-sync (upload documents to SP)
[document-drafter] → crm-sync (upload drafts to SP)
```

## Quick Start

### Sync a Proposal to Unanet

```
User: "Sync FA8612-26-R-0001 to Unanet CRM"

Claude runs crm-sync to:
1. Load proposal from local database
2. Check if Unanet opportunity already exists (by solicitation number)
3. Create or update the Unanet opportunity record
4. Store returned crm_opportunity_id in proposals table
5. Log activity in Unanet: "Proposal created by [capture_manager]"
```

### Create SharePoint Proposal Folder

```
User: "Set up the SharePoint folder for FA8612-26-R-0001"

Claude runs crm-sync to:
1. Authenticate to SharePoint (uses cached token)
2. Create folder: Proposals/FY26/AFRL_FA8612-26-R-0001_MyEffort/
3. Create all standard sub-folders (00_RFP through 05_Final)
4. Store folder URL and site ID in proposals table
5. Return folder URL for team distribution
```

### Upload Documents

```
User: "Upload the technical volume draft to SharePoint"

Claude runs crm-sync to:
1. Locate file in outputs/proposal/{solicitation}/
2. Upload to appropriate SharePoint sub-folder (03_Working/Vol-1-Technical/)
3. Return SharePoint URL for sharing
```

## Unanet Field Mapping

Field mapping is driven by `proposal/integrations/unanet_mapping.json`.
Edit that file to adjust mappings without code changes.

| Local Field | Unanet Field | Notes |
|------------|--------------|-------|
| solicitation_number | external_id | Unique identifier |
| title | name | Opportunity name |
| pipeline_stage | stage_code | Mapped to Unanet codes |
| estimated_value | potential_revenue | Dollar value |
| proposal_due_date | close_date | |
| capture_manager | owner_username | Unanet user login |
| agency | client_name | |
| pwin_score | probability | Converted ×100 |

## SharePoint Folder Structure

Created automatically for each active proposal:
```
Proposals/
└── FY26/
    └── AFRL_FA8612-26-R-0001_ShortTitle/
        ├── 00_RFP/             ← Drop solicitation package here
        ├── 01_Analysis/        ← Shredding outputs, gap analysis
        ├── 02_BidNoBid/        ← B/NB slide and worksheet
        ├── 03_Working/         ← Live drafts (internal access)
        │   ├── Vol-1-Technical/
        │   ├── Vol-2-Management/
        │   ├── Vol-3-Cost/
        │   └── Vol-4-PastPerformance/
        ├── 04_Reviews/         ← Color team markup copies
        │   ├── Pink-Team/
        │   ├── Red-Team/
        │   └── Gold-Team/
        └── 05_Final/           ← Submission-ready package
            ├── Internal/
            └── Submission/
```

## Authentication Setup

### Unanet
1. Set `UNANET_BASE_URL` and `UNANET_API_KEY` in `.env`
2. No browser step required — API key authentication

### SharePoint (One-time browser step)
```bash
uv run python -c "
from proposal.integrations.sharepoint import SharePointClient
client = SharePointClient()
client.authenticate()  # Opens browser for Microsoft login
"
```
Token is cached in `~/.red/sharepoint_token.json` and refreshes automatically.

## Sync Status Report

```
User: "Show CRM sync status for active proposals"

Output:
┌─────────────────────┬───────────┬──────────────┬─────────────────────┐
│ Solicitation        │ Pipeline  │ Unanet Sync  │ SharePoint Sync     │
├─────────────────────┼───────────┼──────────────┼─────────────────────┤
│ FA8612-26-R-0001    │ active    │ ✓ OPP-4521  │ ✓ /Proposals/FY26/… │
│ W81XWH-26-R-0025    │ qualifying│ ✗ Not synced│ ✗ Not created       │
│ N00014-26-BAA-01    │ bid_dec   │ ✓ OPP-4498  │ ✗ Not created       │
└─────────────────────┴───────────┴──────────────┴─────────────────────┘
```

## Future: SharePoint CRM Migration

When Unanet is replaced by SharePoint CRM:
1. Update `UNANET_BASE_URL` to empty string in `.env`
2. Enable `SHAREPOINT_CRM_MODE=true`
3. crm-sync will write opportunity metadata to a SharePoint List instead
4. No code changes required — config-driven switchover

SharePoint List columns mirror the Unanet field mapping JSON.
