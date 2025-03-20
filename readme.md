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
- Terraform installed
- Python 3.9+ installed
- Access to Amazon Bedrock Llama 3.1 405B Instruct model

### IAM Permissions
The following permissions must be granted to the S3 readwrite user:
- AmazonOpenSearchFullAccess
- AmazonTextractFullAccess
- ComprehendFullAccess
- AmazonBedrockFullAccess

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
   pip install -t ./lambda_layer/python boto3 pypdf nltk spacy papaparse
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
   pip install requests tabulate configparser jsons
   ```

2. **Configure the CLI:**
   Edit the `benfordapp-client-config.ini` file with your API Gateway endpoint:
   ```ini
   [client]
   webservice = https://YOUR_GATEWAY_API.amazonaws.com
   ```

3. **Add job details functionality to the CLI:**
   Update the CLI code to add a new function for uploading resumes with job details:

   ```python
   def upload_with_job_details(baseurl):
       """
       Prompts the user for a local filename, user id, and job details,
       then uploads that asset (PDF) to S3 for processing with job matching.

       Parameters
       ----------
       baseurl: baseurl for web service

       Returns
       -------
       nothing
       """
       try:
           print("Enter PDF filename>")
           local_filename = input()

           if not pathlib.Path(local_filename).is_file():
               print("PDF file '", local_filename, "' does not exist...")
               return

           print("Enter user id>")
           userid = input()
           
           print("Enter job title>")
           job_title = input()
           
           print("Enter job description>")
           job_description = input()
           
           print("Enter required skills>")
           job_required_skills = input()

           # Read the PDF as raw bytes
           infile = open(local_filename, "rb")
           bytes = infile.read()
           infile.close()

           # Encode as base64
           data = base64.b64encode(bytes)
           datastr = data.decode()
           
           # Create data packet with job details
           data = {
               "filename": local_filename, 
               "data": datastr,
               "job_title": job_title,
               "job_description": job_description,
               "job_required_skills": job_required_skills
           }

           # Call the web service
           api = '/pdf/'
           url = baseurl + api + userid
           
           res = web_service_post(url, data)

           # Process response
           if res.status_code == 200: #success
               pass
           elif res.status_code == 400: # no such user
               body = res.json()
               print(body)
               return
           else:
               # failed:
               print("Failed with status code:", res.status_code)
               print("url: " + url)
               if res.status_code == 500:
                   # we'll have an error message
                   body = res.json()
                   print("Error message:", body)
               return

           # Extract jobid from response
           body = res.json()
           jobid = body
           
           print("PDF uploaded with job details, job id =", jobid)
           
           # Ask if user wants to poll for results
           print("Poll for results? (y/n)>")
           poll = input().lower()
           
           if poll == 'y':
               # Start polling for results
               print("Polling for results...")
               poll_for_results(baseurl, jobid)
               
           return

       except Exception as e:
           logging.error("**ERROR: upload_with_job_details() failed:")
           logging.error("url: " + url)
           logging.error(e)
           return
           
   def poll_for_results(baseurl, jobid):
       """
       Polls for results until job is complete or error occurs.
       
       Parameters
       ----------
       baseurl: baseurl for web service
       jobid: job id to poll for
       
       Returns
       -------
       nothing
       """
       try:
           while True:
               api = "/results/" + jobid
               url = baseurl + api
               res = web_service_get(url)
               
               print("Status code:", res.status_code)
               
               if res.status_code == 200:
                   # Success - we have results
                   body = res.json()
                   
                   try:
                       base64_bytes = base64.b64decode(body)
                       bytes = base64_bytes.decode()
                       results = bytes
                       print(results)
                       return
                   except Exception as e:
                       print("Error decoding results:", e)
                       return
                       
               elif res.status_code == 400:
                   # No such job
                   body = res.json()
                   print(body)
                   return
                   
               elif res.status_code in [480, 481, 482]:
                   # Still processing
                   msg = res.json()
                   print("Job status:", msg)
                   
                   if "error" in msg:
                       break
                       
                   # Wait a random time before checking again
                   sleeptime = random.randint(1, 5)
                   time.sleep(sleeptime)
                   continue
                   
               else:
                   # Failed
                   print("Failed with status code:", res.status_code)
                   print("url: " + url)
                   
                   if res.status_code == 500:
                       body = res.json()
                       print("Error message:", body)
                       
                   return
                   
       except Exception as e:
           logging.error("**ERROR: poll_for_results() failed:")
           logging.error("url: " + url)
           logging.error(e)
           return
   ```

   Also update the main function to include the new option:

   ```python
   # main processing loop:
   cmd = prompt()

   while cmd != 0:
       if cmd == 1:
           users(baseurl)
       elif cmd == 2:
           jobs(baseurl)
       elif cmd == 3:
           reset(baseurl)
       elif cmd == 4:
           upload(baseurl)
       elif cmd == 5:
           download(baseurl)
       elif cmd == 6:
           upload_and_poll(baseurl)
       elif cmd == 7:
           upload_with_job_details(baseurl)
       else:
           print("** Unknown command, try again...")
       #
       cmd = prompt()
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
