#
# Initialize the MySQL database with tables for resume parsing and ranking
#

import datatier
from configparser import ConfigParser

def init_database():
  try:
    print("**Initializing resume processing database**")
    
    # Read configuration
    config_file = 'resumeapp-config.ini'
    configur = ConfigParser()
    configur.read(config_file)
    
    # Get database connection parameters
    rds_endpoint = configur.get('rds', 'endpoint')
    rds_portnum = int(configur.get('rds', 'port_number'))
    rds_username = configur.get('rds', 'user_name')
    rds_pwd = configur.get('rds', 'user_pwd')
    rds_dbname = configur.get('rds', 'db_name')
    
    # Connect to database
    dbConn = datatier.get_dbConn(rds_endpoint, rds_portnum, rds_username, rds_pwd, rds_dbname)
    
    # Create resumes table
    create_resumes_table = """
    CREATE TABLE IF NOT EXISTS resumes (
      id INT AUTO_INCREMENT PRIMARY KEY,
      file_key VARCHAR(255) NOT NULL UNIQUE,
      structured_data_key VARCHAR(255),
      candidate_name VARCHAR(255),
      candidate_email VARCHAR(255),
      candidate_phone VARCHAR(255),
      candidate_location VARCHAR(255),
      skills JSON,
      status VARCHAR(50) DEFAULT 'pending',
      upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      last_processed TIMESTAMP NULL,
      error_message TEXT
    )
    """
    
    # Create jobs table
    create_jobs_table = """
    CREATE TABLE IF NOT EXISTS jobs (
      job_id VARCHAR(50) PRIMARY KEY,
      title VARCHAR(255) NOT NULL,
      description TEXT NOT NULL,
      required_skills TEXT,
      department VARCHAR(100),
      location VARCHAR(255),
      status VARCHAR(50) DEFAULT 'active',
      created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      ranking_key VARCHAR(255),
      last_ranked TIMESTAMP NULL,
      total_matches INT DEFAULT 0
    )
    """
    
    # Create resume_matches table
    create_matches_table = """
    CREATE TABLE IF NOT EXISTS resume_matches (
      id INT AUTO_INCREMENT PRIMARY KEY,
      resume_key VARCHAR(255),
      job_id VARCHAR(50),
      match_score FLOAT,
      match_details JSON,
      match_file_key VARCHAR(255),
      created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      last_matched TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (resume_key) REFERENCES resumes(file_key),
      FOREIGN KEY (job_id) REFERENCES jobs(job_id),
      UNIQUE KEY unique_match (resume_key, job_id)
    )
    """
    
    # Execute SQL to create tables
    datatier.perform_action(dbConn, create_resumes_table)
    print("Created resumes table")
    
    datatier.perform_action(dbConn, create_jobs_table)
    print("Created jobs table")
    
    datatier.perform_action(dbConn, create_matches_table)
    print("Created resume_matches table")
    
    print("**Database initialization complete**")
    
  except Exception as err:
    print("**ERROR initializing database**")
    print(str(err))

if __name__ == "__main__":
  init_database()