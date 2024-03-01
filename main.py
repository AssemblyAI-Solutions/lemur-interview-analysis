from tenacity import retry, stop_after_attempt, wait_fixed
import concurrent.futures
import st_btn_select
from pathlib import Path
import streamlit_scrollable_textbox as stx
import assemblyai as aai
import os
import streamlit as st
import json
import re

@st.cache_data
def transcribe_file(file):
    transcript = aai.Transcriber().transcribe(file)
    print(f'File {file} Transcript Id: {transcript.id}')
    return transcript.id

@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
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
    return json.loads(parse_json(result.response))

@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
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
    return json.loads(parse_json(result.response))


@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
def generate_summary_paragraph(transcript_id):
    transcript_group = aai.TranscriptGroup.get_by_ids([transcript_id])  
    result = transcript_group.lemur.summarize(
        context="you are the interviewer on this meeting. your job is to write a fact-based candidate summary for the hiring manager to review. do not include any opinions or details that are not directly from the interview. Focus the summary on the candidate background and motiviations for the role",
        answer_format="paragraph",
        max_output_size=4000,
        final_model='default'
    )
    return result.response

@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
def generate_summary_topics(transcript_id):
    transcript_group = aai.TranscriptGroup.get_by_ids([transcript_id])  
    result = transcript_group.lemur.summarize(
        context="you are the interviewer on this meeting. your job is to write a fact-based candidate summary for the hiring manager to review. do not include any opinions or details that are not directly from the interview. Focus the summary on the candidate background and motiviations for the role",
        answer_format="**<topic header>**\n<topic summary>\n",
        max_output_size=4000,
        final_model='default'
    )
    return result.response

@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
def generate_summary_questions(transcript_id):
    transcript_group = aai.TranscriptGroup.get_by_ids([transcript_id])  
    result = transcript_group.lemur.summarize(
        context="list the questions the interviewer asked the candidate. for each interview question, list the candidate response in bullet points",
        answer_format="<Interview Question>,• <Candidate Response>",
        max_output_size=4000,
        final_model='default'
    )
    return result.response

@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
def generate_question_answer(transcript_id):
    transcript_group = aai.TranscriptGroup.get_by_ids([transcript_id])
    # ask some questions
    questions = [
        aai.LemurQuestion(question="what role is the candidate interviewing for?"),
        aai.LemurQuestion(question="what is the candidate's relevant skills or background?"),
        aai.LemurQuestion(question="how many years of relevant experience does the candidate? provide context for your answer?",answer_options=["1-3","4-7","more than 7","Unknown"]),
        aai.LemurQuestion(question="what are the candidate's strengths and weaknesses?"),
        aai.LemurQuestion(question="what questions did the candidate ask the interviewer?",answer_format="bullet points"),
    ]  
    result = transcript_group.lemur.question(questions)
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

# Initialize session_state if it doesn't exist
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""

if 'homepage' not in st.session_state:
    st.session_state.homepage = True

if 'complete' not in st.session_state:
    st.session_state.complete = False

# Initialize session_state if it doesn't exist
if 'transcript_id_input' not in st.session_state:
    st.session_state.transcript_id_input = ''
if 'local_file' not in st.session_state:
    st.session_state.local_file = None
if 'url_input' not in st.session_state:
    st.session_state.url_input = ''
if 'job_description' not in st.session_state:
    st.session_state.job_description = ''
if 'skills' not in st.session_state:
    st.session_state.skills = ''
if 'transcript_text' not in st.session_state:
    st.session_state.transcript_text = ''

st.title('Interviewer Audit and Candidate Assessment')

if st.session_state.homepage:
    # api key
    api_key = st.text_input('Enter your AssemblyAI API key: ',value=st.session_state.api_key , type='password')
    aai.settings.api_key = api_key
    st.session_state.api_key = api_key

    # File
    st.write('Provide either a transcript id, url of your interview file, or a local file.')
    transcript_id_input = st.text_input('Enter your transcript id','')
    local_file = st.file_uploader('Or upload your interview audio/video transcript', accept_multiple_files=False)
    url_input = st.text_input('Or enter the URL of interview transcript', '')

    # jd and skills
    st.write('Enter job description and skills list')
    job_description = st.text_area('Enter your job description')
    skills = st.text_area('Enter the Skills List(comma separated):')


    button = st.button('Submit')

    if button:
        if transcript_id_input == '' and local_file is None and url_input == '':
            st.write('Please input a file or URL.')
        else:
            st.session_state.homepage = False
            st.session_state.transcript_id_input = transcript_id_input
            st.session_state.local_file = local_file
            st.session_state.url_input = url_input
            st.session_state.job_description = job_description
            st.session_state.skills = skills
            st.rerun()


else: #running or complete page
    if st.session_state.complete == False:
        st.write('')
        with st.spinner('Loading...'):
            transcript_id_input = st.session_state.transcript_id_input
            local_file = st.session_state.local_file
            url_input = st.session_state.url_input
            job_description = st.session_state.job_description
            skills = st.session_state.skills
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
            st.session_state.transcript_text = aai.Transcript.get_by_id(transcript_id).text


            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_1 = executor.submit(candidate_quality_assessment, transcript_id, job_description, skills)
                future_2 = executor.submit(interviewer_quality_assessment, transcript_id, job_description, skills)
                future_3 = executor.submit(generate_summary_paragraph,transcript_id)
                future_4 = executor.submit(generate_summary_topics,transcript_id)
                # future_5 = executor.submit(generate_summary_questions,transcript_id)
                future_6 = executor.submit(generate_question_answer,transcript_id)


            st.session_state.parsed_candidate_assessment = future_1.result()
            st.session_state.parsed_interviewer_audit = future_2.result()
            st.session_state.summary_paragraph = future_3.result()
            st.session_state.summary_topics = future_4.result()
            # st.session_state.summary_questions = future_5.result()
            st.session_state.question_answer = future_6.result()
            st.session_state.complete = True
    
    st.write('')
    button2 = st.button('RESET')
    if button2:
        st.session_state.homepage = True
        st.session_state.transcript_id_input = ''
        st.session_state.local_file = None
        st.session_state.url_input = ''
        st.session_state.job_description = ''
        st.session_state.skills = ''
        st.session_state.transcript_text = ''
        st.session_state.complete = False
        st.rerun()


    st.subheader('Transcript Text:')
    stx.scrollableTextbox(st.session_state.transcript_text)
    st.markdown("\n" * 1)
    option = st_btn_select.st_btn_select(('Paragraph Summary', 'Topic Summary', 'Basic Question-Answer','Candidate Assessment', 'Interviewer Assessment'), index=0)
    if option == 'Candidate Assessment':
        st.subheader('Candidate Assessment')
        for q in st.session_state.parsed_candidate_assessment:
            st.markdown('~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ') # Add a line
            st.write('Question: ' + q['question'])
            st.write('Answer: ' + q['answer'])
            st.write('Skill: ' + q['skill'])
            st.write('Grade: ' + str(q['grade']))
        st.markdown('~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ') # Add a line
        st.write("Quality Score: "+str(calculateQualityScore(st.session_state.parsed_candidate_assessment)*100))
        st.write("Quality score formula: (total points)/(5 * # of questions *)")
    if option == 'Interviewer Assessment':
        st.subheader('Interviewer Assessment')
        for q in st.session_state.parsed_interviewer_audit:
            st.markdown('~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ') # Add a line
            st.write('Question: ' + q['question'])
            st.write('Grade: ' + str(q['grade']))
            st.write('Skill: ' + q['skill'])
        st.markdown('~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ') # Add a line
        st.write("Quality Score: "+str(calculateQualityScore(st.session_state.parsed_interviewer_audit)*100))
        st.write("Quality score formula: (total points)/(5 * # of questions *)")
    if option == 'Paragraph Summary':
        st.subheader('Paragraph Summary')
        st.write(st.session_state.summary_paragraph)
    if option == 'Topic Summary':
        st.subheader('Topic Summary')
        st.write(st.session_state.summary_topics)
    # if option == 'Interviewer Questions':
    #     st.subheader('Interviewer Questions')
    #     st.write(st.session_state.summary_questions)
    if option == 'Basic Question-Answer':
        st.subheader('Basic Question-Answer')
        for q in st.session_state.question_answer:
            st.write(f"{q.question}")
            st.write(f"Answer: {q.answer}")
            st.write()