import concurrent.futures
from pathlib import Path
import assemblyai as aai
import os
import streamlit as st
import json
import re

st.title('Interviewer Audit and Candidate Assessment')
# api key
api_key = st.text_input('Enter your AssemblyAI API key: ', type='password')
aai.settings.api_key = api_key

# File
st.write('Provide either a transcript id, url of your interview file, or a local file.')
transcript_id_input = st.text_input('Enter your transcript id','')
local_file = st.file_uploader('Or upload your interview audio/video transcript', accept_multiple_files=False)
url_input = st.text_input('Or enter the URL of interview transcript', '')

# jd and skills
st.write('Enter job description and skills list')
job_description = st.text_area('Enter your job description')
skills = st.text_area('Enter the Skills List(comma separated):')


@st.cache_data
def transcribe_file(file):
    transcript = aai.Transcriber().transcribe(file)
    print(f'File {file} Transcript Id: {transcript.id}')
    return transcript.id

def candidate_quality_assessment(transcript_id, jd, skills):
    prompt = f'''
        You are reading transcript of a job interview.

        Here is the job description for that interview: <jd>{jd}</jd>

        Please pull out questions asked by interviewer and responses of interviewee.  The responses should be a string.
        As a candidate assessor, please grade candidates answer to question with an integer grade based on rubric below:
        Rubric:
        5: Excellent
        4: Good
        3: Mediocre
        2: Bad
        1: Terrible

        Then, tag the question and answer as relating to one of following skills:{skills}

        Return data in following JSON format: [{{'question':<question>,'answer':<answer>, 'skill':<skill>, 'grade',<int>}}].
    '''
    transcript_group = aai.TranscriptGroup.get_by_ids([transcript_id]) 
    result = transcript_group.lemur.task(
        prompt=prompt,
        max_output_size=4000,
        final_model='default'
    )
    return result.response

def interviewer_quality_assessment(transcript_id, jd, skills):
    prompt = f'''
        You are reading a transcript of a job interview.

        Here is the job description for that interview: <jd>{jd}</jd>

        Please pull out the questions asked by the interviewer. The questions should be a string.
        As an interviewer assessor, please grade the interviewers questions with an integer grade based on the rubric below:
        Rubric:
        5: Very Necessary
        4: Critical
        3: Moderately Important
        2: Optional
        1: Unneccessary

        Then, tag the question as relating to one of the following skills:{skills}

        Return the data in the following JSON format: [{{'question':<question>, 'skill':<skill>, 'grade',<int>}}].
    '''
    transcript_group = aai.TranscriptGroup.get_by_ids([transcript_id])  
    result = transcript_group.lemur.task(
        prompt=prompt,
        max_output_size=4000,
        final_model='default'
    )
    return result.response

def parse_json(response_string):
    start_index = response_string.find('[')
    end_index = response_string.rfind(']') + 1
    json_text = response_string[start_index:end_index]
    return json_text

def calculateQualityScore(arr):
  points = 0
  total = 0
  for n in arr:
    total += 5
    points += n['grade']
  return points/total

button = st.button('Submit')

if button:

    if transcript_id_input != '':
        transcript_id = transcript_id_input
    elif local_file is not None:
        file_bytes = local_file.read()
        # Get the file extension from the local file name
        file_extension = Path(local_file.name).suffix

        # Save file before transcribing with the original extension
        with open(f'temp_file{file_extension}', 'wb') as temp_file:
            temp_file.write(file_bytes)

        # API call to transcribe the file
        transcript = aai.Transcriber().transcribe(f'temp_file{file_extension}')
        transcript_id = transcript.id
    elif url_input != '':
        transcript_id = transcribe_file(url_input)
    else:
        st.write('Please input a file or URL.')



    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_1 = executor.submit(candidate_quality_assessment, transcript_id, job_description, skills)
        future_2 = executor.submit(interviewer_quality_assessment, transcript_id, job_description, skills)

    candidate_assessment = future_1.result()
    interviewer_audit = future_2.result()

    parsed_candidate_assessment = json.loads(parse_json(candidate_assessment))
    parsed_interviewer_audit = json.loads(parse_json(interviewer_audit))

    st.markdown('---') # Add a line
    st.subheader('Candidate Assessment')
    for q in parsed_candidate_assessment:
        st.markdown('~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ') # Add a line
        st.write('Question: ' + q['question'])
        st.write('Answer: ' + q['answer'])
        st.write('Skill: ' + q['skill'])
        st.write('Grade: ' + str(q['grade']))
    st.markdown('~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ') # Add a line
    st.write("Quality Score: "+str(calculateQualityScore(parsed_candidate_assessment)*100))
    st.write("Quality score formula: (total points)/(5 * # of questions *)")
    
        

    st.markdown('---') # Add a line
    st.subheader('Interviewer Assessment')
    for q in parsed_interviewer_audit:
        st.markdown('~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ') # Add a line
        st.write('Question: ' + q['question'])
        st.write('Grade: ' + str(q['grade']))
        st.write('Skill: ' + q['skill'])
    st.markdown('~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ') # Add a line
    st.write("Quality Score: "+str(calculateQualityScore(parsed_interviewer_audit)*100))
    st.write("Quality score formula: (total points)/(5 * # of questions *)")
        

