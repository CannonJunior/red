# Career-Monster Skill - Implementation Plan

**Date**: 2025-12-26
**Purpose**: Analyze highly selective career positions (<1% acceptance rate) to identify success factors
**Initial Focus**: PhD → Tenure-Track Academic Positions in Political Science

---

## Executive Summary

The career-monster skill will analyze extremely competitive career placements by:
1. Identifying recent hires at target institutions
2. Retrieving and analyzing candidate dissertations and publications
3. Mapping co-authorship networks and institutional connections
4. Assessing alignment between candidate expertise and hiring department needs
5. Generating multi-perspective narratives explaining hiring decisions
6. Producing actionable intelligence for users pursuing similar positions

**Research Findings**: Academic hiring in political science is influenced by:
- **PhD Institution Prestige**: 80% of faculty trained at 20% of institutions
- **Publication Record**: Multiple peer-reviewed publications increasingly required
- **Co-authorship Networks**: Early collaboration with top scientists predicts success
- **Topic Alignment**: Dissertation topics matching departmental research priorities
- **Dissertation Quality**: Award-winning dissertations (APSA awards) signal excellence

---

## I. Research Phase Summary

### A. Academic Hiring Success Factors (Evidence-Based)

**1. Institution Prestige (Strongest Factor)**
- 11 schools contribute 50% of political science academics to research universities
- Harvard, Princeton, Stanford, Michigan: 20% of tenure-stream faculty
- Prestige operates as "trap" - harder to escape less prestigious institutions

**2. Publication Requirements (Critical Threshold)**
- Multiple peer-reviewed publications now standard for assistant professor positions
- ABD (All-But-Dissertation) candidates at severe disadvantage vs PhD-in-hand
- Post-doctoral positions increasingly serve as publication incubators

**3. Co-authorship Networks (Emerging Factor)**
- Early collaboration with highly-cited researchers predicts future success
- Betweenness centrality in co-authorship networks affects citations
- Network position provides complementary predictive power beyond PhD rank

**4. Topic Alignment (Department-Specific)**
- Dissertation topics must align with departmental research priorities
- Faculty expertise match critical for advising and intellectual contribution
- Emerging subfield specialists more marketable than traditional areas

**5. Dissertation Quality Indicators**
- APSA dissertation awards (e.g., Merze Tate Award, Almond Award)
- External grants (APSA DDRIG, NSF funding)
- Methodological innovation or theoretical contribution

### B. Data Sources Identified

**Primary Sources**:
- University .edu websites (new faculty announcements)
- ProQuest Dissertations & Theses Global (6M+ dissertations)
- Google Scholar (publications, citations, co-authors)
- APSA job placement reports
- Department faculty pages

**Secondary Sources**:
- Academic journal databases (JSTOR, ProQuest Political Science)
- Conference presentation records (APSA, MPSA, ISA)
- Social media (academic Twitter/X for networking visibility)

### C. Example Cases Found

**Harvard Kennedy School 2024 Hires**:
1. Professor Bassan-Nygate (from Princeton postdoc)
   - Specialization: International relations, human rights, political psychology
   - Award: APSA 2024 Merze Tate Award (dissertation)

2. Professor Talibova (from Vanderbilt)
   - Previous position: Assistant Professor
   - Joint appointment: Political Science + Data Science Institute

**Stanford Political Science**:
- Michael Allen (Assistant Professor)
   - PhD: Princeton (Political Economy, 2012)
   - Previous: University of Rochester (Economics + Political Science)

---

## II. Skill Architecture

### A. Skill Definition Structure

```
.claude/skills/career-monster/
├── SKILL.md                        # Skill documentation
├── scripts/
│   ├── analyze_position.py         # Main analysis orchestrator
│   ├── scrape_new_hires.py        # Web scraping for .edu sites
│   ├── retrieve_dissertation.py    # ProQuest/repository access
│   ├── analyze_networks.py         # Co-authorship network analysis
│   ├── assess_alignment.py         # Topic-department matching
│   └── generate_narratives.py      # Multi-perspective assessments
├── prompts/
│   ├── optimistic_assessment.txt
│   ├── pessimistic_assessment.txt
│   ├── pragmatic_assessment.txt
│   └── speculative_assessment.txt
├── examples/
│   └── political_science_example.py
└── references/
    ├── academic_hiring_research.md
    └── data_sources.md
```

### B. Core Library Structure

```
career_monster/
├── __init__.py
├── web_scraper.py                  # .edu site scraping
├── dissertation_retriever.py       # Dissertation access & download
├── publication_analyzer.py         # Google Scholar, JSTOR integration
├── network_mapper.py               # Co-authorship network construction
├── alignment_scorer.py             # Topic-department matching
├── narrative_generator.py          # LLM-powered assessment generation
├── data_models.py                  # Pydantic models for positions, candidates
└── output_formatter.py             # CSV, narrative document generation
```

### C. Data Models

**Position**:
```python
class HiringPosition(BaseModel):
    institution: str
    department: str
    position_title: str
    hire_date: str
    job_posting_url: Optional[str]
    field_specialty: str
    department_faculty: List[FacultyMember]
    department_research_areas: List[str]
```

**Candidate**:
```python
class Candidate(BaseModel):
    name: str
    current_position: str
    phd_institution: str
    phd_year: int
    phd_advisor: Optional[str]
    dissertation_title: str
    dissertation_url: Optional[str]
    dissertation_keywords: List[str]
    dissertation_abstract: str
    publications: List[Publication]
    co_authors: List[str]
    awards: List[Award]
    citations_count: int
    h_index: Optional[int]
```

**Assessment**:
```python
class HiringAssessment(BaseModel):
    candidate: Candidate
    position: HiringPosition
    alignment_score: AlignmentScore
    network_analysis: NetworkAnalysis
    optimistic_narrative: str
    pessimistic_narrative: str
    pragmatic_narrative: str
    speculative_narrative: str
    key_success_factors: List[str]
    red_flags: List[str]
```

---

## III. Technical Implementation Strategy

### A. Phase 1: Web Scraping & Data Collection

**Components**:
1. **University Department Scraper**
   - Target: .edu political science department websites
   - Extract: New faculty announcements, faculty directory pages
   - Technology: BeautifulSoup4, Playwright (for JavaScript-heavy sites)
   - Output: List of recent hires with basic info

2. **Dissertation Retriever**
   - Primary: ProQuest Dissertations & Theses Global API
   - Fallback: University dissertation repositories, Google Scholar
   - Extract: Full-text PDF, metadata, keywords, abstract
   - Technology: requests, PyPDF2, pdfplumber

3. **Publication Scraper**
   - Sources: Google Scholar, JSTOR, ProQuest Political Science Database
   - Extract: Title, abstract, co-authors, citations, journal
   - Technology: scholarly library, selenium (for JavaScript rendering)

4. **Department Research Mapper**
   - Scrape: Faculty research pages, lab/center descriptions
   - Extract: Research interests, recent publications, grants
   - Build: Department research profile

### B. Phase 2: Analysis & Scoring

**1. Alignment Scoring Engine**
```python
class AlignmentScorer:
    def calculate_alignment(self, candidate: Candidate, position: HiringPosition) -> AlignmentScore:
        # Dissertation-Department Topic Alignment
        topic_alignment = self._topic_similarity(
            candidate.dissertation_keywords,
            position.department_research_areas
        )

        # Advisor-Faculty Connection
        advisor_connection = self._check_advisor_connections(
            candidate.phd_advisor,
            position.department_faculty
        )

        # Co-author Network Overlap
        network_overlap = self._network_overlap(
            candidate.co_authors,
            position.department_faculty
        )

        # Methodological Match
        method_match = self._method_alignment(
            candidate.dissertation_abstract,
            position.field_specialty
        )

        return AlignmentScore(
            topic_score=topic_alignment,
            network_score=network_overlap,
            methodology_score=method_match,
            overall_score=weighted_average([...])
        )
```

**2. Network Analysis Engine**
```python
class NetworkAnalyzer:
    def analyze_coauthorship_network(self, candidate: Candidate) -> NetworkAnalysis:
        # Build co-authorship graph
        graph = self._build_network(candidate.publications)

        # Calculate network metrics
        betweenness_centrality = nx.betweenness_centrality(graph)
        eigenvector_centrality = nx.eigenvector_centrality(graph)

        # Identify star collaborators (highly cited)
        star_collaborators = self._identify_stars(candidate.co_authors)

        # Check institutional diversity
        institution_diversity = self._institution_diversity(graph)

        return NetworkAnalysis(
            total_collaborators=len(candidate.co_authors),
            star_collaborators=star_collaborators,
            betweenness_score=betweenness_centrality,
            institution_diversity=institution_diversity
        )
```

**3. Dissertation Quality Assessor**
```python
class DissertationAssessor:
    def assess_quality(self, dissertation: Dissertation) -> QualityScore:
        # Check for awards
        awards_score = self._check_awards(dissertation)

        # Analyze citation count
        citation_score = self._citation_impact(dissertation)

        # LLM-based quality assessment
        llm_assessment = self._llm_quality_analysis(
            dissertation.abstract,
            dissertation.keywords
        )

        # Check for grants
        grant_score = self._check_research_grants(dissertation)

        return QualityScore(
            awards=awards_score,
            citations=citation_score,
            llm_quality=llm_assessment,
            grants=grant_score
        )
```

### C. Phase 3: Narrative Generation

**Multi-Perspective Assessment Framework**:

**1. Optimistic Perspective** (Best-Case Interpretation)
```
Prompt Template:
"Analyze this candidate's hire from the most optimistic perspective.
Focus on:
- Exceptional strengths and qualifications
- Perfect timing and market conditions
- Strategic advantages they bring
- How they exceeded requirements
- Future potential and trajectory"
```

**2. Pessimistic Perspective** (Critical Analysis)
```
Prompt Template:
"Analyze this candidate's hire from a critical, skeptical perspective.
Consider:
- Potential weaknesses or gaps
- Competitive disadvantages overcome
- Market conditions working against them
- Risks the department took
- Alternative explanations beyond merit"
```

**3. Pragmatic Perspective** (Balanced Assessment)
```
Prompt Template:
"Provide a balanced, realistic assessment of this hire.
Evaluate:
- Strengths AND weaknesses
- Clear evidence vs speculation
- Market realities and constraints
- Probable decision-making factors
- Reproducible success elements"
```

**4. Speculative Perspective** (Hidden Factors)
```
Prompt Template:
"Consider non-obvious factors that may have influenced this hire.
Explore:
- Personal connections and networks
- Timing and strategic positioning
- Department politics and needs
- Funding or grant implications
- Diversity initiatives or strategic priorities"
```

### D. Phase 4: Output Generation

**1. CSV Export**
```csv
Name,Institution,Department,Position,PhD_Institution,PhD_Year,Dissertation_Title,Dissertation_URL,Keywords,Publications_Count,Citation_Count,H_Index,Star_Coauthors,Alignment_Score,Awards,Key_Success_Factor_1,Key_Success_Factor_2,Key_Success_Factor_3
Jane Doe,Harvard,Government,Assistant Prof,Princeton,2023,"Political Psychology of...","https://...",["psychology","voting","behavior"],8,142,4,"John Smith (MIT), Sarah Lee (Stanford)",8.7/10,"APSA Merze Tate Award","Perfect topic alignment with dept","Strong publication record","Collaboration with dept faculty"
```

**2. Narrative Document** (Markdown)
```markdown
# Career Analysis: [Candidate Name] → [Institution]

## Position Details
- **Institution**: Harvard Kennedy School
- **Department**: Government
- **Position**: Assistant Professor (Tenure-Track)
- **Hire Date**: Fall 2024

## Candidate Profile
- **Name**: Professor Bassan-Nygate
- **PhD Institution**: Princeton University
- **PhD Year**: 2023
- **Previous Position**: Postdoctoral Research Associate, Princeton
- **Dissertation**: [Title]

## Alignment Analysis
- **Topic Alignment**: 9.2/10
- **Network Overlap**: 7.8/10
- **Methodology Match**: 8.5/10
- **Overall Alignment**: 8.5/10

## Optimistic Assessment
[Generated narrative focusing on exceptional qualifications...]

## Pessimistic Assessment
[Generated narrative examining potential weaknesses...]

## Pragmatic Assessment
[Generated balanced analysis...]

## Speculative Assessment
[Generated analysis of hidden factors...]

## Key Success Factors
1. Dissertation won APSA's prestigious Merze Tate Award
2. Perfect alignment with HKS focus on human rights and experimental methods
3. Strong publication record during doctoral studies
4. Postdoc at Princeton provided additional credentialing

## Actionable Intelligence
For candidates targeting similar positions:
- [Specific recommendations based on this case]
```

---

## IV. Integration with RED Project

### A. Database Schema Extensions

**New Tables**:

```sql
-- Career positions being tracked
CREATE TABLE career_positions (
    id TEXT PRIMARY KEY,
    institution TEXT NOT NULL,
    department TEXT,
    position_title TEXT,
    field_specialty TEXT,
    hire_date TEXT,
    job_posting_url TEXT,
    scrape_date TEXT,
    status TEXT,  -- 'active', 'analyzed', 'archived'
    metadata JSON,
    created_at TEXT,
    updated_at TEXT
);

-- Candidates hired for positions
CREATE TABLE career_candidates (
    id TEXT PRIMARY KEY,
    position_id TEXT,
    name TEXT NOT NULL,
    phd_institution TEXT,
    phd_year INTEGER,
    phd_advisor TEXT,
    dissertation_title TEXT,
    dissertation_url TEXT,
    dissertation_keywords JSON,
    publications_count INTEGER,
    citations_count INTEGER,
    h_index INTEGER,
    awards JSON,
    metadata JSON,
    created_at TEXT,
    updated_at TEXT,
    FOREIGN KEY (position_id) REFERENCES career_positions(id)
);

-- Analysis results
CREATE TABLE career_assessments (
    id TEXT PRIMARY KEY,
    candidate_id TEXT,
    alignment_score REAL,
    network_analysis JSON,
    optimistic_narrative TEXT,
    pessimistic_narrative TEXT,
    pragmatic_narrative TEXT,
    speculative_narrative TEXT,
    key_success_factors JSON,
    red_flags JSON,
    created_at TEXT,
    FOREIGN KEY (candidate_id) REFERENCES career_candidates(id)
);

-- Co-authorship networks
CREATE TABLE coauthor_networks (
    id TEXT PRIMARY KEY,
    candidate_id TEXT,
    coauthor_name TEXT,
    publication_count INTEGER,
    coauthor_institution TEXT,
    coauthor_h_index INTEGER,
    is_star_collaborator BOOLEAN,
    FOREIGN KEY (candidate_id) REFERENCES career_candidates(id)
);
```

### B. Opportunities Integration

**Mapping Career Positions to Opportunities**:

```python
class CareerOpportunityMapper:
    def create_opportunity_from_position(
        self,
        position: HiringPosition,
        analysis: HiringAssessment
    ) -> Opportunity:
        """Convert career analysis into Opportunity for tracking."""

        return Opportunity(
            title=f"{position.institution} - {position.position_title}",
            type="career_position",
            status="research",
            due_date=self._estimate_application_deadline(position),
            agency=position.institution,
            metadata={
                "field": position.field_specialty,
                "department": position.department,
                "alignment_score": analysis.alignment_score.overall_score,
                "key_factors": analysis.key_success_factors,
                "similar_hires": analysis.similar_candidates  # For pattern matching
            }
        )
```

**Use Case**: User researching political science positions can:
1. Add target institutions to Opportunities
2. Track application deadlines
3. Compare their profile against recent hires
4. Generate tailored application materials

### C. TODO List Integration

**Automated Task Generation**:

```python
class CareerTaskGenerator:
    def generate_tasks_from_analysis(
        self,
        user_profile: UserProfile,
        target_position: HiringPosition,
        analysis: HiringAssessment
    ) -> List[Task]:
        """Generate actionable tasks based on gap analysis."""

        tasks = []

        # Publication gap
        if user_profile.publications_count < analysis.avg_publications:
            tasks.append(Task(
                title="Increase publications to competitive level",
                description=f"Target: {analysis.avg_publications} publications (Current: {user_profile.publications_count})",
                priority="high",
                due_date=self._calculate_timeline(target_position.hire_date)
            ))

        # Network gap
        if not self._has_star_collaborators(user_profile):
            tasks.append(Task(
                title="Develop collaboration with highly-cited researchers",
                description=f"Identified targets: {analysis.recommended_collaborators}",
                priority="high"
            ))

        # Topic alignment gap
        if analysis.alignment_score.topic_score < 7.0:
            tasks.append(Task(
                title="Refine research focus to match target department",
                description=f"Key areas: {analysis.department_priority_areas}",
                priority="medium"
            ))

        return tasks
```

### D. Dashboard Visualization

**New UI Components** (for server.py):

```python
@app.route('/career-monster')
def career_monster_dashboard():
    """Career-monster analysis dashboard."""

    positions = db.query("""
        SELECT * FROM career_positions
        WHERE status = 'analyzed'
        ORDER BY hire_date DESC
    """)

    return render_template('career_monster/dashboard.html',
        positions=positions,
        stats=calculate_stats(positions)
    )

@app.route('/career-monster/position/<position_id>')
def position_detail(position_id):
    """Detailed analysis for specific position."""

    position = get_position(position_id)
    candidate = get_candidate(position.candidate_id)
    assessment = get_assessment(candidate.id)

    return render_template('career_monster/position_detail.html',
        position=position,
        candidate=candidate,
        assessment=assessment
    )
```

**Visualization Features**:
- Interactive network graph of co-authorship connections
- Alignment score radar chart (topic, network, methodology, publications)
- Timeline of career progression
- Comparison matrix: user profile vs successful candidates

### E. Output Directory Structure

```
outputs/
└── career-monster/
    ├── analyses/
    │   ├── political-science-2024/
    │   │   ├── harvard_bassan-nygate_2024-12-26.csv
    │   │   ├── harvard_bassan-nygate_narrative_2024-12-26.md
    │   │   ├── stanford_allen_2024-12-26.csv
    │   │   └── stanford_allen_narrative_2024-12-26.md
    │   └── summary_2024-12-26.csv
    ├── networks/
    │   ├── coauthorship_graph_2024-12-26.gexf
    │   └── institution_flow_2024-12-26.png
    └── reports/
        ├── political_science_hiring_trends_2024-12-26.html
        └── success_factors_analysis_2024-12-26.pdf
```

---

## V. User Interaction Flow

### A. Initial Configuration

**Interactive Prompts**:

```python
def configure_analysis():
    """Prompt user for analysis parameters."""

    # 1. Career field selection
    field = prompt_choice(
        "What career field would you like to analyze?",
        options=[
            "Political Science (Tenure-Track)",
            "Economics (Assistant Professor)",
            "Computer Science (Research Faculty)",
            "Law (Tenure-Track)",
            "Custom field..."
        ],
        default="Political Science (Tenure-Track)"
    )

    # 2. Position type
    position_type = prompt_choice(
        "What position level?",
        options=[
            "Assistant Professor (Tenure-Track)",
            "Postdoctoral Fellow",
            "Associate Professor",
            "Research Scientist",
            "Custom..."
        ]
    )

    # 3. Data sources
    data_sources = prompt_multichoice(
        "Where should I search for hiring data?",
        options=[
            ".edu university websites (Recommended)",
            "HigherEdJobs.com",
            "Chronicle of Higher Education",
            "Academic Jobs Online",
            "LinkedIn",
            "Custom sources..."
        ],
        defaults=[".edu university websites"]
    )

    # 4. Assessment types
    assessment_types = prompt_multichoice(
        "What types of assessments would you like?",
        options=[
            "Optimistic (Best-case interpretation)",
            "Pessimistic (Critical analysis)",
            "Pragmatic (Balanced assessment)",
            "Speculative (Hidden factors)",
            "All of the above (Recommended)"
        ],
        defaults=["All of the above"]
    )

    # 5. Verbosity
    verbosity = prompt_choice(
        "Assessment length/detail level?",
        options=[
            "Brief (1-2 paragraphs per assessment)",
            "Standard (3-5 paragraphs per assessment)",
            "Detailed (1-2 pages per assessment)",
            "Comprehensive (3+ pages per assessment)"
        ],
        default="Standard"
    )

    # 6. Target institutions (optional)
    target_institutions = prompt_list(
        "Any specific institutions to focus on? (Leave blank for all)",
        optional=True
    )

    # 7. Time range
    time_range = prompt_choice(
        "Analyze hires from which time period?",
        options=[
            "Last 6 months",
            "Last year",
            "Last 2 years",
            "Last 5 years",
            "Custom range..."
        ],
        default="Last year"
    )

    return AnalysisConfig(
        field=field,
        position_type=position_type,
        data_sources=data_sources,
        assessment_types=assessment_types,
        verbosity=verbosity,
        target_institutions=target_institutions,
        time_range=time_range
    )
```

### B. Execution Flow

```
1. User invokes skill: `/career-monster` or calls from CLI
   ↓
2. System prompts for configuration (if not provided)
   ↓
3. Web scraping phase
   - Scan .edu sites for new faculty announcements
   - Extract candidate names, positions, institutions
   - Progress indicator: "Found 23 recent hires in Political Science..."
   ↓
4. Data enrichment phase
   - For each candidate:
     - Retrieve dissertation from ProQuest
     - Scrape Google Scholar for publications
     - Map co-authorship network
     - Extract department research profile
   - Progress: "Analyzing candidate 5/23: Jane Doe (Harvard)..."
   ↓
5. Analysis phase
   - Calculate alignment scores
   - Assess dissertation quality
   - Analyze co-authorship networks
   - Progress: "Calculating alignment scores..."
   ↓
6. Narrative generation phase
   - Generate 4 perspectives per candidate (if configured)
   - Use Ollama with custom prompts
   - Progress: "Generating assessments for Jane Doe..."
   ↓
7. Output generation
   - Create CSV summary table
   - Generate narrative documents
   - Export to outputs/career-monster/
   - Update database
   ↓
8. Integration with RED
   - Optionally create Opportunities for target positions
   - Generate TODO tasks based on gap analysis
   - Display results in web UI
   ↓
9. Present results to user
   - Summary statistics
   - Links to generated files
   - Key insights
```

### C. Output Presentation

```
✅ CAREER ANALYSIS COMPLETE

Analyzed: 23 recent Political Science hires (2024)
Institutions: Harvard (2), Stanford (1), MIT (0), Princeton (3), Yale (2), ...

📊 Summary Statistics:
  Average publications: 4.3
  Average citations: 287
  Top PhD institutions: Princeton (5), Harvard (4), Berkeley (3)
  Average alignment score: 7.8/10

📁 Generated Files:
  CSV Summary: outputs/career-monster/analyses/political-science-2024/summary_2024-12-26.csv
  Individual Analyses: 23 narrative documents
  Network Graph: outputs/career-monster/networks/coauthorship_graph_2024-12-26.gexf
  Trend Report: outputs/career-monster/reports/political_science_hiring_trends_2024-12-26.html

🎯 Key Success Factors Identified:
  1. PhD from top-5 institution (87% of hires)
  2. 3+ peer-reviewed publications (74% of hires)
  3. Collaboration with star researchers (61% of hires)
  4. Topic alignment with department (96% of hires)
  5. Postdoc at prestigious institution (52% of hires)

💡 Recommendations for users:
  - Focus on building co-authorship network with highly-cited researchers
  - Target 4-5 publications before job market
  - Ensure dissertation aligns with target department research areas
  - Consider postdoc at top institution if PhD from outside top-10

🔗 Integration:
  - Created 5 opportunities in RED for target positions
  - Generated 8 TODO tasks based on gap analysis
  - View full analysis: http://localhost:9090/career-monster
```

---

## VI. Technical Considerations & Challenges

### A. Web Scraping Challenges

**Challenge 1: Dynamic Content**
- Many .edu sites use JavaScript frameworks (React, Angular)
- **Solution**: Use Playwright for full browser automation
- **Fallback**: Selenium for older sites

**Challenge 2: Rate Limiting**
- Aggressive scraping can trigger blocks
- **Solution**: Implement polite scraping (delays, user-agent rotation)
- **Implementation**: respect robots.txt, 2-3 second delays between requests

**Challenge 3: Inconsistent Formats**
- Each university structures faculty pages differently
- **Solution**: Template-based extraction with fallback to LLM parsing
- **Implementation**: Define extraction templates per institution, use Ollama to extract structured data from unstructured text

### B. Dissertation Access Challenges

**Challenge 1: ProQuest Paywall**
- Full-text access requires institutional subscription
- **Solution**:
  - Use ProQuest API with library credentials
  - Fallback to university repositories (often open access)
  - Extract metadata even if full-text unavailable

**Challenge 2: OCR Quality**
- Older dissertations may have poor OCR
- **Solution**: Use improved OCR tools (Tesseract 5.0, cloud OCR APIs)

**Challenge 3: File Size**
- Dissertations can be 100+ MB PDFs
- **Solution**: Extract only relevant sections (abstract, introduction, conclusion, bibliography)

### C. Analysis Challenges

**Challenge 1: Name Disambiguation**
- Common names create confusion in publication matching
- **Solution**: Use ORCID IDs, institutional affiliations, co-author patterns

**Challenge 2: Network Construction**
- Building complete co-authorship graph is computationally expensive
- **Solution**: Limit to 2-degree network (direct collaborators + their collaborators)

**Challenge 3: Topic Alignment Scoring**
- Subjective assessment of alignment
- **Solution**: Hybrid approach:
  - Keyword matching (TF-IDF, cosine similarity)
  - LLM-based semantic similarity
  - Human validation on sample for calibration

### D. Privacy & Ethics Considerations

**Public Data Only**:
- All data sources must be publicly accessible
- No scraping of password-protected content
- Respect robots.txt and terms of service

**Anonymization Options**:
- Allow users to generate reports without candidate names
- Focus on patterns rather than individuals

**Disclosure**:
- Clearly state: "Analysis based on publicly available information"
- Note limitations: "Correlation does not imply causation"
- Disclaimer: "This tool provides research assistance, not hiring predictions"

---

## VII. Implementation Phases

### Phase 1: MVP (Minimum Viable Product) - 2 weeks

**Scope**:
- Web scraper for 5 major political science departments
- Dissertation metadata retrieval (ProQuest API)
- Basic alignment scoring (keyword matching)
- Single narrative generation (pragmatic only)
- CSV export only

**Deliverables**:
- Functional scraper for Harvard, Stanford, Princeton, Yale, MIT
- Database schema implemented
- Basic CLI tool: `career-monster analyze --field "political science" --year 2024`
- CSV output with 10-15 analyzed positions

**Success Criteria**:
- Successfully scrape and analyze 15+ recent hires
- Generate meaningful alignment scores
- Produce usable CSV output

### Phase 2: Enhanced Analysis - 2 weeks

**Scope**:
- Expand to 20+ universities
- Full dissertation text retrieval
- Co-authorship network construction
- Google Scholar integration
- All 4 narrative perspectives
- Markdown narrative documents

**Deliverables**:
- Extended university coverage
- Network analysis module
- Publication scraper
- Multi-perspective narrative generation
- Markdown report templates

**Success Criteria**:
- Analyze 50+ positions across 20 institutions
- Generate complete co-authorship networks
- Produce 4 distinct, insightful narratives per hire

### Phase 3: RED Integration - 1 week

**Scope**:
- Database integration with opportunities.db
- Opportunity creation from positions
- TODO task generation
- Web UI dashboard
- Visualization (network graphs, alignment charts)

**Deliverables**:
- Integrated database tables
- Web routes for career-monster
- Dashboard UI
- Interactive visualizations

**Success Criteria**:
- Seamless integration with existing RED workflow
- Functional web dashboard
- Automatic opportunity and task creation

### Phase 4: Polish & Enhancement - 1 week

**Scope**:
- User configuration prompts
- Better error handling
- Performance optimization
- Documentation
- Example workflows

**Deliverables**:
- Interactive configuration system
- Comprehensive error handling
- Optimized scraping pipeline
- User documentation
- Video tutorials

**Success Criteria**:
- Skill usable by non-technical users
- Robust error handling
- Complete documentation
- <5 minute end-to-end analysis

**Total Timeline**: 6 weeks for full implementation

---

## VIII. Success Metrics

### A. Technical Metrics

- **Scraping Success Rate**: >90% of target .edu sites successfully scraped
- **Dissertation Retrieval Rate**: >80% of dissertations retrieved (metadata or full-text)
- **Publication Match Rate**: >85% of publications correctly attributed
- **Processing Speed**: <30 seconds per candidate for basic analysis
- **Network Construction**: <2 minutes for 2-degree network

### B. Quality Metrics

- **Alignment Score Validity**: Correlation with actual hiring outcomes >0.7
- **Narrative Quality**: LLM-generated narratives deemed "insightful" by users (survey)
- **Actionability**: >70% of generated TODO tasks considered useful by users

### C. User Adoption Metrics

- **Skill Usage**: >10 analysis runs per month
- **Integration**: >5 opportunities created from career-monster data per month
- **User Satisfaction**: >4/5 rating on usefulness

---

## IX. Risk Mitigation

### Risk 1: Web Scraping Blocks
**Likelihood**: Medium
**Impact**: High
**Mitigation**:
- Implement polite scraping (delays, user-agent rotation)
- Use multiple data sources (not just .edu sites)
- Build manual data entry as fallback

### Risk 2: ProQuest API Changes/Costs
**Likelihood**: Low
**Impact**: High
**Mitigation**:
- Use multiple dissertation sources (university repositories)
- Gracefully degrade to metadata-only if full-text unavailable
- Explore alternative APIs (Semantic Scholar, CORE)

### Risk 3: LLM Hallucination in Narratives
**Likelihood**: Medium
**Impact**: Medium
**Mitigation**:
- Ground all narratives in factual data
- Include citations/references in narratives
- Add disclaimer about speculative nature
- User review step before finalizing

### Risk 4: Privacy Concerns
**Likelihood**: Low
**Impact**: High
**Mitigation**:
- Only use publicly available data
- Provide anonymization options
- Clear disclosure in documentation
- Option to exclude specific individuals

### Risk 5: Skill Complexity Overwhelms Users
**Likelihood**: Medium
**Impact**: Medium
**Mitigation**:
- Provide sensible defaults
- Interactive configuration with help text
- Example workflows and tutorials
- Simplified mode for quick analysis

---

## X. Alternative Approaches Considered

### Approach A: Fully Manual Curation
**Description**: User provides all hiring data manually
**Pros**: No scraping complexity, perfect data quality
**Cons**: Not scalable, defeats purpose of automation
**Decision**: Rejected - automation is core value proposition

### Approach B: Focus Only on Publications
**Description**: Skip dissertation analysis, focus on publication metrics
**Pros**: Easier data access, faster processing
**Cons**: Misses critical signal (dissertation quality/alignment)
**Decision**: Rejected - dissertation is central to PhD hiring

### Approach C: Use Existing Academic Databases
**Description**: Rely solely on APIs (ORCID, Semantic Scholar)
**Pros**: No scraping needed, structured data
**Cons**: Incomplete coverage, missing institutional context
**Decision**: Hybrid - use APIs where available, scrape when necessary

### Approach D: Single "Overall Score" Instead of Narratives
**Description**: Provide numerical hiring prediction score
**Pros**: Simpler, faster, quantitative
**Cons**: Lacks nuance, not actionable, feels "black box"
**Decision**: Rejected - narratives provide context and actionability

---

## XI. Future Enhancements (Post-MVP)

### Enhancement 1: Predictive Modeling
- Train ML model on historical hiring data
- Predict hiring probability for user profile
- Identify highest-ROI improvements

### Enhancement 2: Real-Time Monitoring
- Monitor job postings in real-time
- Alert users to new positions matching their profile
- Track application deadlines

### Enhancement 3: Application Materials Generator
- Generate tailored cover letters based on alignment analysis
- Suggest research statement themes
- Highlight relevant publications for each position

### Enhancement 4: Network Recommendations
- Suggest strategic collaborations
- Identify conferences to attend
- Recommend scholars to connect with

### Enhancement 5: Longitudinal Tracking
- Track career progression over time
- Identify trajectory patterns
- Predict tenure outcomes

### Enhancement 6: Multi-Field Support
- Expand beyond political science
- Support STEM fields
- Support industry research positions

---

## XII. Documentation Requirements

### User Documentation
1. **SKILL.md**: Skill description, quick start, examples
2. **USER_GUIDE.md**: Comprehensive usage guide
3. **FAQ.md**: Common questions and answers
4. **TUTORIALS.md**: Step-by-step walkthroughs
5. **API_REFERENCE.md**: For programmatic access

### Developer Documentation
1. **ARCHITECTURE.md**: System design and components
2. **DATA_SOURCES.md**: Where data comes from, how to access
3. **ALGORITHMS.md**: Scoring, matching, analysis logic
4. **TESTING.md**: How to run tests, add new tests
5. **DEPLOYMENT.md**: How to deploy and configure

### Research Documentation
1. **ACADEMIC_HIRING_RESEARCH.md**: Literature review
2. **SUCCESS_FACTORS.md**: Evidence-based hiring predictors
3. **VALIDATION_STUDY.md**: How we validated our approach
4. **CASE_STUDIES.md**: Detailed examples with analysis

---

## XIII. Cost Considerations

### Development Costs
- Developer time: 6 weeks × 40 hours = 240 hours
- LLM API costs (Ollama): $0 (local deployment)
- ProQuest API: Likely included in university library subscription
- Hosting: Minimal (part of existing RED infrastructure)

### Operational Costs
- Compute: Negligible (local processing)
- Storage: <1GB per 100 analyses
- Bandwidth: <100MB per analysis run
- LLM inference: Local Ollama (free)

**Total Estimated Cost**: Primarily developer time; ongoing operational costs negligible

---

## XIV. Conclusion & Recommendation

### Summary

The career-monster skill addresses a real need for candidates in highly selective career markets. By automating the analysis of successful hires, it provides:

1. **Data-Driven Insights**: Evidence-based understanding of success factors
2. **Actionable Intelligence**: Specific gaps and recommendations
3. **Strategic Advantage**: Information asymmetry reduction
4. **Time Savings**: Automated research vs manual investigation

### Key Strengths

- **Evidence-Based**: Grounded in academic research on hiring
- **Comprehensive**: Analyzes multiple dimensions (publications, networks, alignment, quality)
- **Actionable**: Generates specific tasks and recommendations
- **Integrated**: Fits naturally into RED's opportunity management workflow
- **Scalable**: Can expand to other fields and career types

### Potential Concerns

- **Complexity**: Significant technical implementation
- **Data Access**: Some data sources may be restricted
- **Ethical**: Could reinforce existing prestige hierarchies
- **Causation**: Correlation ≠ causation (need to communicate this clearly)

### Recommendation

**PROCEED WITH IMPLEMENTATION**

This skill is:
- ✅ Technically feasible
- ✅ Valuable to users
- ✅ Well-integrated with RED
- ✅ Ethically defensible (public data, clear disclaimers)
- ✅ Scalable and maintainable

**Suggested Approach**:
1. Implement Phase 1 MVP (2 weeks) to validate approach
2. User testing and feedback
3. Iterate based on feedback
4. Proceed to Phases 2-4 if MVP successful

**Expected Impact**:
- Help users understand competitive landscape
- Identify strategic improvements to candidacy
- Increase success rate in highly selective markets
- Demonstrate RED's capabilities for complex career intelligence

---

**Next Steps**: Review this plan, discuss approach, and proceed to implementation if approved.

**Sources**:
- [Harvard Kennedy School New Faculty](https://www.hks.harvard.edu/admissions-blog/hks-welcomes-new-faculty-members)
- [Academic Hiring Success Factors - APSA](https://apsanet.org/wp-content/uploads/2024/08/GS1-Chapter-34.pdf)
- [Where You Earn Your PhD Matters](https://www.cambridge.org/core/journals/ps-political-science-and-politics/article/where-you-earn-your-phd-matters/09DCA7FDED5D830D487FF4029F338944)
- [80% of Faculty from 20% of Institutions](https://www.insidehighered.com/news/2022/09/23/new-study-finds-80-faculty-trained-20-institutions)
- [Co-authorship Networks Predict Faculty Placement](https://arxiv.org/html/2507.14696)
- [Early Coauthorship Predicts Success](https://www.nature.com/articles/s41467-019-13130-4)
- [ProQuest Dissertations & Theses Global](https://about.proquest.com/en/products-services/pqdtglobal/)
