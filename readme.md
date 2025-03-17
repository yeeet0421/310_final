# Job Match Resume Analyzer

A cloud-based solution that helps job seekers optimize their resumes for specific job descriptions by identifying missing keywords, assessing formatting, and providing improvement recommendations.

## Project Architecture

### Backend API (AWS Lambda + API Gateway)
- Processes resume uploads and job descriptions
- Extracts text using AWS Textract
- Analyzes content using AWS Comprehend and OpenSearch
- Returns detailed match analysis and recommendations

### Command Line Interface
- Upload resumes and job descriptions
- View analysis results
- Access previous analysis reports

### Analysis Services
- **AWS Textract:** Extract structured text from PDF resumes
- **AWS OpenSearch:** Index and compare resumes against job descriptions
- **AWS Comprehend:** Identify keywords and perform sentiment analysis

### Data Storage
- **Amazon S3:** Store uploaded resumes and analysis results
- **Amazon RDS Aurora Serverless:** Store analysis reports and metadata

## Setup and Deployment

### Prerequisites
- AWS Account with appropriate permissions
- AWS CLI installed and configured
- Terraform installed
- Python 3.9+ installed

### Infrastructure Deployment

1. **Clone the repository:**
   ```
   git clone https://github.com/yourusername/resume-analyzer.git
   cd resume-analyzer
   ```

2. **Initialize Terraform:**
   ```
   terraform init
   ```

3. **Configure Variables:**
   Create a `terraform.tfvars` file with your specific configuration values:
   ```
   aws_region = "us-east-1"
   app_name = "resume-analyzer"
   environment = "dev"
   ```

4. **Prepare Lambda Deployment Packages:**
   ```
   # Prepare main Lambda function
   pip install -t ./lambda_layer/python boto3 pypdf nltk spacy
   cd lambda_layer
   zip -r ../lambda_function.zip .
   cd ..
   zip -g lambda_function.zip lambda_function.py
   
   # Prepare DB init Lambda function
   zip db_init.zip db_init.py
   ```

5. **Deploy Infrastructure:**
   ```
   terraform apply
   ```

6. **Note the Outputs:**
   After successful deployment, Terraform will output:
   - API Gateway endpoint URL
   - OpenSearch domain endpoint
   - RDS database endpoint
   - S3 bucket name

### CLI Client Setup

1. **Install required packages:**
   ```
   pip install requests tabulate configparser
   ```

2. **Configure the CLI:**
   ```
   python resume_analyzer_cli.py config --api-url <API_ENDPOINT_URL>
   ```

## Using the Resume Analyzer

### Via CLI

1. **Analyze a resume:**
   ```
   python resume_analyzer_cli.py analyze path/to/resume.pdf path/to/job_description.txt
   ```

2. **List previous analyses:**
   ```
   python resume_analyzer_cli.py list
   ```

3. **View a specific analysis report:**
   ```
   python resume_analyzer_cli.py get <analysis_id>
   ```

## Architecture Details

### Data Flow

1. User uploads a resume and job description through the CLI
2. API Gateway receives the request and triggers the Lambda function
3. Lambda extracts text from the resume using Textract
4. The extracted text and job description are indexed in OpenSearch
5. Comprehend analyzes the texts for key phrases, entities, and sentiment
6. The system performs keyword matching and similarity scoring
7. Analysis results are stored in RDS and returned to the user

### Database Schema

The system uses two main tables:

1. **jobs**: Tracks the status of analysis jobs
   - job_id: Unique identifier
   - datafilekey: S3 key for the uploaded resume
   - resultsfilekey: S3 key for the analysis results
   - status: Current job status
   - created_at: Timestamp when job was created
   - updated_at: Timestamp when job was last updated
   - job_description: The job description text

2. **analysis_reports**: Stores detailed analysis results
   - analysis_id: Unique identifier
   - resume_name: Name of the uploaded resume
   - job_description: Job description text
   - results: JSON string containing analysis results
   - match_score: Overall match score
   - created_at: Timestamp when analysis was completed

## Configuration

The system uses a configuration file to manage AWS service connections. A template is provided at `resumeanalyzer-config.ini`.

Example configuration:
```ini
[s3]
bucket_name = resume-analyzer-dev-resumes
profile_name = s3readwrite

[opensearch]
domain = https://search-resume-analyzer-dev-abcdefg.us-east-1.es.amazonaws.com

[rds]
endpoint = resume-analyzer-dev.cluster-abcdefg.us-east-1.rds.amazonaws.com
port_number = 5432
user_name = admin
user_pwd = your-secure-password-here
db_name = resume_analysis
secret_arn = arn:aws:secretsmanager:us-east-1:123456789012:secret:resume-analyzer-dev-db-credentials-abcdef
cluster_arn = arn:aws:rds:us-east-1:123456789012:cluster:resume-analyzer-dev
```

## Extending the System

### Adding a Web Frontend

If time permits, a web frontend can be developed using React/Next.js:

1. Create a new React application using Create React App or Next.js
2. Set up API integration to communicate with the backend
3. Develop UI components for:
   - Resume upload
   - Job description input
   - Analysis results display
   - Historical reports access

### Adding More Analysis Features

You can enhance the analysis capabilities by:

1. Implementing sentiment analysis of job descriptions
2. Adding industry-specific keyword dictionaries
3. Developing resume formatting templates
4. Creating visualizations of skill gaps
5. Implementing ATS (Applicant Tracking System) simulation

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

## License

MIT License