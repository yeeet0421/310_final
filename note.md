* reused proj03_upload
    * changed folder to  '/310_final'

* new function: final_compute
    * remove previous S3 event trigger to avoid `An error occurred when creating the trigger: Configuration is ambiguously defined. Cannot have overlapping suffixes in two rules if the prefixes are overlapping for the same event type.`
    * use content type `application/json` when uploading entity json results to S3

* added permissions to readwrite user in IAM
    * AmazonOpenSearchFullAccess
    * AmazonTextractFullAccess
    * ComprehendFullAccess
    * AmazonBedrockFullAccess

* reference
    * https://www.southeastern.edu/admin/career_srv/student_alumni/build_a_resume/resume_guide/samples/

* Amazon Bedrock
    * request model access for `Llama 3.1 405B Instruct`