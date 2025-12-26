-- Career Monster Schema Migration
-- Created: 2025-12-26
-- Phase 1: Core tables for analyzing highly selective career positions

-- ============================================================
-- Career Positions: Hiring positions being tracked
-- ============================================================
CREATE TABLE IF NOT EXISTS career_positions (
    -- Identity
    id TEXT PRIMARY KEY,
    opportunity_id TEXT,  -- Optional link to opportunities table

    -- Position Details
    institution TEXT NOT NULL,
    department TEXT NOT NULL,
    position_title TEXT NOT NULL,
    field_specialty TEXT NOT NULL,
    hire_date TEXT NOT NULL,  -- YYYY-MM-DD format

    -- Job Posting Info
    job_posting_url TEXT,
    posting_description TEXT,
    department_research_areas TEXT,  -- JSON array of research areas

    -- Status
    status TEXT DEFAULT 'pending',  -- pending, analyzing, completed

    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE SET NULL
);

-- ============================================================
-- Career Candidates: Hired individuals being analyzed
-- ============================================================
CREATE TABLE IF NOT EXISTS career_candidates (
    -- Identity
    id TEXT PRIMARY KEY,
    position_id TEXT NOT NULL,

    -- Basic Info
    name TEXT NOT NULL,
    current_position TEXT,

    -- PhD Information
    phd_institution TEXT NOT NULL,
    phd_year INTEGER NOT NULL,
    phd_advisor TEXT,

    -- Dissertation
    dissertation_title TEXT NOT NULL,
    dissertation_url TEXT,
    dissertation_keywords TEXT,  -- JSON array
    dissertation_abstract TEXT,

    -- Publications
    publications_data TEXT,  -- JSON array of Publication objects
    publications_count INTEGER DEFAULT 0,

    -- Network
    co_authors TEXT,  -- JSON array of co-author names

    -- Metrics
    awards_data TEXT,  -- JSON array of Award objects
    citations_count INTEGER DEFAULT 0,
    h_index INTEGER,

    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (position_id) REFERENCES career_positions(id) ON DELETE CASCADE
);

-- ============================================================
-- Career Assessments: Analysis results for each hire
-- ============================================================
CREATE TABLE IF NOT EXISTS career_assessments (
    -- Identity
    id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,
    position_id TEXT NOT NULL,

    -- Alignment Scores (0-10 scale)
    topic_alignment REAL NOT NULL,
    network_overlap REAL NOT NULL,
    methodology_match REAL NOT NULL,
    publication_strength REAL NOT NULL,
    overall_score REAL NOT NULL,

    -- Network Analysis
    total_collaborators INTEGER DEFAULT 0,
    star_collaborators TEXT,  -- JSON array
    institutional_diversity INTEGER DEFAULT 0,
    network_quality_score REAL DEFAULT 5.0,

    -- Confidence Metrics (0-1 scale)
    confidence_overall REAL NOT NULL,
    confidence_data_quality REAL NOT NULL,
    confidence_analysis_robustness REAL NOT NULL,

    -- Narratives (4 perspectives)
    optimistic_narrative TEXT NOT NULL,
    pessimistic_narrative TEXT NOT NULL,
    pragmatic_narrative TEXT NOT NULL,
    speculative_narrative TEXT NOT NULL,

    -- Key Insights
    success_factors TEXT,  -- JSON array
    red_flags TEXT,  -- JSON array

    -- Processing Info
    analysis_model TEXT DEFAULT 'qwen2.5:3b',
    analysis_verbosity TEXT DEFAULT 'standard',
    processing_time_seconds REAL,

    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (candidate_id) REFERENCES career_candidates(id) ON DELETE CASCADE,
    FOREIGN KEY (position_id) REFERENCES career_positions(id) ON DELETE CASCADE
);

-- ============================================================
-- Coauthor Networks: Track collaboration networks
-- ============================================================
CREATE TABLE IF NOT EXISTS coauthor_networks (
    -- Identity
    id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,

    -- Collaborator Info
    coauthor_name TEXT NOT NULL,
    coauthor_institution TEXT,

    -- Collaboration Metrics
    joint_publications_count INTEGER DEFAULT 1,
    first_collaboration_year INTEGER,
    latest_collaboration_year INTEGER,

    -- Network Position
    is_star_collaborator BOOLEAN DEFAULT FALSE,  -- Highly cited co-author
    estimated_citations INTEGER DEFAULT 0,

    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (candidate_id) REFERENCES career_candidates(id) ON DELETE CASCADE
);

-- ============================================================
-- Indexes for Performance
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_career_positions_institution ON career_positions(institution);
CREATE INDEX IF NOT EXISTS idx_career_positions_field ON career_positions(field_specialty);
CREATE INDEX IF NOT EXISTS idx_career_positions_hire_date ON career_positions(hire_date);
CREATE INDEX IF NOT EXISTS idx_career_positions_status ON career_positions(status);
CREATE INDEX IF NOT EXISTS idx_career_positions_opportunity ON career_positions(opportunity_id);

CREATE INDEX IF NOT EXISTS idx_career_candidates_position ON career_candidates(position_id);
CREATE INDEX IF NOT EXISTS idx_career_candidates_phd_institution ON career_candidates(phd_institution);
CREATE INDEX IF NOT EXISTS idx_career_candidates_phd_year ON career_candidates(phd_year);

CREATE INDEX IF NOT EXISTS idx_career_assessments_candidate ON career_assessments(candidate_id);
CREATE INDEX IF NOT EXISTS idx_career_assessments_position ON career_assessments(position_id);
CREATE INDEX IF NOT EXISTS idx_career_assessments_overall_score ON career_assessments(overall_score);

CREATE INDEX IF NOT EXISTS idx_coauthor_networks_candidate ON coauthor_networks(candidate_id);
CREATE INDEX IF NOT EXISTS idx_coauthor_networks_is_star ON coauthor_networks(is_star_collaborator);

-- ============================================================
-- Example Usage (commented out):
-- ============================================================
-- INSERT INTO career_positions (id, institution, department, position_title, field_specialty, hire_date)
-- VALUES ('pos_001', 'Harvard University', 'Government', 'Assistant Professor', 'Political Science', '2024-07-01');
--
-- INSERT INTO career_candidates (id, position_id, name, phd_institution, phd_year, dissertation_title)
-- VALUES ('cand_001', 'pos_001', 'Jane Doe', 'Stanford University', 2023, 'Democratic Accountability in Hybrid Regimes');
--
-- INSERT INTO career_assessments (id, candidate_id, position_id, topic_alignment, network_overlap, ...)
-- VALUES ('assess_001', 'cand_001', 'pos_001', 8.5, 7.2, ...);
