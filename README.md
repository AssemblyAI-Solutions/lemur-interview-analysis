# Interviewer Audit and Candidate Assessment

This script uses AssemblyAI, a transcription API, to assess the quality of job interviews by separately evaluating both the interviewer and the candidate's performance. The result of the analysis is displayed with the Streamlit library, an easy-to-use tool that helps to create custom web apps for machine learning and data science projects.

## Features

- Transcribes an interview file (audio/video).
- Parses the transcript to assess interviewer and candidate’s performance.
- Calculates a quality score based on the assessment.
- Displays the assessment result and quality score using Streamlit.
 
## Usage

Run the python script in your terminal. Open your browser and navigate to the indicated IP address. 

- Enter your AssemblyAI API key on Streamlit interface which is for accessing the AssemblyAI services. 
- You have three options to provide the interview transcript: 
 - Enter the id of the transcript if you already have it.
 - Enter URL of the interview file (audio/video).
 - Upload the file from your local system.
- Input job description and skills as per the job profile. 
- Click on 'Submit' and the analysis will be displayed on the screen. 

## Functions

- `transcribe_file(file)`: Transcribes the interview file and returns the transcript id.
- `candidate_quality_assessment(transcript_id, jd, skills)`: Rates the candidate's responses to the questions asked based on a set rubric and returns a string in JSON format. 
- `interviewer_quality_assessment(transcript_id, jd, skills)`: Evaluate the relevance of interviewer's questions based on a set rubric and returns a string in JSON format.
- `parse_json(response_string)`: Parses the output assessed quality to a Python format.
- `calculateQualityScore(arr)`: Calculates the quality score based on the grade obtained in the assessment.

Note: Both `candidate_quality_assessment` and `interviewer_quality_assessment` functions generate a task using `lemur.task()` to the AssemblyAI servers by passing `prompt` message and return the response asynchronously. 

## Dependencies

This script requires Python and the following Python libraries installed:

- assemblyai
- concurrent.futures
- json
- os
- re
- streamlit
