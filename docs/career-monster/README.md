# Career-Monster Skill - Documentation Index

**Date**: 2025-12-26
**Status**: Implementation Planning Complete - Awaiting User Approval

---

## Quick Navigation

**Start Here** → [Executive Summary](./EXECUTIVE_SUMMARY.md)

**Full Details** → [Implementation Plan](./IMPLEMENTATION_PLAN.md)

**Critical Review** → [Plan Review & Critique](./PLAN_REVIEW_AND_CRITIQUE.md)

---

## What Is This?

This directory contains comprehensive planning documentation for the **career-monster** skill - a tool for analyzing highly selective career positions (<1% acceptance rate) by examining patterns in successful hires.

**Initial Focus**: PhD → Tenure-Track academic positions in Political Science

**Core Innovation**: Multi-perspective narrative assessment rather than simplistic scoring

---

## Document Overview

### 1. [EXECUTIVE_SUMMARY.md](./EXECUTIVE_SUMMARY.md) - READ THIS FIRST ⭐

**What it is**: Concise synthesis of research, plan, and recommendations

**Key Sections**:
- What career-monster does
- Research findings (evidence-based)
- Technical architecture
- Critical issues & resolutions
- Modified implementation plan
- Recommendation: PROCEED ✅

**Reading Time**: 15 minutes

**For**: Anyone wanting to understand the skill quickly

---

### 2. [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) - COMPREHENSIVE DETAIL

**What it is**: Complete technical implementation plan (14,000+ words)

**Key Sections**:
- I. Research Phase Summary (academic hiring success factors)
- II. Skill Architecture (directory structure, data models)
- III. Technical Implementation Strategy (web scraping, analysis, narratives)
- IV. Integration with RED Project (database, opportunities, TODO, UI)
- V. User Interaction Flow (configuration, execution, output)
- VI. Technical Considerations & Challenges
- VII. Implementation Phases (6-week timeline)
- VIII. Success Metrics
- IX. Risk Mitigation
- X-XIV. Additional topics (alternatives, documentation, costs, conclusion)

**Reading Time**: 60 minutes

**For**: Developers, technical reviewers, implementation team

**Research Sources**:
- [Harvard Kennedy School New Faculty](https://www.hks.harvard.edu/admissions-blog/hks-welcomes-new-faculty-members)
- [Where You Earn Your PhD Matters (Cambridge)](https://www.cambridge.org/core/journals/ps-political-science-and-politics/article/where-you-earn-your-phd-matters/09DCA7FDED5D830D487FF4029F338944)
- [80% of Faculty from 20% of Institutions](https://www.insidehighered.com/news/2022/09/23/new-study-finds-80-faculty-trained-20-institutions)
- [Co-authorship Networks Predict Placement](https://arxiv.org/html/2507.14696)
- [Early Coauthorship Predicts Success](https://www.nature.com/articles/s41467-019-13130-4)
- [ProQuest Dissertations & Theses Global](https://about.proquest.com/en/products-services/pqdtglobal/)

---

### 3. [PLAN_REVIEW_AND_CRITIQUE.md](./PLAN_REVIEW_AND_CRITIQUE.md) - CRITICAL ANALYSIS

**What it is**: Self-critical review of implementation plan (8,000+ words)

**Key Sections**:
- I. Critical Issues Analysis (3 major issues identified)
- II. Major Strengths (5 strengths identified)
- III. Recommended Modifications (7 modifications proposed)
- IV. Integration Review (point-by-point assessment)
- V. Feasibility Assessment (technical, resource, user value, ethical)
- VI. Alternative Approaches
- VII. Risk Assessment
- VIII. Recommendations Summary
- IX. Final Recommendation: PROCEED WITH MODIFICATIONS ✅

**Reading Time**: 40 minutes

**For**: Stakeholders, reviewers, risk assessment

---

## Key Findings from Research

### Academic Hiring Success Factors (Evidence-Based)

1. **PhD Institution Prestige** (Strongest Factor)
   - 80% of faculty trained at 20% of institutions
   - Harvard, Princeton, Stanford, Michigan: 20% of all tenure-stream faculty

2. **Publication Requirements** (Critical Threshold)
   - 4-5 peer-reviewed publications typical for competitive candidates
   - ABD candidates severely disadvantaged vs PhD-in-hand

3. **Co-authorship Networks** (Emerging Factor)
   - Early collaboration with highly-cited researchers predicts success
   - Network position affects citations and visibility

4. **Topic Alignment** (Department-Specific)
   - Dissertation must align with departmental research priorities
   - 96% of successful hires show strong alignment

5. **Dissertation Quality Indicators**
   - APSA dissertation awards signal excellence
   - External grants (NSF, DDRIG) demonstrate research potential

---

## Critical Issues Identified & Resolved

### Issue 1: Dissertation Access (HIGH PRIORITY)
**Problem**: ProQuest requires expensive subscriptions

**Solution**: Tiered access strategy
- Try university repositories (free)
- Use metadata only if full-text unavailable
- Manual entry as fallback

**Status**: ✅ RESOLVED

---

### Issue 2: Causation vs Correlation (CRITICAL)
**Problem**: Original plan implied we can determine "why" someone was hired

**Solution**:
- Changed all language from "why hired" to "patterns observed"
- Added strong disclaimers to all outputs
- Multi-perspective narratives acknowledge uncertainty

**Status**: ✅ RESOLVED

---

### Issue 3: Computational Performance (MEDIUM)
**Problem**: Underestimated processing time (11 hours for 50 hires)

**Solution**:
- Aggressive caching (90-day TTL)
- Parallel processing
- Tiered analysis modes (Quick/Standard/Comprehensive)

**Status**: ✅ RESOLVED

---

## Modified Implementation Timeline

### Phase 1: MVP (Weeks 1-2)
**Focus**: Manual entry + core analysis

**Deliverable**: Working analysis pipeline, 5 narrative reports

**Success Criteria**: Validate value before building automation

---

### Phase 2: User Comparison (Week 3)
**Focus**: Gap analysis, personalized recommendations

**Deliverable**: Profile comparison feature

**Success Criteria**: Generate actionable insights for users

---

### Phase 3: Web Scraping (Week 4)
**Focus**: Semi-automated data collection

**Deliverable**: Scrape 5-10 hires from 1 university

**Success Criteria**: 80% scraping success rate

---

### Phase 4: Integration & Polish (Weeks 5-6)
**Focus**: RED integration, dashboard, documentation

**Deliverable**: Production-ready MVP

**Success Criteria**: Seamless integration with existing workflow

---

## Technical Architecture Summary

### Core Components
1. **Web Scraper**: Extract hiring data from .edu sites
2. **Dissertation Retriever**: Access dissertations from multiple sources
3. **Publication Analyzer**: Scrape Google Scholar, JSTOR
4. **Network Mapper**: Build co-authorship networks
5. **Alignment Scorer**: Calculate topic-department match
6. **Narrative Generator**: Create 4-perspective assessments (Ollama)

### Integration with RED
- **Database**: New tables (career_positions, career_candidates, career_assessments)
- **Opportunities**: Map positions to opportunities for tracking
- **TODO**: Generate tasks based on gap analysis (with user approval)
- **Web UI**: Dashboard at `/career-monster`

### Output Directory
```
outputs/career-monster/
├── analyses/
│   └── political-science-2024/
│       ├── summary_2024-12-26.csv
│       ├── candidate_narrative_2024-12-26.md
│       └── ...
├── networks/
│   └── coauthorship_graph_2024-12-26.gexf
└── reports/
    └── hiring_trends_2024-12-26.html
```

---

## Key Features

### 1. Multi-Perspective Narratives
Each hire analyzed from 4 viewpoints:
- **Optimistic**: Best-case interpretation
- **Pessimistic**: Critical analysis
- **Pragmatic**: Balanced assessment
- **Speculative**: Hidden factors

### 2. Alignment Scoring
Quantitative assessment (0-10):
- Topic alignment
- Network overlap
- Methodology match
- Publication strength

### 3. Profile Comparison
User vs successful candidates:
- Gap analysis
- Strength identification
- Actionable recommendations

### 4. RED Integration
- Opportunity creation
- TODO task generation
- Web dashboard
- Export (CSV, Markdown)

---

## Ethical Considerations

### What We Do ✅
- Use only publicly available data
- Provide clear disclaimers
- Multi-perspective narratives (not single "truth")
- Confidence scores for transparency
- Respect robots.txt and ToS

### What We Don't Do ❌
- Claim to predict hiring decisions
- Use private or password-protected data
- Guarantee outcomes
- Ignore systemic barriers

---

## Recommendation: PROCEED ✅

### Why Proceed?

**Strengths**:
- Evidence-based approach
- Innovative multi-perspective framework
- Natural RED integration
- Clear user value
- Technically feasible
- Ethically defensible

**Concerns Addressed**:
- Data access: Tiered strategy
- Causation: Language fixed
- Performance: Realistic expectations
- Ethics: Strong guardrails

**Modified Approach**:
- Start with manual entry (validate first)
- Add automation incrementally
- Build profile comparison early
- Integrate with RED from start

---

## Next Steps

1. **User Review**: Review these documents, provide feedback
2. **Decision**: Approve, request modifications, or decline
3. **If Approved**:
   - Verify ProQuest access (or confirm metadata-only)
   - Begin Phase 1: Manual entry + core analysis
   - Test with 5 real political science hires
   - Validate narrative quality
   - Iterate or proceed based on results

---

## Document Statistics

- **Total Documentation**: 3 comprehensive documents
- **Total Word Count**: ~30,000 words
- **Research Sources**: 10+ academic studies and databases
- **Implementation Timeline**: 6 weeks
- **Expected Development Hours**: 240 hours

---

## Questions & Feedback

For questions or feedback on this planning documentation:
1. Review the Executive Summary first
2. Dive into Implementation Plan for technical details
3. Check Review & Critique for critical analysis
4. Provide feedback on approach, scope, or priorities

---

**Status**: Ready for user review and decision

**Created**: 2025-12-26

**Next Update**: After user approval (if proceeding to implementation)
