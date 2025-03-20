# Job Match Resume Analyzer

A cloud-based solution that helps job seekers optimize their resumes for specific job descriptions by identifying missing keywords and providing improvement recommendations.

## Project Architecture

### Backend API (AWS Lambda + API Gateway)
- Processes resume uploads and job descriptions
- Extracts text using AWS Textract
- Analyzes content using AWS Comprehend for entity extraction
- Uses AWS Bedrock with Llama 3.1 405B for resume-job matching
- Returns detailed match analysis and recommendations

### Main Command Line Interface Functions
- Upload resumes and job descriptions
- Download analysis results

### Analysis Services
- **AWS Textract:** Extract structured text from single page PDF resumes
- **AWS Comprehend:** Extract entities and identify keywords
- **AWS Bedrock:** Perform AI-powered resume-job matching with Llama 3.1 405B


### Data Storage
- **Amazon S3:** Store uploaded resumes and analysis results
- **Amazon RDS Aurora Serverless:** Store analysis reports and metadata

## Setup and Deployment

### Prerequisites
- AWS Account with appropriate permissions
- Python 3.9+ installed
- Access to Amazon Bedrock Llama 3.1 405B Instruct model

### Required IAM Permissions
The following permissions are needed for this project:
- S3 access (for storing resumes and analysis results)
- RDS access (for database operations)
- Lambda execution permissions
- API Gateway access
- AWS Textract access (for PDF processing)
- AWS Comprehend access (for entity extraction)
- AWS Bedrock access (for AI resume matching)


### Manual Infrastructure Setup

1. **S3 Bucket Setup:**
   - Create an S3 bucket to store resumes and analysis results
   - Note the bucket name for configuration

2. **Database Setup:**
   - Create a PostgreSQL database in Amazon RDS
   - The database should include the following tables:
     - `users`: Stores user information (`userid`, `username`, `pwdhash`)
     - `jobs`: Tracks analysis jobs (`jobid`, `userid`, `status`, `originaldatafile`, `datafilekey`, `resultsfilekey`, `analyzefilekey`)
   - The provided `db.sql` file can be used to create the database tables
   - Record the database endpoint, port, username, and password

3. **Lambda Functions:**
   - Create lambda functions using the provided zip files:
     - `final_download.zip`: For downloading analysis results
     - `final_compute.zip`: For processing resumes into structured resumes
     - `final_analyze.zip`: Returns resume analysis results
     - `proj03_jobs.zip`: Returns all the jobs from the database

# API Gateway Endpoints

The API Gateway should be configured with the following endpoints:

## User Management
- **GET /users**
  - Returns a list of all users in the system
  - No parameters required

## Job Management
- **GET /jobs**
  - Returns a list of all jobs in the system
  - No parameters required

## Database Management
- **DELETE /reset**
  - Resets the database to its initial state
  - Use with caution as this deletes all user data

## PDF Upload
- **POST /pdf/{userid}**
  - Uploads a resume PDF for a specific user
  - Path Parameter: userid (integer)
  - Body: JSON object containing:
    - filename: Original filename
    - data: Base64-encoded PDF content
    - job_title (optional): Title of the job being applied for
    - job_description (optional): Description of the job
    - job_required_skills (optional): Required skills for the job
  - Returns: jobid (integer)

## Results Retrieval
- **GET /results/{jobid}/{job_title}/{job_description}/{job_required_skills}**
  - Retrieves the analysis results for a specific job
  - Path Parameter: 
    - jobid (integer)
    - job_title (string)
    - job_description (string)
    - job_required_skills (string)
  - Returns:
    - If job is complete: Resume matching result (hire, interview, or reject, etc.), Full analysis file name, Resume structured by Amazon Comprehend file name
    ```
    Resume processed successfully
    Resume matching result: reject
    Full analysis in file: resume_analysis.json
    Resume structed by Amazon Comprehend in file: resume_structured.json
    ```
    - If job is still processing: Status message (processing, error, uploaded, etc.)
    - If job doesn't exist: Error message

5. **Configuration:**
   - Modify configuration files into the following sections:
     ```ini
     [s3]
     bucket_name = your-bucket-name
     region_name = your-region
     
     [rds]
     endpoint = your-db-endpoint
     port_number = 5432
     user_name = your-username
     user_pwd = your-password
     db_name = your-db-name

     [s3readwrite]
     region_name = your-region
     aws_access_key_id = your-access-key
     aws_secret_access_key = your-secret-key
     ```

### Client Setup Usage

The Resume Analyzer  client requires a configuration file to connect to the AWS services. A sample configuration file named `resumeapp-client-config.ini` should be created with the following format:

```ini
[client]
webservice = https://your-api-gateway-url
```

The client will automatically read this configuration file to establish connection with the backend services.

## Using the Resume Analyzer

The Resume Analyzer comes with a command-line interface (CLI) client that provides the following functionality:

1. **View Users** - List all registered users in the system
2. **View Jobs** - List all resume analysis jobs in the system
3. **Reset Database** - Reset the database to its initial state
4. **Upload Resume** - Upload a resume PDF for analysis
5. **Download Results** - Download analysis results for the resume analysis job
6. **Match Resume with Job Details** - Analyze the match between the uploaded resume and the provided job information

To use the CLI, follow the instructions in `/docker/_readme.txt` file to run docker and simply run the provided Python script and follow the on-screen prompts:

```
python3 main.py
```

### Job Matching Process

When using the `Upload Resume` option, you'll be prompted to provide:
- User ID for tracking
- Your resume PDF file name
The system will then return the jobid for the uploaded resume. In the lambda function, the system does the following:
1. Upload your resume
2. Extract text using AWS Textract
3. Identify entities using AWS Comprehend

After the upload, you can use the `Match Resume with Job Details` option, you'll be prompted to provide:
- Jobid of the resume you want to match
- Job title
- Job description
- Required skills for the position

The system will then download 2 files to your local machine. One file is `{resume_file_name}_analysis.json`, which contains the analysis results, includes the overall score from 0-100, skills match, experience match, education match, strengths, gaps, and recommendation. The other file is `{resume_file_name}_structured.json`, which contains the structured resume, includes personal info, education, experience, skills, and extracted entities. In the lambda function, the system does the following:
1. Structure the resume into sections (personal info, education, experience, skills)
2. Compare your resume with the job description using AI
3. Generate a match report with scores and recommendations

## Architecture Details

### Data Flow

1. User uploads a resume and job details through the CLI
2. API Gateway receives the request and triggers the Lambda function
3. Lambda extracts text from the resume using Textract
4. Comprehend analyzes the texts for entities (PERSON, ORGANIZATION, DATE, etc.)
5. The system builds a structured resume from the entities
6. Bedrock's Llama 3.1 405B model compares the resume with job details
7. Analysis results are stored in S3 and RDS, then returned to the user

# Database Schema Details

## Users Table
The `users` table stores information about registered users:
- `userid` (integer): Primary key, unique identifier for each user
- `username` (text): User's display name
- `pwdhash` (text): Hashed password for user authentication

## Jobs Table
The `jobs` table tracks resume analysis jobs:
- `jobid` (integer): Primary key, unique identifier for each job
- `userid` (integer): Foreign key referencing the users table
- `status` (text): Current status of the job (uploaded, processing, completed, error)
- `originaldatafile` (text): Original filename of the uploaded resume
- `datafilekey` (text): S3 key for the uploaded resume PDF
- `resultsfilekey` (text): S3 key for the extracted entities JSON
- `analyzefilekey` (text): S3 key for the job match analysis results

## Analysis Features

The Job Match Resume Analyzer provides several key features:

### Entity Extraction
Using AWS Comprehend, the system extracts and categorizes entities from resumes:
- Personal information (name, email, phone, location)
- Education history (institutions, degrees, dates)
- Work experience (companies, positions, dates)
- Skills and qualifications

### Resume Structuring
The system organizes extracted information into a structured format:
- Identifies the most probable current location
- Distinguishes between education and work experience
- Associates dates with the appropriate organizations
- Recognizes education-related details like GPA

### AI-Powered Job Matching
Using AWS Bedrock with the Llama 3.1 405B model, the system:
- Compares the structured resume against the job description
- Calculates an overall match score (0-100)
- Identifies matching skills and missing qualifications
- Evaluates the relevance of work experience
- Assesses education requirements
- Provides specific strengths and gaps analysis
- Makes a hiring recommendation (hire, interview, or reject)

### Results Presentation
The system presents analysis results in a clear, readable format:
- Overall match score
- Detailed skills assessment
- Experience evaluation
- Education assessment
- Strengths and weaknesses
- Hiring recommendation with rationale