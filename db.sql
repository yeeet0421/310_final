-- Database schema for Resume Analyzer

-- Drop tables if they exist
DROP TABLE IF EXISTS analysis_reports;
DROP TABLE IF EXISTS jobs;

-- Create jobs table to track resume analysis jobs
CREATE TABLE jobs (
    job_id SERIAL PRIMARY KEY,
    datafilekey VARCHAR(255) NOT NULL UNIQUE,  -- S3 key for the uploaded resume
    resultsfilekey VARCHAR(255),               -- S3 key for the analysis results
    status VARCHAR(100) NOT NULL,              -- Job status (new, processing, completed, error)
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    job_description TEXT NOT NULL              -- The job description text
);

-- Create analysis_reports table to store analysis results
CREATE TABLE analysis_reports (
    analysis_id VARCHAR(36) PRIMARY KEY,
    resume_name VARCHAR(255) NOT NULL,
    job_description TEXT NOT NULL,
    results TEXT NOT NULL,                    -- JSON string containing analysis results
    match_score FLOAT NOT NULL,
    created_at TIMESTAMP NOT NULL
);

-- Create indexes
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);
CREATE INDEX idx_analysis_reports_created_at ON analysis_reports(created_at);

-- Create trigger to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_jobs_modtime
BEFORE UPDATE ON jobs
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();