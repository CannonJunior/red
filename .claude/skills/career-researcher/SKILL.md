---
name: career-researcher
description: "Automated web research for competitive career positions. Searches .edu faculty pages to identify recent hires, then gathers complete profile data (PhD institution, publications, citations, dissertation details) through web searches. Integrates with career-monster skill to enable fully automated analysis from general user prompts. Use when user requests research on hiring patterns without providing specific candidate data."
---

# Career-Researcher: Automated Academic Hiring Research

## Overview

Career-Researcher automates the data collection process for competitive career position analysis. Instead of requiring manual entry of candidate and position data, this skill searches the web to find recent hires and automatically gathers all required information.

**Primary Use Case**: Automated research of academic hiring patterns

**Key Capabilities**:
- Search .edu faculty pages for recent hires
- Extract position and candidate information from faculty profiles
- Research PhD backgrounds via institutional databases
- Find publication records through Google Scholar
- Gather dissertation information from ProQuest/library catalogs
- Auto-populate career-monster database with research findings

## Quick Start

### Via AI Agent (Recommended)

Use an agent configured with both `career-researcher` and `career-monster` skills:

```
User: "Research recent political science hires at top universities from 2023-2024"

Agent: [Uses career-researcher to find hires]
       [Uses career-monster to analyze each hire]
       [Returns comprehensive analysis]
```

### API Usage (Programmatic)

```python
from career_researcher import (
    FacultyPageSearcher,
    AcademicProfileEnricher,
    CareerResearchPipeline
)

# Initialize pipeline
pipeline = CareerResearchPipeline(
    database_path="opportunities.db"
)

# Run research
results = pipeline.research_hires(
    domains=[".edu"],
    departments=["political science", "government"],
    date_range=("2023-01-01", "2024-12-31"),
    university_tier="R1",  # Optional: filter by Carnegie classification
    max_results=50
)

print(f"Found {len(results.positions)} positions")
print(f"Enriched {len(results.candidates)} candidate profiles")
```

## Research Pipeline

### Phase 1: Faculty Page Discovery
**Goal**: Find recent faculty hires on .edu websites

**Search Strategy**:
- Google site search: `site:.edu "new faculty" OR "recent hire" [department]`
- Target pages: "People", "Faculty", "New Hires", "Join Us"
- Parse HTML for hire announcements and faculty listings

**Extracted Data**:
- Institution name
- Department
- Hired individual's name
- Position title
- Hire date (if available)

### Phase 2: Profile Enrichment
**Goal**: Gather complete academic profile for each hire

**Data Sources**:
1. **University Profile Pages**
   - Scrape individual faculty profile pages
   - Extract: research interests, education history, contact info

2. **Google Scholar**
   - Search by name + institution
   - Extract: publication count, citation count, co-authors
   - Identify h-index and recent publications

3. **CV/Personal Websites**
   - Search for candidate's personal website or CV
   - Extract: dissertation title, PhD institution, awards

4. **ProQuest/University Libraries**
   - Search dissertation databases
   - Extract: dissertation abstract, keywords, committee members

### Phase 3: Data Validation
**Goal**: Ensure data quality before populating career-monster

**Validation Checks**:
- Name disambiguation (multiple people with same name)
- Date consistency (PhD year < hire year)
- Institution matching (verify PhD institution exists)
- Publication count sanity checks

### Phase 4: Career-Monster Integration
**Goal**: Automatically create position and candidate records

**Process**:
1. Create `HiringPosition` object from extracted data
2. Create `Candidate` object with enriched profile
3. Store in `opportunities.db` via CareerDatabase
4. Trigger career-monster analysis (optional)

## Configuration

### Search Filters

**University Tiers** (Carnegie Classification):
- R1: Very high research activity
- R2: High research activity
- D/PU: Doctoral/Professional universities
- ALL: No filter

**Date Ranges**:
- Specify as tuples: `("2023-01-01", "2024-12-31")`
- Use relative: "last_year", "last_2_years"

**Departments**:
```python
SUPPORTED_DEPARTMENTS = [
    "political science",
    "government",
    "economics",
    "sociology",
    "computer science",
    "psychology"
]
```

### Rate Limiting

**Important**: Respects robots.txt and implements polite scraping

```python
config = {
    "requests_per_domain": 10,  # Max requests per domain per minute
    "delay_between_requests": 2,  # Seconds between requests
    "timeout": 10,  # Request timeout in seconds
    "max_retries": 3
}
```

## API Endpoints

When integrated with main application:

```
POST /api/career/research          # Start research job
GET  /api/career/research/:job_id  # Check research status
GET  /api/career/research/results  # Get research results
```

**Example Request**:
```json
{
  "query": "recent political science hires",
  "filters": {
    "university_tier": "R1",
    "date_range": ["2023-01-01", "2024-12-31"],
    "departments": ["political science", "government"]
  },
  "auto_analyze": true
}
```

**Example Response**:
```json
{
  "job_id": "research_abc123",
  "status": "completed",
  "results": {
    "positions_found": 23,
    "candidates_enriched": 23,
    "analysis_completed": 23,
    "failed": 0
  },
  "data": [
    {
      "position_id": "uuid-1",
      "candidate_id": "uuid-2",
      "assessment_id": "uuid-3",
      "institution": "Harvard University",
      "candidate_name": "Jane Doe",
      "overall_score": 8.2
    }
  ]
}
```

## Web Scraping Components

### FacultyPageSearcher

**Responsibilities**:
- Execute Google search queries
- Parse search results for .edu faculty pages
- Extract hire announcements

**Key Methods**:
```python
searcher = FacultyPageSearcher()

# Find faculty pages
pages = searcher.search_faculty_pages(
    department="political science",
    keywords=["new hire", "recent faculty"],
    max_results=100
)

# Parse hire announcements
hires = searcher.extract_hires(pages)
```

### AcademicProfileEnricher

**Responsibilities**:
- Search Google Scholar for publications
- Scrape CV and personal websites
- Query dissertation databases

**Key Methods**:
```python
enricher = AcademicProfileEnricher()

# Enrich candidate profile
profile = enricher.enrich_profile(
    name="Jane Doe",
    current_institution="Harvard University",
    department="Government"
)

# Returns: PhD info, publications, citations, co-authors, dissertation
```

### HTMLParser Utilities

**Supported Patterns**:
- Faculty directory tables
- Individual profile pages
- Hire announcement pages
- CV/resume documents (PDF, HTML, DOCX)

## Integration with Career-Monster

Career-researcher outputs data in the exact format expected by career-monster:

```python
# career-researcher output
research_result = {
    "position": HiringPosition(...),
    "candidate": Candidate(...)
}

# Automatically feeds into career-monster
from career_monster import CareerDatabase, AlignmentScorer, NarrativeGenerator

db = CareerDatabase("opportunities.db")
position_id = db.create_position(research_result["position"])
candidate_id = db.create_candidate(research_result["candidate"], position_id)

# Run analysis
scorer = AlignmentScorer()
alignment = scorer.calculate_alignment(
    research_result["candidate"],
    research_result["position"]
)
```

## Example Use Cases

### 1. Research Recent Hires at Peer Institutions

```
User: "Find all political science hires at R1 universities in 2024"

Agent Response:
- Searches 50 R1 university political science departments
- Finds 23 new faculty hires
- Enriches each profile with PhD info, publications
- Runs career-monster analysis on all 23
- Returns summary: "Found 23 hires. Average alignment score: 7.8/10.
  Top factors: PhD from top-5 institution (87%), 4+ publications (91%)"
```

### 2. Track Hiring Patterns Over Time

```
User: "Compare political science hires from 2022 vs 2024"

Agent Response:
- Researches hires from both years
- Analyzes publication requirements over time
- Identifies changing trends: "2024 hires averaged 6.2 publications
  vs 4.8 in 2022. Citation counts increased 35%."
```

### 3. Department-Specific Analysis

```
User: "What types of candidates did Harvard Government hire in the last 3 years?"

Agent Response:
- Focuses search on Harvard Government department
- Finds 8 hires from 2021-2024
- Analyzes common patterns: "All 8 from top-10 PhD programs.
  75% focus on comparative politics. Average 5.5 publications at hire."
```

## Ethical Considerations

**What Career-Researcher Does** ✅:
- Collects publicly available information only
- Respects robots.txt and rate limits
- Uses data for research and analysis purposes
- Provides transparency about data sources

**What Career-Researcher Does NOT Do** ❌:
- Access password-protected or paywalled content
- Scrape personal email or contact information
- Store sensitive biographical data
- Bypass access restrictions or CAPTCHAs

**Data Collection Policy**:
> This skill collects only publicly available information from .edu websites, Google Scholar, and academic databases. All data is used solely for career pattern analysis and is stored locally. We respect robots.txt directives and implement polite scraping practices with rate limiting.

## Limitations

**Current Limitations**:
1. **Language**: English-language pages only
2. **Geography**: Primarily US-based .edu institutions
3. **Fields**: Best results for social sciences and humanities
4. **Hire Dates**: May miss exact hire dates if not publicly posted
5. **Dissertation Data**: Not all dissertations are publicly available

**Accuracy Notes**:
- Name disambiguation may fail for common names
- Publication counts depend on Google Scholar indexing
- Some older hires may have limited online presence
- Private institutions may have restricted faculty pages

## Troubleshooting

**Issue**: No results found for department
**Solution**: Try alternative department names (e.g., "Government" vs "Political Science")

**Issue**: Enrichment fails for candidate
**Solution**: Check if candidate has Google Scholar profile or public CV

**Issue**: Rate limit errors
**Solution**: Reduce requests_per_domain or increase delay_between_requests

**Issue**: Parsing errors on faculty pages
**Solution**: Some universities use non-standard HTML structures. Add custom parser for specific domains.

## Technical Architecture

**Backend**: Python (requests, BeautifulSoup4, scholarly)
**Web Scraping**: Respectful crawling with rate limiting
**Search**: Google Custom Search API (free tier: 100 queries/day)
**Database**: Shared SQLite database with career-monster
**Integration**: Designed to work with Ollama agents via skill system

## Support

For issues or enhancements:
- Check documentation in `docs/career-researcher/`
- Review implementation in `.claude/skills/career-researcher/scripts/`
- Test with example prompts in `.claude/skills/career-researcher/examples/`

---

**Skill Version**: 1.0.0 (MVP)
**Last Updated**: 2025-12-26
**Maintainer**: RED Project Team
