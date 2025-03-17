import json
import boto3
import os

# Initialize AWS service clients
rds_client = boto3.client('rds-data')

# Configuration from environment variables
RDS_SECRET_ARN = os.environ.get('RDS_SECRET_ARN')
RDS_CLUSTER_ARN = os.environ.get('RDS_CLUSTER_ARN')
DATABASE_NAME = os.environ.get('DATABASE_NAME')

def lambda_handler(event, context):
    """
    Initialize the database schema for the Resume Analyzer
    """
    try:
        # Create the analysis_reports table
        create_analysis_reports_table()
        
        return {
            'statusCode': 200,
            'body': json.dumps('Database initialization completed successfully')
        }
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def create_analysis_reports_table():
    """
    Create the analysis_reports table in the database
    """
    sql = """
    CREATE TABLE IF NOT EXISTS analysis_reports (
        analysis_id VARCHAR(36) PRIMARY KEY,
        resume_name VARCHAR(255) NOT NULL,
        job_description TEXT NOT NULL,
        results TEXT NOT NULL,
        match_score FLOAT NOT NULL,
        created_at TIMESTAMP NOT NULL
    );
    """
    
    response = rds_client.execute_statement(
        secretArn=RDS_SECRET_ARN,
        resourceArn=RDS_CLUSTER_ARN,
        database=DATABASE_NAME,
        sql=sql
    )
    
    print(f"Table creation response: {response}")
    return response