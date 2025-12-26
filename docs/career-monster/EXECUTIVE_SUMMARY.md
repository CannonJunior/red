# Career-Monster Skill - Executive Summary

**Date**: 2025-12-26
**Status**: Implementation Plan Complete - Awaiting Approval
**Recommendation**: PROCEED with modifications

---

## What Is Career-Monster?

A skill for analyzing highly selective career positions (<1% acceptance rate) by examining patterns in successful hires, with initial focus on PhD → Tenure-Track academic positions in Political Science.

**Core Capability**: Identify success factors in competitive hiring by analyzing:
- Dissertation topics and quality
- Publication records
- Co-authorship networks
- Alignment between candidate expertise and institutional needs
- Career trajectories and credentials

**Key Innovation**: Multi-perspective narrative assessment (optimistic, pessimistic, pragmatic, speculative) rather than single "score"

---

## Research Findings (Evidence-Based)

### Academic Hiring Success Factors

**1. PhD Institution Prestige** (Strongest Factor)
- 80% of faculty trained at 20% of institutions
- Top 11 schools produce 50% of political science academics
- Harvard, Princeton, Stanford, Michigan: 20% of tenure-stream faculty

**2. Publication Requirements** (Critical Threshold)
- Multiple peer-reviewed publications now standard
- "ABD" (All-But-Dissertation) candidates severely disadvantaged
- 4-5 publications typical for competitive candidates

**3. Co-authorship Networks** (Emerging Factor)
- Early collaboration with highly-cited researchers predicts success
- Network position (betweenness centrality) affects citations
- Collaboration with "star" researchers provides career boost

**4. Topic Alignment** (Department-Specific)
- Dissertation must align with departmental research priorities
- Faculty expertise match critical for intellectual contribution
- Emerging subfield specialists more marketable

**5. Dissertation Quality Indicators**
- APSA dissertation awards signal excellence
- External grants (NSF, DDRIG) demonstrate research potential
- Methodological innovation increases competitiveness

**Sources**:
- [Where You Earn Your PhD Matters (Cambridge Core)](https://www.cambridge.org/core/journals/ps-political-science-and-politics/article/where-you-earn-your-phd-matters/09DCA7FDED5D830D487FF4029F338944)
- [80% of Faculty from 20% of Institutions (Inside Higher Ed)](https://www.insidehighered.com/news/2022/09/23/new-study-finds-80-faculty-trained-20-institutions)
- [Early Coauthorship Predicts Success (Nature)](https://www.nature.com/articles/s41467-019-13130-4)
- [Forecasting Faculty Placement from Co-authorship Networks (arXiv)](https://arxiv.org/html/2507.14696)

---

## What The Skill Does

### Input
User specifies:
- Career field (default: Political Science)
- Position type (default: Assistant Professor, Tenure-Track)
- Target institutions (default: Top 50)
- Time range (default: Last 2 years)
- Assessment verbosity (default: Standard)

### Processing
1. **Web Scraping**: Identify recent hires from university .edu websites
2. **Dissertation Retrieval**: Access dissertations from ProQuest, university repositories
3. **Publication Analysis**: Scrape Google Scholar for publication records
4. **Network Mapping**: Build co-authorship networks
5. **Alignment Scoring**: Calculate topic-department match
6. **Narrative Generation**: Create 4-perspective assessments using Ollama

### Output
1. **CSV Table**: All analyzed hires with key metrics
2. **Individual Narratives**: 4-perspective assessment per hire (Markdown)
3. **Summary Report**: Hiring trends, success factors, recommendations
4. **RED Integration**:
   - Create Opportunities for target positions
   - Generate TODO tasks based on gap analysis
   - Display in web dashboard

---

## Technical Architecture

### Directory Structure
```
.claude/skills/career-monster/
├── SKILL.md
├── scripts/
│   ├── analyze_position.py
│   ├── scrape_new_hires.py
│   ├── retrieve_dissertation.py
│   └── generate_narratives.py
└── prompts/
    ├── optimistic_assessment.txt
    ├── pessimistic_assessment.txt
    ├── pragmatic_assessment.txt
    └── speculative_assessment.txt

career_monster/                    # Core library
├── web_scraper.py
├── dissertation_retriever.py
├── publication_analyzer.py
├── network_mapper.py
├── alignment_scorer.py
├── narrative_generator.py
└── data_models.py

outputs/career-monster/            # Skill outputs
├── analyses/
│   └── political-science-2024/
├── networks/
└── reports/
```

### Database Integration
```sql
career_positions       -- Hiring positions tracked
career_candidates      -- Candidates hired
career_assessments     -- Analysis results
coauthor_networks      -- Co-authorship data
```

### Web UI Integration
```
/career-monster                 -- Dashboard
/career-monster/analyze         -- Start analysis
/career-monster/position/<id>   -- Position detail
/career-monster/compare         -- User profile comparison
```

---

## Critical Issues & Resolutions

### Issue 1: Dissertation Access (HIGH PRIORITY)
**Problem**: ProQuest requires expensive institutional subscriptions

**Solution**: Tiered access strategy
1. Try university open-access repositories (free)
2. Try Google Scholar PDF links (sometimes free)
3. Use metadata only (abstract, keywords)
4. Prompt user for manual entry

**Result**: Functional with degraded data, not blocked

---

### Issue 2: Causation vs Correlation (CRITICAL)
**Problem**: Original plan implied we can determine "why" someone was hired

**Solution**:
- Changed all language to "patterns observed" not "causes identified"
- Added strong disclaimers to all outputs
- Multi-perspective narratives acknowledge uncertainty
- Included "confidence scores" for each analysis

**Result**: Ethically sound, scientifically accurate

---

### Issue 3: Computational Performance (MEDIUM)
**Problem**: Underestimated processing time (11 hours for 50 hires, not "5 minutes")

**Solution**:
- Aggressive caching (90-day TTL)
- Parallel processing (5 concurrent threads)
- Progressive results (save intermediate CSVs)
- Tiered analysis modes (Quick/Standard/Comprehensive)

**Result**: Realistic expectations, acceptable performance

---

## Modified Implementation Plan

### Phase 1: MVP (Weeks 1-2) - Manual Entry + Core Analysis
**Scope**:
- Web form for manual hire entry
- Alignment scoring (keyword-based)
- Narrative generation (Ollama, 4 perspectives)
- Test with 5 manually entered hires

**Deliverable**: Working analysis pipeline, 5 narrative reports

**Success Criteria**:
- Generate 4-perspective narratives
- User feedback: "insightful" rating
- Validate value before building automation

---

### Phase 2: User Comparison (Week 3)
**Scope**:
- User profile input form
- Gap analysis (user vs successful candidates)
- Personalized recommendations
- TODO task suggestions

**Deliverable**: Profile comparison feature

**Success Criteria**:
- Identify concrete gaps
- Generate actionable tasks
- Rated useful by test users

---

### Phase 3: Web Scraping (Week 4)
**Scope**:
- Scraper for 1 university (Harvard or Stanford)
- Dissertation metadata retrieval
- Google Scholar publication scraping
- Process 5-10 hires automatically

**Deliverable**: Semi-automated data collection

**Success Criteria**:
- 80% scraping success rate
- Data quality comparable to manual entry
- Processing time <2 hours for 10 hires

---

### Phase 4: Integration & Polish (Weeks 5-6)
**Scope**:
- CSV/Markdown export with timestamps
- Database schema implementation
- Opportunities mapping
- TODO generation with user approval
- Web dashboard UI

**Deliverable**: Production-ready MVP

**Success Criteria**:
- Seamless RED integration
- Clean, organized outputs
- Dashboard displays results
- All features documented

---

## Key Features

### 1. Multi-Perspective Narratives
Each hire analyzed from 4 viewpoints:
- **Optimistic**: Best-case interpretation, exceptional strengths
- **Pessimistic**: Critical analysis, potential weaknesses
- **Pragmatic**: Balanced, realistic assessment
- **Speculative**: Hidden factors, non-obvious influences

**Why**: Avoids over-confidence, promotes critical thinking

---

### 2. Alignment Scoring
Quantitative assessment of candidate-position match:
- **Topic Alignment**: Dissertation keywords vs department research (0-10)
- **Network Overlap**: Co-authors shared with department (0-10)
- **Methodology Match**: Research methods fit (0-10)
- **Publication Strength**: Citation impact vs field average (0-10)

**Overall Score**: Weighted average with confidence interval

---

### 3. Profile Comparison
User enters their own profile, system compares to successful candidates:
- **Gap Analysis**: What user lacks vs typical hire
- **Strength Analysis**: Where user exceeds typical hire
- **Recommendations**: Specific, actionable next steps
- **Timeline Estimation**: How long to close gaps

**Why**: Turns research into actionable career planning

---

### 4. RED Integration
Automatically creates:
- **Opportunities**: Target positions with application deadlines
- **TODO Tasks**: Gap-closing actions (with user approval)
- **Dashboard Views**: Hiring trends, success patterns
- **Export Files**: CSV tables, Markdown narratives

**Why**: Fits naturally into existing workflow

---

## User Interaction Flow

```
1. User invokes: /career-monster

2. System prompts for configuration:
   - Career field? [Political Science (default)]
   - Position type? [Assistant Professor (default)]
   - Target institutions? [Top 50 (default)]
   - Time range? [Last 2 years (default)]
   - Verbosity? [Standard (default)]

3. System analyzes:
   [Progress bar: Analyzing 23 recent hires...]
   - Scraping university websites...
   - Retrieving dissertations...
   - Analyzing publications...
   - Calculating alignment scores...
   - Generating narratives...

4. System outputs:
   ✅ CAREER ANALYSIS COMPLETE

   Analyzed: 23 hires in Political Science (2024)
   Average publications: 4.3
   Top PhD institutions: Princeton (5), Harvard (4)

   📁 Files generated:
   - summary_2024-12-26.csv
   - 23 individual narrative documents
   - hiring_trends_report_2024-12-26.html

   🎯 Key Success Factors:
   1. PhD from top-5 institution (87%)
   2. 3+ peer-reviewed publications (74%)
   3. Topic alignment with department (96%)

   💡 Recommendations for you:
   - Focus on building co-authorship networks
   - Target 4-5 publications before job market
   - Align dissertation with target departments

5. User options:
   - Compare my profile to successful candidates
   - Create opportunities for target positions
   - Generate TODO tasks from gap analysis
   - View web dashboard
```

---

## Ethical Considerations

### What We Do ✅
- Use only publicly available data
- Provide clear disclaimers (correlation ≠ causation)
- Offer anonymization options
- Respect robots.txt and terms of service
- Include confidence scores for transparency
- Multi-perspective narratives (not single "truth")

### What We Don't Do ❌
- Claim to predict hiring decisions
- Use password-protected or private data
- Guarantee outcomes
- Provide scores without context
- Ignore systemic barriers or biases

### Disclaimers Included
Every output includes:
```
METHODOLOGICAL NOTE: This assessment identifies patterns and correlations
in hiring data. Correlation does not imply causation. Actual hiring
decisions involve factors not captured in public data, including:
interviews, teaching demonstrations, departmental politics, funding
availability, and strategic positioning. Use these insights as one input
among many for career planning.
```

---

## Expected Outcomes

### For Job Seekers
- **Information Asymmetry Reduction**: Understand what successful candidates look like
- **Strategic Planning**: Identify gaps, prioritize improvements
- **Evidence-Based Decisions**: Career moves grounded in data, not speculation
- **Confidence Calibration**: Realistic assessment of competitiveness

### For The RED Project
- **Showcase Advanced Capabilities**: Multi-modal analysis (web, LLM, network)
- **Integration Excellence**: Seamless Opportunities/TODO workflow
- **Differentiation**: No existing tool provides this analysis
- **Extensibility**: Framework applies to other selective careers

### Success Metrics
- **User Adoption**: >10 analyses per month
- **Quality**: Narratives rated "insightful" by >70% of users
- **Actionability**: >70% of TODO tasks considered useful
- **Integration**: >5 opportunities created from career-monster per month

---

## Risks & Mitigations

### High Risks
1. **Data Access Limitations**: Mitigated by tiered access (full-text → metadata → manual)
2. **Over-promising Causation**: Mitigated by strong disclaimers, multi-perspective narratives

### Medium Risks
3. **Performance Issues**: Mitigated by caching, parallel processing, tiered modes
4. **Web Scraping Blocks**: Mitigated by polite scraping, multiple sources, manual fallback

### Low Risks
5. **LLM Hallucination**: Mitigated by grounding narratives in facts, including citations
6. **User Adoption**: Mitigated by clear value proposition, good documentation

---

## Timeline & Resources

### Development Timeline
- **Weeks 1-2**: Manual entry + core analysis (MVP validation)
- **Week 3**: User profile comparison
- **Week 4**: Web scraping prototype
- **Weeks 5-6**: Integration + polish

**Total: 6 weeks**

### Resource Requirements
- **Developer Time**: 6 weeks × 40 hours = 240 hours
- **Infrastructure**: RED project (existing)
- **LLM**: Ollama (existing, local, free)
- **Data Access**: ProQuest via library (check availability), Google Scholar (free)
- **Storage**: <10GB for 1000 analyses

**Total Cost**: Primarily developer time; negligible operational costs

---

## Recommendation: PROCEED ✅

### Rationale

**Strengths**:
1. ✅ Evidence-based approach (grounded in research)
2. ✅ Multi-perspective framework (innovative, honest)
3. ✅ Natural RED integration (enhances existing workflow)
4. ✅ Clear user value (job market intelligence)
5. ✅ Technically feasible (with modifications)
6. ✅ Ethically defensible (public data, disclaimers)

**Concerns Addressed**:
1. ✅ Data access: Tiered strategy works
2. ✅ Causation language: Fixed throughout
3. ✅ Performance: Realistic expectations set
4. ✅ Ethics: Strong guardrails in place

**Modified Approach**:
- Start with manual entry (validate value first)
- Add automation incrementally (scraping in Phase 3)
- Build profile comparison early (high user value)
- Integrate with RED from start (not bolted on later)

**Decision Points**:
- **After Week 2**: If narratives aren't useful → Pivot to scoring only
- **After Week 4**: If scraping fails → Stick with manual + community data
- **After Week 6**: If no adoption → Shelve or open-source

---

## Next Steps

1. **Review & Approval**: User reviews this plan, provides feedback
2. **Configuration Check**: Verify ProQuest access (or confirm metadata-only approach)
3. **Phase 1 Kickoff**: Begin manual data entry form + core analysis
4. **Test with Real Data**: 5 actual political science hires (manually entered)
5. **Validate Narratives**: Do they provide genuine insight?
6. **Iterate or Proceed**: Based on Phase 1 results

---

## Conclusion

The career-monster skill addresses a real pain point (brutal academic job market) with an innovative solution (multi-perspective analysis of successful hires). The research is solid, the technical approach is sound, and the integration with RED is well-designed.

**With the modifications outlined in this review**, the skill is:
- ✅ Technically feasible
- ✅ Ethically defensible
- ✅ Valuable to users
- ✅ Well-integrated with RED
- ✅ Scalable to other fields

**Proceed with modified Phase 1 scope**: Manual entry + core analysis to validate value before building automation complexity.

---

**Documents Created**:
1. `IMPLEMENTATION_PLAN.md` - Comprehensive technical plan (14,000+ words)
2. `PLAN_REVIEW_AND_CRITIQUE.md` - Critical analysis (8,000+ words)
3. `EXECUTIVE_SUMMARY.md` - This document (synthesis and recommendation)

**Status**: Ready for user review and approval

**Awaiting**: User decision to proceed or request modifications
