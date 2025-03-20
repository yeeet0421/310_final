# Job Match Resume Analyzer

A cloud-based solution that helps job seekers optimize their resumes for specific job descriptions by identifying missing keywords, assessing formatting, and providing improvement recommendations.

## Project Architecture

### Backend API (AWS Lambda + API Gateway)
- Processes resume uploads and job descriptions
- Extracts text using AWS Textract
- Analyzes content using AWS Comprehend for entity extraction
- Uses AWS Bedrock with Llama 3.1 405B for resume-job matching
- Returns detailed match analysis and recommendations

### Command Line Interface
- Upload resumes and job descriptions
- View analysis results
- Access previous analysis reports
- Poll for results until job is complete

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
- AWS CLI installed and configured
- Python 3.9+ installed
- Access to Amazon Bedrock Llama 3.1 405B Instruct model

### IAM Permissions
The following permissions must be granted to the S3 readwrite user:
- AmazonOpenSearchFullAccess
- AmazonTextractFullAccess
- ComprehendFullAccess
- AmazonBedrockFullAccess
- AmazonS3FullAccess
- AmazonRDSFullAccess
- AWSLambdaFullAccess
- AmazonAPIGatewayAdministrator

### Manual Infrastructure Deployment

1. **Clone the repository:**
   ```
   git clone https://github.com/yourusername/resume-analyzer.git
   cd resume-analyzer
   ```

2. **Create S3 Bucket:**
   ```bash
   aws s3api create-bucket \
     --bucket resume-analyzer-dev-resumes \
     --region us-east-1
   ```

3. **Create Lambda Deployment Packages:**
   ```bash
   # Create directories for Lambda packages
   mkdir -p lambda_layer/python
   
   # Install required dependencies
   pip install -t ./lambda_layer/python boto3 pypdf nltk spacy papaparse
   
   # Create Lambda deployment package
   cd lambda_layer
   zip -r ../lambda_function.zip .
   cd ..
   zip -g lambda_function.zip lambda_function.py
   
   # Create DB initialization Lambda
   zip db_init.zip db_init.py
   ```

4. **Create RDS Database:**
   ```bash
   # Create a security group for RDS
   aws ec2 create-security-group \
     --group-name resume-analyzer-db-sg \
     --description "Security group for Resume Analyzer RDS"
   
   # Create the RDS instance
   aws rds create-db-instance \
     --db-instance-identifier resume-analyzer-db \
     --db-instance-class db.t3.micro \
     --engine postgres \
     --master-username admin \
     --master-user-password your-secure-password \
     --allocated-storage 20 \
     --vpc-security-group-ids sg-xxxxxxxx
   ```

5. **Create Lambda Functions:**
   ```bash
   Create functions and paste our function handler into code, add our provided layer .zip file
   ```

6. **Set up API Gateway:**
   ```bash
   # Create the API
   aws apigateway create-rest-api \
     --name "Resume Analyzer API" \
     --description "API for Resume Analyzer"
   
   # Get the API ID
   API_ID=$(aws apigateway get-rest-apis \
     --query "items[?name=='Resume Analyzer API'].id" \
     --output text)
   
   # Get the root resource ID
   ROOT_ID=$(aws apigateway get-resources \
     --rest-api-id $API_ID \
     --query "items[?path=='/'].id" \
     --output text)
   
   # Create resources and methods (example for /users endpoint)
   aws apigateway create-resource \
     --rest-api-id $API_ID \
     --parent-id $ROOT_ID \
     --path-part "users"
   
   USER_RESOURCE_ID=$(aws apigateway get-resources \
     --rest-api-id $API_ID \
     --query "items[?path=='/users'].id" \
     --output text)
   
   aws apigateway put-method \
     --rest-api-id $API_ID \
     --resource-id $USER_RESOURCE_ID \
     --http-method GET \
     --authorization-type NONE
   
   # Create other resources and methods for /jobs, /reset, /pdf, /results
   # (similar commands as above)
   
   # Deploy the API
   aws apigateway create-deployment \
     --rest-api-id $API_ID \
     --stage-name dev
   ```

7. **Initialize the Database:**
   ```bash
   # Invoke the DB initialization Lambda
   aws lambda invoke \
     --function-name resume-analyzer-db-init \
     --payload '{}' \
     output.txt
   ```

8. **Note the API Gateway URL:**
   ```bash
   # Get the API Gateway URL
   echo "https://$API_ID.execute-api.us-east-1.amazonaws.com/dev"
   ```

9. **Configure the CLI:**
   Update the configuration file with the API Gateway endpoint and other settings:
   ```ini
   [client]
   webservice = https://API_ID.execute-api.us-east-1.amazonaws.com/dev
   
   [s3]
   bucket_name = resume-analyzer-dev-resumes
   profile_name = s3readwrite
   region_name = us-east-1
   
   [rds]
   endpoint = your-db-endpoint.us-east-1.rds.amazonaws.com
   port_number = 5432
   user_name = admin
   user_pwd = your-secure-password
   db_name = resume_analysis
   ```


## Using the Resume Analyzer

### Via CLI

1. **Upload a resume and poll for results:**
   ```
   python resume_analyzer_cli.py
   ```
   Then select option 6 to upload a PDF and automatically poll for results.

2. **View all jobs:**
   ```
   python resume_analyzer_cli.py
   ```
   Then select option 2 to list all jobs in the system.

3. **Download analysis results:**
   ```
   python resume_analyzer_cli.py
   ```
   Then select option 5 and enter the job ID to download results.

4. **Submit a resume for analysis with job details:**
   ```
   python resume_analyzer_cli.py
   ```
   Then select option 7 (to be added) to upload a resume with job details:
   - You'll be prompted to enter the PDF file path
   - Enter the user ID
   - Enter the job title (e.g., "Human Resources Assistant")
   - Enter the job description
   - Enter the required skills

Example job details format:
```
Job Title: Human Resources Assistant
Job Description: This position reports to the Human Resources (HR) director and interfaces with company managers and HR staff...
Required Skills: 
- Proficient with Microsoft Word and Excel
- General knowledge of employment law and practices
- Able to maintain a high level of confidentiality
- Effective oral and written management communication skills
```

## Architecture Details

### Data Flow

1. User uploads a resume and job details through the CLI
2. API Gateway receives the request and triggers the Lambda function
3. Lambda extracts text from the resume using Textract
4. Comprehend analyzes the texts for entities (PERSON, ORGANIZATION, DATE, etc.)
5. The system builds a structured resume from the entities
6. Bedrock's Llama 3.1 405B model compares the resume with job details
7. Analysis results are stored in S3 and RDS, then returned to the user

### Database Schema

The system uses two main tables:

1. **jobs**: Tracks the status of analysis jobs
   - jobid: Unique identifier
   - userid: User identifier
   - status: Current job status (uploaded, processing, completed, error)
   - originaldatafile: Original file name
   - datafilekey: S3 key for the uploaded resume
   - resultsfilekey: S3 key for extracted entities
   - analyzefilekey: S3 key for job match analysis results

2. **users**: Stores user information
   - userid: Unique identifier
   - username: User's name
   - pwdhash: Password hash

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

## Analysis Process

1. **Entity Extraction:** The system uses AWS Comprehend to extract entities from the resume:
   - PERSON: Candidate name
   - ORGANIZATION: Companies and educational institutions
   - DATE: Employment dates and graduation dates
   - LOCATION: Work and education locations
   - TITLE: Job titles and skills
   - QUANTITY: GPA and other numerical data

2. **Resume Structuring:** The system organizes the extracted entities into:
   - Personal Information (name, email, phone, location)
   - Education (institutions, degrees, dates, GPAs)
   - Experience (companies, titles, dates, locations)
   - Skills

3. **Job Matching:** Using AWS Bedrock with Llama 3.1 405B Instruct, the system:
   - Compares the structured resume with job details
   - Scores the match from 0-100
   - Identifies skills matches and gaps
   - Assesses experience relevance
   - Evaluates education requirements
   - Provides hiring recommendations (hire, interview, reject)

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
