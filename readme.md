# Job Match Resume Analyzer

A cloud-based solution that helps job seekers optimize their resumes for specific job descriptions by identifying missing keywords, assessing formatting, and providing improvement recommendations.

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
- **AWS Textract:** Extract structured text from PDF resumes
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
   - Record the database endpoint, port, username, and password

3. **Lambda Functions:**
   - Create Lambda functions using the provided code:
     - `db_init.py`: For initializing the database schema
     - `lambda_function.py`: Main processor for handling resume uploads
     - `resume_processor.py`: For processing resumes and performing job matching
   - Configure environment variables or config files with S3 and RDS connection details
   - Ensure Lambda functions have appropriate permissions to access S3, RDS, Textract, Comprehend, and Bedrock

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
- **GET /results/{jobid}**
  - Retrieves the analysis results for a specific job
  - Path Parameter: jobid (integer)
  - Returns:
    - If job is complete: Base64-encoded results
    - If job is still processing: Status message
    - If job doesn't exist: Error message

5. **Configuration:**
   - Create a configuration file (`resumeapp-config.ini`) with the following sections:
     ```ini
     [s3]
     bucket_name = your-bucket-name
     profile_name = s3readwrite
     region_name = your-region
     
     [rds]
     endpoint = your-db-endpoint
     port_number = 5432
     user_name = your-username
     user_pwd = your-password
     db_name = your-db-name
     ```
   - Create a client configuration file (`benfordapp-client-config.ini`):
     ```ini
     [client]
     webservice = https://your-api-gateway-url
     ```

### Client Setup Usage

The Resume Analyzer  client requires a configuration file to connect to the AWS services. A sample configuration file named `resumeapp-client-config.ini` should be created with the following format:

```ini
[client]
webservice = https://your-api-gateway-url
```

The  client will automatically read this configuration file to establish connection with the backend services.

## Using the Resume Analyzer

The Resume Analyzer comes with a command-line interface (CLI) client that provides the following functionality:

1. **View Users** - List all registered users in the system
2. **View Jobs** - List all resume analysis jobs in the system
3. **Reset Database** - Reset the database to its initial state
4. **Upload Resume** - Upload a resume PDF for analysis
5. **Download Results** - Download analysis results for a specific job
6. **Upload and Poll** - Upload a resume and automatically wait for results
7. **Upload with Job Details** - Upload a resume and provide job information for matching

To use the CLI, simply run the provided Python script and follow the on-screen prompts:

```
python resume_analyzer_cli.py
```

### Job Matching Process

When using the "Upload with Job Details" option, you'll be prompted to provide:
- Path to your resume PDF file
- User ID for tracking
- Job title
- Job description
- Required skills for the position

The system will then:
1. Upload your resume
2. Extract text using AWS Textract
3. Identify entities using AWS Comprehend
4. Structure the resume into sections (personal info, education, experience, skills)
5. Compare your resume with the job description using AI
6. Generate a match report with scores and recommendations

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

## Configuration

The system uses a configuration file to manage AWS service connections. A template is provided at `benfordapp-config.ini`.

Example configuration:
```ini
[s3]
bucket_name = resume-analyzer-dev-resumes
profile_name = s3readwrite
region_name = us-east-1

[rds]
endpoint = resume-analyzer-dev.cluster-abcdefg.us-east-1.rds.amazonaws.com
port_number = 5432
user_name = admin
user_pwd = your-secure-password-here
db_name = resume_analysis
```

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

## Troubleshooting

Common issues and solutions:

1. **API Connection Errors**:
   - Verify API Gateway endpoint in CLI configuration
   - Check AWS credentials and permissions

2. **PDF Parsing Issues**:
   - Ensure PDF is not password-protected
   - Verify PDF is text-based (not scanned)

3. **Database Connection Errors**:
   - Check database credentials in config file
   - Verify VPC security group settings

4. **Analysis Delays**:
   - Use the polling function (option 6) to automatically wait for results
   - Large resumes may take longer to process

5. **Bedrock Model Access**:
   - Ensure you have requested and been granted access to Llama 3.1 405B Instruct model
   - Verify IAM permissions include AmazonBedrockFullAccess

## License

MIT License
