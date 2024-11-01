from retrying import retry, RetryError
from time import sleep
from concurrent.futures import ThreadPoolExecutor
import st_btn_select
from pathlib import Path
import streamlit_scrollable_textbox as stx
import assemblyai as aai
import os
import streamlit as st
import json
import re

def transcribe_file(file):
    print('starting transcribe')
    transcript = aai.Transcriber().transcribe(file)
    print(f'File {file} Transcript Id: {transcript.id}')
    return transcript.id

def filter_q_and_a(q_and_a_arr):
    filtered_arr = []
    for item in q_and_a_arr:
        if "question" in item and "answer" in item:
            filtered_arr.append(item)
    return filtered_arr

@retry(wait_fixed=1000, stop_max_attempt_number=10)
def get_questions(transcript_id, jd, api_key, transcript_text=None):  # Add transcript_text parameter
    try:
        if transcript_text:  # Use Lemur with input text
            prompt = f'''
                You are reading transcript of a job interview.

                Here is the job description for that interview: <jd>{jd}</jd>

                Please pull out questions asked by interviewer and responses of the candidate. 
                Format the questions as if they were appearing on a test.

                Return data in following JSON format: [{{"question":"<question>","answer":"<answer>"}}].
            '''
            result = aai.Lemur().task(
                prompt=prompt,
                input_text=transcript_text,  # Pass transcript_text to Lemur
                max_output_size=4000,
                final_model='anthropic/claude-3-5-sonnet'
            )
        else:  # Use Lemur with transcript ID
            prompt = f'''
                You are reading transcript of a job interview.

                Here is the job description for that interview: <jd>{jd}</jd>

                Please pull out questions asked by interviewer and responses of the candidate. 
                Format the questions as if they were appearing on a test.

                Return data in following JSON format: [{{"question":"<question>","answer":"<answer>"}}].
            '''
            aai.settings.api_key = api_key
            transcript_group = aai.TranscriptGroup.get_by_ids([transcript_id]) 
            result = transcript_group.lemur.task(
                prompt=prompt,
                max_output_size=4000,
                final_model='anthropic/claude-3-5-sonnet'
            )
        print(result.response)
        q_and_a_arr = filter_q_and_a(parse_json(result.response))

        if not q_and_a_arr:
            print("q_and_a_arr is empty")
            raise ValueError("q_and_a_arr is empty")
        return q_and_a_arr
    except RetryError:
        # Handle the case when all retries are used
        print("All retries used. Returning empty array.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Re-running LeMUR Request")
        try:
            if '429' in e:
                sleep(60)
        except: pass
        raise

@retry(wait_fixed=1000, stop_max_attempt_number=10)
def get_skills(transcript_id, jd, skills, api_key, q_and_a_arr, transcript_text=None):  # Add transcript_text parameter
    try:
        if transcript_text:  # Use Lemur with input text
            new_prompt = f'''
                You are reading transcript of a job interview.

                Here is the job description for that interview: <jd>{jd}</jd>

                Here is an array of the questions asked by the interviewer and the candidates answer in the transcript: {json.dumps(q_and_a_arr)}
                Reference the transcript for a more complete understanding of the candidates answer.

                Tag each question and answer pair as relating to one of following skills:{skills}

                Return data in following JSON format: [{{"question":"<question>","answer":"<answer>", "skill":"<skill>"}}].
            '''
            result = aai.Lemur().task(
                prompt=new_prompt,
                input_text=transcript_text,  # Pass transcript_text to Lemur
                max_output_size=4000,
                final_model='anthropic/claude-3-5-sonnet'
            )
        else:  # Use Lemur with transcript ID
            new_prompt = f'''
                You are reading transcript of a job interview.

                Here is the job description for that interview: <jd>{jd}</jd>

                Here is an array of the questions asked by the interviewer and the candidates answer in the transcript: {json.dumps(q_and_a_arr)}
                Reference the transcript for a more complete understanding of the candidates answer.

                Tag each question and answer pair as relating to one of following skills:{skills}

                Return data in following JSON format: [{{"question":"<question>","answer":"<answer>", "skill":"<skill>"}}].
            '''
            aai.settings.api_key = api_key
            transcript_group = aai.TranscriptGroup.get_by_ids([transcript_id]) 
            result = transcript_group.lemur.task(
                prompt=new_prompt,
                max_output_size=4000,
                final_model='anthropic/claude-3-5-sonnet'
            )
        print(result.response)
        final_q_and_a_arr = parse_json(result.response)
        if not final_q_and_a_arr:
            print("final_q_and_a_arr is empty")
            raise ValueError("final_q_and_a_arr is empty")
        return final_q_and_a_arr
    except RetryError:
        # Handle the case when all retries are used
        print("All retries used. Returning empty array.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Re-running LeMUR Request")
        try:
            if '429' in e:
                sleep(60)
        except: pass
        raise


@retry(wait_fixed=1000, stop_max_attempt_number=10)
def candidate_quality_assessment(transcript_id, jd, skills, api_key, q_and_a_arr, transcript_text=None):  # Add transcript_text parameter
    try:
        if transcript_text:  # Use Lemur with input text
            prompt = f'''
                You are reading transcript of a job interview.

                Here is the job description for that interview: <jd>{jd}</jd>

                Here is an array of objects that each include a question asked by the interviewer, the candidates answer to the question, and the related skill: {json.dumps(q_and_a_arr)}
                For each question, reference the transcript for a more complete understanding of the candidates answer.

                As a candidate assessor, please grade candidates answers to questions with an integer grade based on rubric below:
                Rubric:
                5: Excellent
                4: Good
                3: Mediocre
                2: Bad
                1: Terrible

                Return data in following JSON format: [{{"question":"<question>","answer":"<answer>", "grade":"<grade>"}}].
            '''
            result = aai.Lemur().task(
                prompt=prompt,
                input_text=transcript_text,  # Pass transcript_text to Lemur
                max_output_size=4000,
                final_model='anthropic/claude-3-5-sonnet'
            )
        else:  # Use Lemur with transcript ID
            prompt = f'''
                You are reading transcript of a job interview.

                Here is the job description for that interview: <jd>{jd}</jd>

                Here is an array of objects that each include a question asked by the interviewer, the candidates answer to the question, and the related skill: {json.dumps(q_and_a_arr)}
                For each question, reference the transcript for a more complete understanding of the candidates answer.

                As a candidate assessor, please grade candidates answers to questions with an integer grade based on rubric below:
                Rubric:
                5: Excellent
                4: Good
                3: Mediocre
                2: Bad
                1: Terrible

                Return data in following JSON format: [{{"question":"<question>","answer":"<answer>", "grade":"<grade>"}}].
            '''
            aai.settings.api_key = api_key
            transcript_group = aai.TranscriptGroup.get_by_ids([transcript_id]) 
            result = transcript_group.lemur.task(
                prompt=prompt,
                max_output_size=4000,
                final_model='anthropic/claude-3-5-sonnet'
            )
        return parse_json(result.response)
    except RetryError:
        # Handle the case when all retries are used
        print("All retries used. Returning empty array.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Re-running LeMUR Request")
        try:
            if '429' in e:
                sleep(60)
        except: pass
        raise

@retry(wait_fixed=1000, stop_max_attempt_number=10)
def interviewer_quality_assessment(transcript_id, jd, skills, api_key, q_and_a_arr, transcript_text=None):  # Add transcript_text parameter
    try:
        if transcript_text:  # Use Lemur with input text
            prompt = f'''
                You are reading a transcript of a job interview.

                Here is the job description for that interview: <jd>{jd}</jd>

                Here is an array of objects that each include a question asked by the interviewer, the candidates answer to the question, and the related skill: {json.dumps(q_and_a_arr)}
                Reference the transcript for a more complete understanding of the candidates answer.

                As an interviewer assessor, your role involves evaluating the relevance of each question posed by the interviewer. 
                Avoid assigning low grades unless the questions lack relevance to the job description. 
                Questions pertaining to soft skills and background, such as "tell me about yourself" and "how do you work in teams," should be considered essential.
                
                Please grade the interviewers questions with an integer grade based on the rubric below:
                Rubric:
                5: Very Necessary
                4: Critical
                3: Optional
                2: Unneccessary
                1: Completely Irrelevant

                Return the data in the following JSON format: [{{"question":"<question>", "grade":"<grade>"}}].
            '''
            result = aai.Lemur().task(
                prompt=prompt,
                input_text=transcript_text,  # Pass transcript_text to Lemur
                max_output_size=4000,
                final_model='anthropic/claude-3-5-sonnet'
            )
        else:  # Use Lemur with transcript ID
            prompt = f'''
                You are reading a transcript of a job interview.

                Here is the job description for that interview: <jd>{jd}</jd>

                Here is an array of objects that each include a question asked by the interviewer, the candidates answer to the question, and the related skill: {json.dumps(q_and_a_arr)}
                Reference the transcript for a more complete understanding of the candidates answer.

                As an interviewer assessor, your role involves evaluating the relevance of each question posed by the interviewer. 
                Avoid assigning low grades unless the questions lack relevance to the job description. 
                Questions pertaining to soft skills and background, such as "tell me about yourself" and "how do you work in teams," should be considered essential.
                
                Please grade the interviewers questions with an integer grade based on the rubric below:
                Rubric:
                5: Very Necessary
                4: Critical
                3: Optional
                2: Unneccessary
                1: Completely Irrelevant

                Return the data in the following JSON format: [{{"question":"<question>", "grade":"<grade>"}}].
            '''
            aai.settings.api_key = api_key
            transcript_group = aai.TranscriptGroup.get_by_ids([transcript_id])  
            result = transcript_group.lemur.task(
                prompt=prompt,
                max_output_size=4000,
                final_model='anthropic/claude-3-5-sonnet'
            )
        return parse_json(result.response)
    except RetryError:
        # Handle the case when all retries are used
        print("All retries used. Returning empty array.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Re-running LeMUR Request")
        try:
            if '429' in e:
                sleep(60)
        except: pass
        raise

@retry(wait_fixed=1000, stop_max_attempt_number=10)
def generate_summary_paragraph(transcript_id, api_key, transcript_text=None):  # Add transcript_text parameter
    try:
        if transcript_text:  # Use Lemur with input text
            result = aai.Lemur().summarize(
                context="you are the interviewer on this meeting. your job is to write a fact-based candidate summary for the hiring manager to review. do not include any opinions or details that are not directly from the interview. Focus the summary on the candidate background and motiviations for the role",
                answer_format="paragraph",
                input_text=transcript_text,  # Pass transcript_text to summarize
                max_output_size=4000,
                final_model='anthropic/claude-3-5-sonnet'
            )
        else:  # Use Lemur with transcript ID
            aai.settings.api_key = api_key
            transcript_group = aai.TranscriptGroup.get_by_ids([transcript_id])  
            result = transcript_group.lemur.summarize(
                context="you are the interviewer on this meeting. your job is to write a fact-based candidate summary for the hiring manager to review. do not include any opinions or details that are not directly from the interview. Focus the summary on the candidate background and motiviations for the role",
                answer_format="paragraph",
                max_output_size=4000,
                final_model='anthropic/claude-3-5-sonnet'
            )
        return result.response
    except RetryError:
        # Handle the case when all retries are used
        print("All retries used. Returning empty string.")
        return ''
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Re-running LeMUR Request")
        try:
            if '429' in e:
                sleep(60)
        except: pass
        raise

@retry(wait_fixed=1000, stop_max_attempt_number=10)
def generate_summary_topics(transcript_id, api_key, transcript_text=None):  # Add transcript_text parameter
    try:
        if transcript_text:  # Use Lemur with input text
            result = aai.Lemur().summarize(
                context="you are the interviewer on this meeting. your job is to write a fact-based candidate summary for the hiring manager to review. do not include any opinions or details that are not directly from the interview. Focus the summary on the candidate background and motiviations for the role",
                answer_format="**<topic header>**\n<topic summary>\n",
                input_text=transcript_text,  # Pass transcript_text to summarize
                max_output_size=4000,
                final_model='anthropic/claude-3-5-sonnet'
            )
        else:  # Use Lemur with transcript ID
            aai.settings.api_key = api_key
            transcript_group = aai.TranscriptGroup.get_by_ids([transcript_id])  
            result = transcript_group.lemur.summarize(
                context="you are the interviewer on this meeting. your job is to write a fact-based candidate summary for the hiring manager to review. do not include any opinions or details that are not directly from the interview. Focus the summary on the candidate background and motiviations for the role",
                answer_format="**<topic header>**\n<topic summary>\n",
                max_output_size=4000,
                final_model='anthropic/claude-3-5-sonnet'
            )
        return result.response
    except RetryError:
        # Handle the case when all retries are used
        print("All retries used. Returning empty string.")
        return ''
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Re-running LeMUR Request")
        try:
            if '429' in e:
                sleep(60)
        except: pass
        raise


@retry(wait_fixed=1000, stop_max_attempt_number=10)
def generate_summary_questions(transcript_id, transcript_text=None):  # Add transcript_text parameter
    try:
        if transcript_text:  # Use Lemur with input text
            result = aai.Lemur().summarize(
                context="list the questions the interviewer asked the candidate. for each interview question, list the candidate response in bullet points",
                answer_format="<Interview Question>,• <Candidate Response>",
                input_text=transcript_text,  # Pass transcript_text to summarize
                max_output_size=4000,
                final_model='anthropic/claude-3-5-sonnet'
            )
        else:  # Use Lemur with transcript ID
            transcript_group = aai.TranscriptGroup.get_by_ids([transcript_id])  
            result = transcript_group.lemur.summarize(
                context="list the questions the interviewer asked the candidate. for each interview question, list the candidate response in bullet points",
                answer_format="<Interview Question>,• <Candidate Response>",
                max_output_size=4000,
                final_model='anthropic/claude-3-5-sonnet'
            )
        return result.response
    except RetryError:
        # Handle the case when all retries are used
        print("All retries used. Returning empty string.")
        return ''
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Re-running LeMUR Request")
        try:
            if '429' in e:
                sleep(60)
        except: pass
        raise

@retry(wait_fixed=1000, stop_max_attempt_number=10)
def generate_question_answer(transcript_id, api_key, transcript_text=None):  # Add transcript_text parameter
    try:
        if transcript_text:  # Use Lemur with input text
            # ask some questions
            questions = [
                aai.LemurQuestion(question="what role is the candidate interviewing for?"),
                aai.LemurQuestion(question="what is the candidate's relevant skills or background?"),
                aai.LemurQuestion(question="how many years of relevant experience does the candidate? provide context for your answer?",answer_options=["1-3","4-7","more than 7","Unknown"]),
                aai.LemurQuestion(question="what are the candidate's strengths and weaknesses?"),
                aai.LemurQuestion(question="what questions did the candidate ask the interviewer?",answer_format="bullet points"),
            ]  
            result = aai.Lemur().question(questions, input_text=transcript_text)  # Pass transcript_text to question
        else:  # Use Lemur with transcript ID
            aai.settings.api_key = api_key
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
    except RetryError:
        # Handle the case when all retries are used
        print("All retries used. Returning empty list.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Re-running LeMUR Request")
        try:
            if '429' in e:
                sleep(60)
        except: pass
        raise

def parse_json(response_string):
    # Remove newline characters
    response_string = response_string.replace('\n', ' ')

    start_index = response_string.find('[')
    end_index = response_string.rfind(']') + 1
    # Check if both '[' and ']' are present in the response_string
    if start_index == -1 or end_index == 0:
        return []  # Return an empty array if either '[' or ']' is not present
    json_content = response_string[start_index:end_index]
    try:
        response_json = json.loads(json_content)
        return response_json
    except json.JSONDecodeError as e:
        # # errors are irrelevant, moves on if not found
        print(f"Error decoding JSON: {e}")
        return [] 

def calculateQualityScore(arr):
    points = 0
    total = 0
    for n in arr:
        try:
            grade = int(n['grade'])
            total += 5
            points += grade
        except:
            pass  # If grade is not convertible to int, do nothing
    if total == 0:
        return 0  # Avoid division by zero
    return points / total


# Initialize session_state if it doesn't exist
if 'api_key' not in st.session_state:
    st.session_state.api_key = ''
if 'homepage' not in st.session_state:
    st.session_state.homepage = True
if 'complete' not in st.session_state:
    st.session_state.complete = False
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
    api_key = st.text_input('Enter your AssemblyAI API key: ', value=st.session_state.api_key, type='password')
    aai.settings.api_key = api_key
    st.session_state.api_key = api_key

    # File
    st.write('Provide either a transcript id, url of your interview file, a local file, or enter the transcript text directly.')
    transcript_id_input = st.text_input('Enter your transcript id', '')
    local_file = st.file_uploader('Or upload your interview audio/video transcript', accept_multiple_files=False)
    url_input = st.text_input('Or enter the URL of interview transcript', '')
    transcript_text = st.text_area('Or enter the transcript text directly', '')

    # jd and skills
    st.write('Enter job description and skills list')
    job_description = st.text_area('Enter your job description')
    skills = st.text_area('Enter the Skills List:')

    button = st.button('Submit')
    if button:
        if transcript_id_input == '' and local_file is None and url_input == '' and transcript_text == '':
            st.write('Please input a file, URL, or transcript text.')
        else:
            st.session_state.homepage = False
            st.session_state.transcript_id_input = transcript_id_input
            st.session_state.local_file = local_file
            st.session_state.url_input = url_input
            st.session_state.job_description = job_description
            st.session_state.skills = skills
            st.session_state.transcript_text = transcript_text
            st.rerun()
else: #running or complete page
    api_key = st.session_state.api_key
    if st.session_state.complete == False:
        st.write('')
        with st.spinner('Loading...'):
            transcript_id_input = st.session_state.transcript_id_input
            local_file = st.session_state.local_file
            url_input = st.session_state.url_input
            job_description = st.session_state.job_description
            skills = st.session_state.skills
            transcript_text = st.session_state.transcript_text

            if transcript_id_input != '':
                transcript_id = transcript_id_input
            elif local_file is not None:
                file_bytes = local_file.read()
                file_extension = Path(local_file.name).suffix
                with open(f'temp_file{file_extension}', 'wb') as temp_file:
                    temp_file.write(file_bytes)
                transcript_id = transcribe_file(f'temp_file{file_extension}')
            elif url_input != '':
                transcript_id = transcribe_file(url_input)
            elif transcript_text != '':
                # If transcript text is provided, we don't need to transcribe
                st.session_state.transcript_text = transcript_text
                # Create a temporary transcript ID
                transcript_id = 'temp_transcript_id'
            else:
                st.write('Please input a file, URL, or transcript text.')
                st.stop()

            if transcript_text == '':
                st.session_state.transcript_text = aai.Transcript.get_by_id(transcript_id).text
            
            print('starting q_a_request')
            q_and_a_arr = get_questions(transcript_id, job_description, api_key, st.session_state.transcript_text)  # Pass transcript_text to get_questions
            print(q_and_a_arr)

            with ThreadPoolExecutor() as executor:
                future_1 = executor.submit(candidate_quality_assessment, transcript_id, job_description, skills, api_key, q_and_a_arr, st.session_state.transcript_text)  # Pass transcript_text to candidate_quality_assessment
                future_2 = executor.submit(interviewer_quality_assessment, transcript_id, job_description, skills, api_key, q_and_a_arr, st.session_state.transcript_text)  # Pass transcript_text to interviewer_quality_assessment
                future_7 = executor.submit(get_skills, transcript_id, job_description, skills, api_key, q_and_a_arr, st.session_state.transcript_text)  # Pass transcript_text to get_skills
                future_3 = executor.submit(generate_summary_paragraph, transcript_id, api_key, st.session_state.transcript_text)  # Pass transcript_text to generate_summary_paragraph
                future_4 = executor.submit(generate_summary_topics, transcript_id, api_key, st.session_state.transcript_text)  # Pass transcript_text to generate_summary_topics
                future_6 = executor.submit(generate_question_answer, transcript_id, api_key, st.session_state.transcript_text)  # Pass transcript_text to generate_question_answer

            skills = future_7.result()
            temp_candidate_assessment = future_1.result()
            temp_interviewer_audit = future_2.result()

            for i in range(len(temp_candidate_assessment)):
                try:
                    skill = skills[i]['skill']
                    temp_candidate_assessment[i]['skill'] = skill
                    temp_interviewer_audit[i]['skill'] = skill
                except: pass

            st.session_state.parsed_candidate_assessment = temp_candidate_assessment
            st.session_state.parsed_interviewer_audit = temp_interviewer_audit
            
            st.session_state.summary_paragraph = future_3.result()
            st.session_state.summary_topics = future_4.result()
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
        st.session_state.parsed_candidate_assessment = []
        st.session_state.parsed_interviewer_audit = []
        st.session_state.summary_paragraph = ''
        st.session_state.summary_topics = ''
        st.session_state.question_answer = ''
        st.rerun()

    st.subheader('Transcript Text:')
    stx.scrollableTextbox(st.session_state.transcript_text)
    st.markdown('\n' * 1)

    option = st_btn_select.st_btn_select(('Paragraph Summary', 'Topic Summary', 'Basic Question-Answer', 'Candidate Assessment', 'Interviewer Assessment'), index=0)
    
    if option == 'Candidate Assessment':
        st.subheader('Candidate Assessment')
        for q in st.session_state.parsed_candidate_assessment:
            st.markdown('~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ')
            st.write('Question: ' + q['question'])
            st.write('Answer: ' + q['answer'])
            st.write('Skill: ' + q['skill'])
            st.write('Grade: ' + str(q['grade']))
        st.markdown('~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ')
        st.write('Quality Score: '+str(calculateQualityScore(st.session_state.parsed_candidate_assessment)*100))
        st.write('Quality score formula: (total points)/(5 * # of questions *)')

    if option == 'Interviewer Assessment':
        st.subheader('Interviewer Assessment')
        for q in st.session_state.parsed_interviewer_audit:
            st.markdown('~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ')
            st.write('Question: ' + q['question'])
            st.write('Grade: ' + str(q['grade']))
            st.write('Skill: ' + q['skill'])
        st.markdown('~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ')
        st.write('Quality Score: '+str(calculateQualityScore(st.session_state.parsed_interviewer_audit)*100))
        st.write('Quality score formula: (total points)/(5 * # of questions *)')

    if option == 'Paragraph Summary':
        st.subheader('Paragraph Summary')
        st.write(st.session_state.summary_paragraph)

    if option == 'Topic Summary':
        st.subheader('Topic Summary')
        st.write(st.session_state.summary_topics)

    if option == 'Basic Question-Answer':
        st.subheader('Basic Question-Answer')
        for q in st.session_state.question_answer:
            st.write(f'{q.question}')
            st.write(f'Answer: {q.answer}')
            st.write()