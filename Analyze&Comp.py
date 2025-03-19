#
# Lambda function to process resume entities and match against job descriptions
# This function assumes the entities have already been extracted using Amazon Comprehend
#
# import resume_analyzer

import json
import boto3
import os
import uuid
import urllib.parse
import datetime
from configparser import ConfigParser

def lambda_handler(event, context):
  try:
    print("**STARTING**")
    print("**lambda: resume_processor**")
    
    # Setup AWS based on config file
    config_file = 'benfordapp-config.ini'
    os.environ['AWS_SHARED_CREDENTIALS_FILE'] = config_file
    
    configur = ConfigParser()
    configur.read(config_file)
    
    # Configure for S3 access
    s3_profile = 's3readwrite'
    boto3.setup_default_session(profile_name=s3_profile)
    
    bucketname = configur.get('s3', 'bucket_name')
    region_name = configur.get('s3', 'region_name')
    
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucketname)
    
    # Configure Bedrock client for resume-job matching
    bedrock_runtime = boto3.client('bedrock-runtime', region_name=region_name)
    
    # Comment out DB configuration
    # rds_endpoint = configur.get('rds', 'endpoint')
    # rds_portnum = int(configur.get('rds', 'port_number'))
    # rds_username = configur.get('rds', 'user_name')
    # rds_pwd = configur.get('rds', 'user_pwd')
    # rds_dbname = configur.get('rds', 'db_name')
    
    # Get the resume key and entity data from the event
    resume_key = event['resume_key']
    raw_entities = event.get('entities_data')
    # job_id = event.get('job_id', 'default_job')  # Use a default job ID if not provided

    job_id = event.get('job_id', '0')  # Use a default job ID if not provided
    
    # If raw_entities is not provided in the event, try to read from S3
    if not raw_entities:
        entities_key = "310_final/p_sarkar/resume-a4be9513-dbeb-4e82-8335-2f2a356e4b44.json"
        print(f"Fetching entities from S3: {entities_key}")
        
        try:
            response = s3.Object(bucketname, entities_key).get()
            raw_entities = json.loads(response['Body'].read().decode('utf-8'))
        except Exception as e:
            print(f"Error reading entities file: {str(e)}")
            raise Exception(f"Entities data not provided and could not be read from S3: {str(e)}")
    # Comment out DB connection
    # dbConn = datatier.get_dbConn(rds_endpoint, rds_portnum, rds_username, rds_pwd, rds_dbname)
    
    # Process the entities from Comprehend
    print("**Processing entities**")
    
    # Organize entities by type
    entities = {}
    if 'Entities' in raw_entities:
      for entity in raw_entities['Entities']:
        entity_type = entity['Type']
        if entity_type not in entities:
          entities[entity_type] = []
        
        entities[entity_type].append({
          'text': entity['Text'],
          'score': entity['Score'],
          'begin_offset': entity['BeginOffset'],
          'end_offset': entity['EndOffset']
        })
    else:
      print("Warning: No 'Entities' key found in the raw data")
      entities = raw_entities  # Assume raw_entities is already organized by type
    
    # Build structured resume
    print("**Building structured resume**")
    
    # Extract personal information
    personal_info = {
      'name': '',
      'email': '',
      'phone': '',
      'location': ''
    }
    
    # Get name (PERSON entity with highest score)
    if 'PERSON' in entities and entities['PERSON']:
      sorted_persons = sorted(entities['PERSON'], key=lambda x: x['score'], reverse=True)
      personal_info['name'] = sorted_persons[0]['text']
    
    # Get contact info from OTHER entities
    if 'OTHER' in entities:
      for entity in entities['OTHER']:
        text = entity['text']
        if '@' in text and '.' in text and not personal_info['email']:
          # Extract email (look for email pattern)
          personal_info['email'] = text.split()[0] if ' ' in text else text
        elif '-' in text and text.replace('-', '').isdigit() and not personal_info['phone']:
          # Extract phone (look for phone number pattern)
          personal_info['phone'] = text
    
    # Get location
    if 'LOCATION' in entities and entities['LOCATION']:
      # Use the most frequent location as the candidate's current location
      location_counts = {}
      for location in entities['LOCATION']:
        loc_text = location['text']
        if loc_text not in location_counts:
          location_counts[loc_text] = 0
        location_counts[loc_text] += 1
      
      most_frequent_location = max(location_counts.items(), key=lambda x: x[1])[0]
      personal_info['location'] = most_frequent_location
    
    # Extract education information
    education = []
    education_orgs = []
    
    # Find education-related organizations
    if 'ORGANIZATION' in entities:
      for org in entities['ORGANIZATION']:
        org_text = org['text']
        if any(edu_term in org_text.lower() for edu_term in ['university', 'college', 'school', 'institute']):
          education_orgs.append(org)
    
    # Match education orgs with dates and locations
    for edu_org in education_orgs:
      edu_entry = {
        'institution': edu_org['text'],
        'degree': '',
        'field': '',
        'graduation_date': '',
        'location': '',
        'gpa': ''
      }
      
      # Find dates near this education entry
      if 'DATE' in entities:
        for date in entities['DATE']:
          # Check if date is near the education org in the text
          if abs(date['begin_offset'] - edu_org['end_offset']) < 100:
            edu_entry['graduation_date'] = date['text']
            break
      
      # Find GPA
      if 'QUANTITY' in entities:
        for quantity in entities['QUANTITY']:
          if '/' in quantity['text'] and abs(quantity['begin_offset'] - edu_org['end_offset']) < 200:
            edu_entry['gpa'] = quantity['text']
            break
      
      education.append(edu_entry)
    
    # Extract work experience
    experience = []
    
    # Find work-related organizations (exclude education orgs)
    work_orgs = []
    if 'ORGANIZATION' in entities:
      edu_org_texts = [org['text'] for org in education_orgs]
      for org in entities['ORGANIZATION']:
        if org['text'] not in edu_org_texts and not any(edu_term in org['text'].lower() for edu_term in ['university', 'college', 'school', 'institute', 'honor society']):
          work_orgs.append(org)
    
    # Sort work orgs by position in document
    work_orgs.sort(key=lambda x: x['begin_offset'])
    
    # Process each work organization
    for i, work_org in enumerate(work_orgs):
      # Skip organizations that appear to be associations/organizations rather than employers
      if any(term in work_org['text'].lower() for term in ['association', 'society', 'club', 'team']):
        continue
        
      work_entry = {
        'company': work_org['text'],
        'title': '',
        'start_date': '',
        'end_date': '',
        'location': '',
        'description': ''
      }
      
      # Find dates near this work entry
      if 'DATE' in entities:
        dates_near_work = []
        for date in entities['DATE']:
          # Check if date is near the work org in the text
          if abs(date['begin_offset'] - work_org['begin_offset']) < 100:
            dates_near_work.append(date)
        
        # Sort dates by position in document
        dates_near_work.sort(key=lambda x: x['begin_offset'])
        
        # Assign start and end dates
        if len(dates_near_work) >= 2:
          work_entry['start_date'] = dates_near_work[0]['text']
          work_entry['end_date'] = dates_near_work[1]['text']
        elif len(dates_near_work) == 1:
          work_entry['start_date'] = dates_near_work[0]['text']
      
      # Find locations near this work entry
      if 'LOCATION' in entities:
        for location in entities['LOCATION']:
          # Check if location is near the work org in the text
          if abs(location['begin_offset'] - work_org['begin_offset']) < 100:
            work_entry['location'] = location['text']
            break
      
      experience.append(work_entry)
    
    # Extract skills (TITLE entities are often skills in resumes)
    skills = []
    if 'TITLE' in entities:
      for title in entities['TITLE']:
        if title['text'] not in skills:
          skills.append(title['text'])
    
    # Build the complete structured resume
    structured_resume = {
      'personal_info': personal_info,
      'education': education,
      'experience': experience,
      'skills': skills,
      'extracted_entities': entities
    }
    
    # Create a resume summary for easier matching
    resume_summary = f"Name: {personal_info['name']}\n"
    resume_summary += f"Location: {personal_info['location']}\n"
    resume_summary += f"Contact: {personal_info['email']} | {personal_info['phone']}\n\n"
    
    resume_summary += "EDUCATION:\n"
    for edu in education:
      resume_summary += f"- {edu['institution']}"
      if edu['graduation_date']:
        resume_summary += f", {edu['graduation_date']}"
      if edu['gpa']:
        resume_summary += f", GPA: {edu['gpa']}"
      resume_summary += "\n"
    
    resume_summary += "\nEXPERIENCE:\n"
    for exp in experience:
      resume_summary += f"- {exp['company']}"
      if exp['title']:
        resume_summary += f", {exp['title']}"
      if exp['start_date'] or exp['end_date']:
        date_range = f"{exp['start_date'] if exp['start_date'] else ''} - {exp['end_date'] if exp['end_date'] else 'Present'}"
        resume_summary += f", {date_range}"
      if exp['location']:
        resume_summary += f", {exp['location']}"
      resume_summary += "\n"
    
    resume_summary += "\nSKILLS:\n"
    resume_summary += ", ".join(skills)
    
    # Store the structured resume and summary in S3
    results_file_key = resume_key.rsplit('.', 1)[0] + "_structured.json"
    
    print(f"**Saving structured resume to {results_file_key}**")
    
    local_results_file = "/tmp/structured_resume.json"
    with open(local_results_file, "w") as outfile:
      json.dump(structured_resume, outfile, indent=2)
    
    bucket.upload_file(
      local_results_file,
      results_file_key,
      ExtraArgs={
        'ACL': 'public-read',
        'ContentType': 'application/json'
      }
    )
    
    # If a job ID is provided, match the resume against it
    if job_id != 0:
      print(f"**Matching resume against job {job_id}**")
      
      # Instead of getting job from DB, load from S3
      job_file_key = f"jobs/{job_id}.json"
      print(f"Fetching job details from S3: {job_file_key}")
      
      try:
        job_response = s3.Object(bucketname, job_file_key).get()
        job_data = json.loads(job_response['Body'].read().decode('utf-8'))
        
        job_title = job_data.get('title', 'Unknown Position')
        job_description = job_data.get('description', '')
        job_required_skills = job_data.get('required_skills', [])
        
        # If required_skills is a list, convert to string
        if isinstance(job_required_skills, list):
          job_required_skills = ", ".join(job_required_skills)
        
      except Exception as e:
        print(f"Error reading job file, using test data: {str(e)}")
        # Use test data if job file doesn't exist
        job_title = "Software Developer"
        job_description = "We are looking for a skilled software developer with experience in Python, AWS, and web development."
        job_required_skills = "Python, AWS, JavaScript, REST API, Database Design"
      
      # Use AWS Bedrock with Claude to compare resume with job
      prompt = f"""
      <|begin_of_text|><|start_header_id|>system<|end_header_id|>
      You are a helpful AI assistant for Human Resource<|eot_id|><|start_header_id|>user<|end_header_id|>
      Compare the following resume summary with the job description and rate the match from 0 to 100.
      Provide a detailed analysis of the match, highlighting strengths and gaps.
      
      RESUME SUMMARY:
      {resume_summary}
      
      JOB TITLE: {job_title}
      
      JOB DESCRIPTION:
      {job_description}
      
      REQUIRED SKILLS:
      {job_required_skills}
      
      Provide your response in JSON format with these fields:
      - overall_score: (number between 0-100)
      - skills_match: (description of skills that match and skills that are missing)
      - experience_match: (assessment of relevant experience)
      - education_match: (assessment of education requirements)
      - strengths: (list of candidate's strengths for this position)
      - gaps: (list of areas where the candidate lacks qualifications)
      - recommendation: (hire, interview, or reject)
      <|eot_id|><|start_header_id|>assistant<|end_header_id|>
      """
      
      # Use the current Anthropic Claude model ID format for Bedrock
      response = bedrock_runtime.invoke_model(
        # modelId="anthropic.claude-3-sonnet-20240229-v1:0",  # Updated model ID
        modelId="us.meta.llama3-1-405b-instruct-v1:0",
        contentType="application/json",
        accept="application/json",
        body=json.dumps(
          {"prompt": prompt,
          # "max_tokens": 4000,
          "temperature": 0}
        #   {
        #   "anthropic_version": "bedrock-2023-05-31",
        #   "max_tokens": 4000,
        #   "temperature": 0,
        #   "messages": [
        #     {
        #       "role": "user",
        #       "content": prompt
        #     }
        #   ]
        # }
        )
      )
      print("**Llama successfully set up**")
      response_body = json.loads(response['body'].read())
      print(f"response_body: {response_body}")
      # Extract content from the new Claude API response format
      # match_analysis = response_body['content'][0]['text']
      match_analysis = response_body['generation']
      
      # Extract JSON from Claude's response
      try:
        match_results = json.loads(match_analysis)
      except:
        # If Claude didn't return proper JSON, try to parse it
        import re
        json_pattern = r'({[\s\S]*})'
        match = re.search(json_pattern, match_analysis)
        if match:
          try:
            match_results = json.loads(match.group(1))
          except:
            match_results = {
              "overall_score": 50,
              "skills_match": "Unable to parse detailed results",
              "experience_match": "Unable to parse detailed results",
              "education_match": "Unable to parse detailed results",
              "strengths": [],
              "gaps": [],
              "recommendation": "unknown"
            }
        else:
          match_results = {
            "overall_score": 50,
            "skills_match": "Error parsing results",
            "experience_match": "Error parsing results",
            "education_match": "Error parsing results",
            "strengths": [],
            "gaps": [],
            "recommendation": "unknown"
          }
      
      # Store the match results
      match_file_key = f"matches/{resume_key.rsplit('/', 1)[-1].rsplit('.', 1)[0]}_{job_id}.json"
      
      local_match_file = "/tmp/match_results.json"
      with open(local_match_file, "w") as outfile:
        json.dump(match_results, outfile, indent=2)
      
      bucket.upload_file(
        local_match_file,
        match_file_key,
        ExtraArgs={
          'ACL': 'public-read',
          'ContentType': 'application/json'
        }
      )
      
      # Include match results in the response
      structured_resume['job_match'] = {
        'job_id': job_id,
        'job_title': job_title,
        'match_score': match_results.get('overall_score', 50),
        'match_analysis': match_results
      }
    
    # Return the structured resume
    return {
      'statusCode': 200,
      'body': json.dumps({
        'message': 'Resume processed successfully',
        'resume_key': resume_key,
        'structured_resume': structured_resume,
        'results_file_key': results_file_key
      })
    }
    
  except Exception as err:
    print("**ERROR**")
    print(str(err))
    
    return {
      'statusCode': 500,
      'body': json.dumps({
        'message': 'Error processing resume',
        'error': str(err)
      })
    }