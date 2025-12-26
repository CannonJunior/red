---
name: career-monster
description: "Analyze highly selective career positions (<1% acceptance rate) by examining patterns in successful hires. Initial focus: PhD → tenure-track academic positions. Generates multi-perspective assessments (optimistic, pessimistic, pragmatic, speculative) based on: (1) Dissertation-department topic alignment, (2) Publication strength and citations, (3) Co-author network analysis, (4) PhD institution prestige. Use for career strategy planning, not for guaranteeing outcomes."
---

# Career-Monster: Competitive Career Position Analysis

## Overview

Career-Monster analyzes highly selective career positions (typically <1% acceptance rate) by studying patterns in successful hires. The skill uses data-driven analysis to generate multi-perspective assessments that help users understand competitive hiring landscapes.

**Initial Use Case**: PhD → Tenure-Track Academic Positions in Political Science

**Key Capabilities**:
- Manual entry of hiring position and candidate data
- Multi-factor alignment scoring (0-10 scale)
- Four-perspective narrative generation using local AI
- Network analysis of co-authorship patterns
- Gap analysis comparing user profile to successful candidates
- Export to CSV and markdown reports

## Quick Start

### Access Career-Monster Interface

**Via Main Application**:
1. Navigate to http://localhost:9090/
2. Click "Skills Interface" in sidebar
3. Select "Career-Monster"
4. Use 3-step workflow to analyze positions

**Via Standalone Page**:
1. Navigate to http://localhost:9090/career-monster.html
2. Follow guided workflow

### Basic Workflow

```
Step 1: Add Position
→ Enter institution, department, field, hire date
→ List department research areas

Step 2: Add Candidate
→ Enter hired individual's details
→ PhD institution, dissertation title, keywords
→ Publications count, citations, co-authors

Step 3: Generate Assessment
→ Select verbosity level (brief/standard/detailed)
→ Generate multi-perspective analysis
→ View alignment scores and narratives
```

### API Usage (Programmatic)

```python
from career_monster import (
    CareerDatabase,
    AlignmentScorer,
    NarrativeGenerator,
    HiringPosition,
    Candidate
)

# Initialize database
db = CareerDatabase("opportunities.db")

# Create position
position = HiringPosition(
    institution="Harvard University",
    department="Government",
    position_title="Assistant Professor",
    field_specialty="Political Science",
    hire_date="2024-07-01",
    department_research_areas=["Democracy", "Political Economy", "Comparative Politics"]
)
position_id = db.create_position(position)

# Create candidate
candidate = Candidate(
    name="Jane Doe",
    phd_institution="Stanford University",
    phd_year=2023,
    dissertation_title="Democratic Accountability in Hybrid Regimes",
    dissertation_keywords=["democracy", "accountability", "hybrid regimes"],
    dissertation_abstract="This dissertation examines...",
    publications_count=5,
    citations_count=120,
    co_authors=["Alice Smith", "Bob Johnson", "Carol Williams"]
)
candidate_id = db.create_candidate(candidate, position_id)

# Run analysis
scorer = AlignmentScorer()
alignment = scorer.calculate_alignment(candidate, position)
network = scorer.analyze_network(candidate)
confidence = scorer.calculate_confidence(candidate, position)

# Generate narratives
generator = NarrativeGenerator(
    ollama_url="http://localhost:11434",
    model="qwen2.5:3b"
)

assessment = generator.generate_assessment(
    candidate=candidate,
    position=position,
    alignment=alignment,
    network=network,
    verbosity="standard"
)

# Save results
assessment.confidence_score = confidence
assessment_id = db.create_assessment(assessment, candidate_id, position_id)

print(f"✅ Assessment complete: {assessment_id}")
print(f"Overall score: {alignment.overall_score:.1f}/10")
print(f"\nOptimistic: {assessment.optimistic_narrative[:200]}...")
```

## Analysis Components

### Alignment Scoring (0-10 Scale)

**Topic Alignment** (35% weight)
- Keyword matching between dissertation and department research areas
- Jaccard similarity + semantic overlap
- Score interpretation:
  - 8-10: Excellent fit (5+ keyword matches)
  - 5-7: Moderate fit (1-4 matches)
  - 0-4: Weak fit (minimal overlap)

**Network Overlap** (20% weight)
- Co-authorship network size and quality
- Institutional diversity estimation
- Score interpretation:
  - 9-10: 10+ collaborators
  - 7-8: 5-9 collaborators
  - 3-6: 1-4 collaborators

**Methodology Match** (20% weight)
- Detection of quantitative, qualitative, formal methods
- Multi-method approaches scored higher
- Field-appropriate methodology bonus

**Publication Strength** (25% weight)
- Publication count (peer-reviewed)
- Citation impact adjustment
- Score interpretation:
  - 9-10: 8+ papers or 200+ citations
  - 7-8: 5+ papers or 100+ citations
  - 4-6: 2-4 papers

### Four-Perspective Narratives

**Optimistic Perspective**
- Best-case interpretation of hire
- Focus on exceptional strengths
- Perfect timing and strategic advantages
- Future potential trajectory

**Pessimistic/Critical Perspective**
- Potential gaps or limitations
- Competitive disadvantages
- Market conditions working against
- Alternative explanations beyond merit

**Pragmatic Perspective**
- Balanced strengths AND weaknesses
- Clear evidence vs speculation
- Market realities and constraints
- Reproducible success elements

**Speculative Perspective**
- Hidden or non-obvious factors
- Personal connections and networks
- Timing and strategic positioning
- Departmental politics and funding
- Diversity initiatives and priorities

### Confidence Scoring

**Data Quality** (0-1 scale)
- Completeness of candidate information
- Availability of dissertation data
- Publication and network details

**Analysis Robustness** (0-1 scale)
- Pattern strength in alignment scores
- Quality of available comparisons

**Overall Confidence**
- Average of data quality and robustness
- Provides transparency on analysis limitations

## Database Schema

Career-Monster uses 4 main tables:

**career_positions**
- Institution, department, position details
- Department research areas (JSON)
- Job posting information

**career_candidates**
- PhD information and dissertation details
- Publications and citations
- Co-author networks (JSON)
- Awards data (JSON)

**career_assessments**
- Alignment scores (all 4 components)
- Network analysis metrics
- Four narrative perspectives
- Success factors and red flags

**coauthor_networks**
- Individual collaborator records
- Joint publication counts
- Star collaborator identification

## API Endpoints

Career-Monster integrates with the main application via REST API:

```
GET  /api/career/positions      # List positions
POST /api/career/positions      # Create position
POST /api/career/candidates     # Create candidate
POST /api/career/analyze        # Generate assessment
GET  /api/career/assessments/:id # Get assessment
GET  /api/career/stats          # Dashboard statistics
```

## Evidence-Based Success Factors

Based on research of academic hiring patterns:

**PhD Institution Prestige** (Strongest Factor)
- 80% of faculty from 20% of institutions
- Harvard, Princeton, Stanford, Michigan: 20% of all tenure-stream faculty

**Publication Requirements** (Critical Threshold)
- 4-5 peer-reviewed papers typical for competitive candidates
- ABD candidates severely disadvantaged vs PhD-in-hand

**Co-authorship Networks** (Emerging Factor)
- Early collaboration with highly-cited researchers predicts success
- Network position affects citations and visibility

**Topic Alignment** (Department-Specific)
- Dissertation must align with departmental research priorities
- 96% of successful hires show strong alignment

**Dissertation Quality Indicators**
- APSA dissertation awards signal excellence
- External grants (NSF, DDRIG) demonstrate research potential

*Research sources: Harvard Kennedy School, Cambridge University Press, Inside Higher Ed, Nature, arXiv*

## Ethical Considerations

**What Career-Monster Does** ✅
- Identifies patterns and correlations in public data
- Provides multi-perspective analysis (not single "truth")
- Includes confidence scores for transparency
- Uses only publicly available information
- Adds disclaimers to all outputs

**What Career-Monster Does NOT Do** ❌
- Predict hiring decisions with certainty
- Claim causation from correlations
- Use private or password-protected data
- Guarantee outcomes based on patterns
- Ignore systemic barriers in hiring

**Methodological Disclaimers**

All outputs include:
> This assessment identifies patterns and correlations in hiring data. Correlation does not imply causation. Actual hiring decisions involve factors not captured in public data, including: interviews, teaching demonstrations, departmental politics, funding availability, and strategic positioning. Use these insights as one input among many for career planning.

## Output Examples

### CSV Export Format

```csv
name,institution,department,position,phd_institution,phd_year,dissertation_topic,overall_score,topic_alignment,publications,citations
Jane Doe,Harvard,Government,Assistant Professor,Stanford,2023,Democratic Accountability,8.2,8.5,5,120
```

### Markdown Report Format

```markdown
# Hiring Assessment: Jane Doe → Harvard Government (2024)

## Alignment Scores
- **Overall**: 8.2/10 (High Confidence)
- Topic Alignment: 8.5/10
- Network Overlap: 7.2/10
- Publications: 8.5/10
- Methodology: 7.0/10

## Success Factors
✅ Excellent topic alignment (8.5/10) between dissertation and department research
✅ Strong publication record (5 papers, 120 citations)
✅ PhD from top-tier institution (Stanford)
✅ Well-developed co-authorship network (8 collaborators)

## Optimistic Narrative
[Generated by Ollama - 3-5 paragraphs explaining best-case interpretation...]

## Pragmatic Narrative
[Generated by Ollama - Balanced assessment with evidence...]
```

## Common Use Cases

### 1. Career Strategy Planning
- Identify competitive gaps before applying
- Understand hiring preferences by subfield
- Plan publication and collaboration strategy

### 2. PhD Candidate Benchmarking
- Compare own profile to successful hires
- Set realistic publication targets
- Identify strategic collaboration opportunities

### 3. Departmental Hiring Analysis
- Study hiring patterns over time
- Understand institutional preferences
- Benchmark against competitor departments

## Phase 1 MVP Features (Current)

✅ Manual data entry via web interface
✅ Alignment scoring engine (keyword-based)
✅ Multi-perspective narrative generation (Ollama)
✅ Network analysis (basic)
✅ Database persistence (SQLite)
✅ Web dashboard with statistics
✅ CSV and markdown export

## Future Enhancements

### Phase 2: User Comparison
- Profile comparison feature
- Gap analysis with recommendations
- Personalized career strategy suggestions

### Phase 3: Web Scraping
- Semi-automated data collection from .edu sites
- Google Scholar integration
- ProQuest dissertation retrieval

### Phase 4: Advanced Analytics
- Time-series analysis of hiring trends
- Cluster analysis of successful profiles
- Predictive modeling (with disclaimers)

### Phase 5: Multi-Field Support
- Economics, Computer Science, Sociology
- Industry positions (data science, research scientist)
- Postdoc and research fellow positions

## Troubleshooting

**Issue**: Narratives are generic or repetitive
**Solution**: Increase verbosity level or provide more detailed candidate information

**Issue**: Low alignment scores across all candidates
**Solution**: Check department research areas are comprehensive and specific

**Issue**: Ollama timeout during assessment
**Solution**: Use "brief" verbosity mode or restart Ollama service

**Issue**: Database schema not initialized
**Solution**: Migration runs automatically on first import of CareerDatabase class

## Technical Architecture

**Backend**: Python (Pydantic, SQLite)
**Frontend**: HTML/CSS/JavaScript (embedded in main app)
**LLM**: Ollama (qwen2.5:3b for narrative generation)
**Database**: SQLite (opportunities.db with career_* tables)
**Integration**: REST API with main RED application

## Support

For issues or enhancements:
- Check documentation in `docs/career-monster/`
- Review implementation plan
- Test with manual entry workflow first

---

**Skill Version**: 1.0.0 (Phase 1 MVP)
**Last Updated**: 2025-12-26
**Maintainer**: RED Project Team
