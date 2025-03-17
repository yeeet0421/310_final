import json
import os
import uuid
import boto3
from datetime import datetime
import base64
from configparser import ConfigParser

# Configuration
CONFIG_FILE = '/tmp/resumeanalyzer-config.ini'

def initialize_config():
    """
    Initialize configuration file for AWS services
    """
    # Create config file
    config = ConfigParser()
    
    # Add S3 section
    config['s3'] = {
        'bucket_name': os.environ.get('RESUME_BUCKET', ''),
        'profile_name': 's3readwrite'
    }
    
    # Add OpenSearch section
    config['opensearch'] = {
        'domain': os.environ.get('OPENSEARCH_DOMAIN', '')
    }
    
    # Add RDS section
    config['rds'] = {
        'endpoint': os.environ.get('RDS_ENDPOINT', ''),
        'port_number': os.environ.get('RDS_PORT', '5432'),
        'user_name': os.environ.get('RDS_USERNAME', 'admin'),
        'user_pwd': os.environ.get('RDS_PASSWORD', ''),
        'db_name': os.environ.get('DATABASE_NAME', 'resume_analysis'),
        'secret_arn': os.environ.get('RDS_SECRET_ARN', ''),
        'cluster_arn': os.environ.get('RDS_CLUSTER_ARN', '')
    }
    
    # Write config to file
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)
    
    # Set environment variable for AWS credentials
    os.environ['AWS_SHARED_CREDENTIALS_FILE'] = CONFIG_FILE
    
    # Return config object
    return config

# Initialize config
config = initialize_config()

# Initialize AWS service clients using config file
boto3.setup_default_session(profile_name=config['s3']['profile_name'])
s3 = boto3.resource('s3')
s3_client = boto3.client('s3')
textract = boto3.client('textract')
comprehend = boto3.client('comprehend')
rds_client = boto3.client('rds-data')
opensearch = boto3.client('opensearch')

# Load configuration values
BUCKET_NAME = config['s3']['bucket_name']
OPENSEARCH_DOMAIN = config['opensearch']['domain']
RDS_SECRET_ARN = config['rds']['secret_arn']
RDS_CLUSTER_ARN = config['rds']['cluster_arn']
DATABASE_NAME = config['rds']['db_name']

def lambda_handler(event, context):
    """
    Main handler for the resume analysis API
    """
    try:
        # Parse request path and method
        path = event.get('path', '')
        http_method = event.get('httpMethod', '')
        
        # Route the request to the appropriate handler
        if path == '/analyze' and http_method == 'POST':
            return handle_analyze_request(event)
        elif path == '/reports' and http_method == 'GET':
            return handle_get_reports(event)
        elif path.startswith('/reports/') and http_method == 'GET':
            report_id = path.split('/')[-1]
            return handle_get_report(report_id)
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Not found'})
            }
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def handle_analyze_request(event):
    """
    Handle resume analysis request
    """
    # Parse the request body
    body = json.loads(event.get('body', '{}'))
    
    # Extract request parameters
    resume_base64 = body.get('resume')
    job_description = body.get('jobDescription')
    resume_name = body.get('resumeName', 'resume.pdf')
    
    # Validate inputs
    if not resume_base64 or not job_description:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing resume or job description'})
        }
    
    # Generate a unique ID for this analysis
    analysis_id = str(uuid.uuid4())
    
    # Decode the base64 resume
    resume_data = base64.b64decode(resume_base64)
    
    # Upload the resume to S3
    s3_key = f"resumes/{analysis_id}/{resume_name}"
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=s3_key,
        Body=resume_data,
        ContentType='application/pdf'
    )
    
    # Extract text from resume using Textract
    textract_response = textract.detect_document_text(
        Document={
            'S3Object': {
                'Bucket': BUCKET_NAME,
                'Name': s3_key
            }
        }
    )
    
    # Process Textract response
    resume_text = extract_text_from_textract(textract_response)
    
    # Index the resume and job description in OpenSearch for analysis
    opensearch_response = index_documents(analysis_id, resume_text, job_description)
    
    # Analyze the resume against the job description
    analysis_results = analyze_resume(resume_text, job_description, analysis_id)
    
    # Store the analysis results in RDS
    store_analysis_results(analysis_id, resume_name, job_description, analysis_results)
    
    # Return the analysis results
    return {
        'statusCode': 200,
        'body': json.dumps({
            'analysisId': analysis_id,
            'results': analysis_results
        })
    }

def handle_get_reports(event):
    """
    Retrieve all analysis reports
    """
    # Query parameters for pagination
    query_params = event.get('queryStringParameters', {}) or {}
    limit = int(query_params.get('limit', '10'))
    offset = int(query_params.get('offset', '0'))
    
    # Query RDS for analysis reports
    sql = f"""
    SELECT analysis_id, resume_name, created_at, match_score
    FROM analysis_reports
    ORDER BY created_at DESC
    LIMIT {limit} OFFSET {offset}
    """
    
    response = rds_client.execute_statement(
        secretArn=RDS_SECRET_ARN,
        resourceArn=RDS_CLUSTER_ARN,
        database=DATABASE_NAME,
        sql=sql
    )
    
    # Process query results
    reports = []
    for record in response.get('records', []):
        reports.append({
            'analysisId': record[0]['stringValue'],
            'resumeName': record[1]['stringValue'],
            'createdAt': record[2]['stringValue'],
            'matchScore': float(record[3]['doubleValue'])
        })
    
    return {
        'statusCode': 200,
        'body': json.dumps({'reports': reports})
    }

def handle_get_report(report_id):
    """
    Retrieve a specific analysis report
    """
    # Query RDS for the specific report
    sql = f"""
    SELECT analysis_id, resume_name, job_description, results, created_at
    FROM analysis_reports
    WHERE analysis_id = '{report_id}'
    """
    
    response = rds_client.execute_statement(
        secretArn=RDS_SECRET_ARN,
        resourceArn=RDS_CLUSTER_ARN,
        database=DATABASE_NAME,
        sql=sql
    )
    
    # Check if report exists
    if not response.get('records'):
        return {
            'statusCode': 404,
            'body': json.dumps({'error': 'Report not found'})
        }
    
    # Process query result
    record = response['records'][0]
    report = {
        'analysisId': record[0]['stringValue'],
        'resumeName': record[1]['stringValue'],
        'jobDescription': record[2]['stringValue'],
        'results': json.loads(record[3]['stringValue']),
        'createdAt': record[4]['stringValue']
    }
    
    return {
        'statusCode': 200,
        'body': json.dumps(report)
    }

def extract_text_from_textract(textract_response):
    """
    Extract text from Textract response
    """
    text = ""
    for item in textract_response['Blocks']:
        if item['BlockType'] == 'LINE':
            text += item['Text'] + '\n'
    return text

def index_documents(analysis_id, resume_text, job_description):
    """
    Index resume and job description in OpenSearch for analysis
    """
    # Index resume
    resume_doc = {
        'resume_id': analysis_id,
        'content': resume_text,
        'type': 'resume',
        'timestamp': datetime.now().isoformat()
    }
    
    opensearch.index(
        DomainName=OPENSEARCH_DOMAIN,
        Index='resumes',
        Id=analysis_id,
        Body=json.dumps(resume_doc)
    )
    
    # Index job description
    job_doc = {
        'job_id': analysis_id,
        'content': job_description,
        'type': 'job_description',
        'timestamp': datetime.now().isoformat()
    }
    
    opensearch.index(
        DomainName=OPENSEARCH_DOMAIN,
        Index='jobs',
        Id=analysis_id,
        Body=json.dumps(job_doc)
    )
    
    # Allow indices to refresh
    return True

def analyze_resume(resume_text, job_description, analysis_id):
    """
    Analyze resume against job description
    """
    # Extract key phrases from job description using Comprehend
    job_key_phrases_response = comprehend.detect_key_phrases(
        Text=job_description,
        LanguageCode='en'
    )
    
    job_key_phrases = [phrase['Text'].lower() for phrase in job_key_phrases_response['KeyPhrases']]
    
    # Extract entities from job description (skills, qualifications, etc.)
    job_entities_response = comprehend.detect_entities(
        Text=job_description,
        LanguageCode='en'
    )
    
    job_entities = [entity['Text'].lower() for entity in job_entities_response['Entities']]
    
    # Combine key phrases and entities
    job_keywords = list(set(job_key_phrases + job_entities))
    
    # Check which keywords are present in the resume
    present_keywords = []
    missing_keywords = []
    
    for keyword in job_keywords:
        if keyword.lower() in resume_text.lower():
            present_keywords.append(keyword)
        else:
            missing_keywords.append(keyword)
    
    # Calculate match score
    match_score = (len(present_keywords) / len(job_keywords)) * 100 if job_keywords else 0
    
    # Perform more advanced similarity search using OpenSearch
    query = {
        "query": {
            "more_like_this": {
                "fields": ["content"],
                "like": job_description,
                "min_term_freq": 1,
                "max_query_terms": 50
            }
        }
    }
    
    similarity_response = opensearch.search(
        DomainName=OPENSEARCH_DOMAIN,
        Index='resumes',
        Body=json.dumps(query)
    )
    
    # Extract similarity score
    similarity_score = 0
    hits = json.loads(similarity_response.get('Body').read().decode('utf-8')).get('hits', {}).get('hits', [])
    if hits:
        similarity_score = hits[0].get('_score', 0)
    
    # Formatting analysis
    formatting_issues = analyze_formatting(resume_text)
    
    # Generate recommendations
    recommendations = generate_recommendations(missing_keywords, formatting_issues)
    
    # Prepare analysis results
    results = {
        'matchScore': round(match_score, 2),
        'similarityScore': round(similarity_score, 2),
        'presentKeywords': present_keywords,
        'missingKeywords': missing_keywords,
        'formattingIssues': formatting_issues,
        'recommendations': recommendations
    }
    
    return results

def analyze_formatting(resume_text):
    """
    Analyze resume formatting
    """
    issues = []
    
    # Check resume length
    lines = resume_text.strip().split('\n')
    if len(lines) < 10:
        issues.append("Resume appears too short")
    elif len(lines) > 100:
        issues.append("Resume may be too long")
    
    # Check for contact information
    has_email = any('@' in line for line in lines)
    has_phone = any(any(c.isdigit() for c in line) and ('-' in line or '(' in line or ')' in line) for line in lines)
    
    if not has_email:
        issues.append("Email address not detected")
    if not has_phone:
        issues.append("Phone number not detected")
    
    # Check for sections
    has_education = any('education' in line.lower() for line in lines)
    has_experience = any('experience' in line.lower() for line in lines)
    has_skills = any('skills' in line.lower() for line in lines)
    
    if not has_education:
        issues.append("Education section not clearly identified")
    if not has_experience:
        issues.append("Experience section not clearly identified")
    if not has_skills:
        issues.append("Skills section not clearly identified")
    
    return issues

def generate_recommendations(missing_keywords, formatting_issues):
    """
    Generate recommendations based on analysis
    """
    recommendations = []
    
    # Keyword recommendations
    if missing_keywords:
        recommendations.append({
            'category': 'Keywords',
            'description': 'Consider adding these missing keywords to your resume:',
            'items': missing_keywords[:10]  # Limit to top 10 keywords
        })
    
    # Formatting recommendations
    if formatting_issues:
        recommendations.append({
            'category': 'Formatting',
            'description': 'Address these formatting issues:',
            'items': formatting_issues
        })
    
    # General recommendations
    recommendations.append({
        'category': 'General',
        'description': 'General improvements:',
        'items': [
            'Quantify achievements with numbers and percentages',
            'Use action verbs to start bullet points',
            'Tailor your resume to match the specific job description',
            'Keep formatting consistent throughout the document'
        ]
    })
    
    return recommendations

def store_analysis_results(analysis_id, resume_name, job_description, results):
    """
    Store analysis results in RDS
    """
    sql = f"""
    INSERT INTO analysis_reports (
        analysis_id, resume_name, job_description, results, match_score, created_at
    ) VALUES (
        :analysis_id, :resume_name, :job_description, :results, :match_score, :created_at
    )
    """
    
    params = [
        {'name': 'analysis_id', 'value': {'stringValue': analysis_id}},
        {'name': 'resume_name', 'value': {'stringValue': resume_name}},
        {'name': 'job_description', 'value': {'stringValue': job_description}},
        {'name': 'results', 'value': {'stringValue': json.dumps(results)}},
        {'name': 'match_score', 'value': {'doubleValue': results['matchScore']}},
        {'name': 'created_at', 'value': {'stringValue': datetime.now().isoformat()}}
    ]
    
    rds_client.execute_statement(
        secretArn=RDS_SECRET_ARN,
        resourceArn=RDS_CLUSTER_ARN,
        database=DATABASE_NAME,
        sql=sql,
        parameters=params
    )
    
    return True