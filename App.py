import streamlit as st
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import re
import pandas as pd
import base64
import time
import datetime
from pdfminer3.layout import LAParams
from pdfminer3.pdfpage import PDFPage
from pdfminer3.pdfinterp import PDFResourceManager
from pdfminer3.pdfinterp import PDFPageInterpreter
from pdfminer3.converter import TextConverter
import io
import random
from streamlit_tags import st_tags
from PIL import Image
import pymysql
from Courses import ds_course, web_course, android_course, ios_course, uiux_course
import pafy
import plotly.express as px
import yt_dlp
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# Download NLTK data
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab')
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

def fetch_yt_video(link):
    ydl_opts = {
        'quiet': True,
        'force_generic_extractor': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(link, download=False)
            return info_dict.get('title', 'No title found')
    except Exception as e:
        print(f"Error fetching video title: {e}")
        return "Error fetching title"

def get_table_download_link(df, filename, text):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href

def clean_extracted_text(text):
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'(?<=\b[A-Z]) (?=[A-Z])', '', text)  # Converts "E X P E R I E N C E" → "EXPERIENCE"
    return text.strip()

def pdf_reader(file):
    """Extracts and cleans text from PDF."""
    resource_manager = PDFResourceManager()
    fake_file_handle = io.StringIO()
    converter = TextConverter(resource_manager, fake_file_handle, laparams=LAParams())
    page_interpreter = PDFPageInterpreter(resource_manager, converter)
    with open(file, 'rb') as fh:
        for page in PDFPage.get_pages(fh, caching=True, check_extractable=True):
            page_interpreter.process_page(page)
    text = fake_file_handle.getvalue()
    converter.close()
    fake_file_handle.close()
    return clean_extracted_text(text)

def extract_skills(resume_text):
    """Extract skills from resume text using NLTK."""
    stop_words = set(stopwords.words('english'))
    tokens = word_tokenize(resume_text.lower())
    skill_keywords = [
        'python', 'java', 'javascript', 'react', 'django', 'flask', 'tensorflow', 'keras', 'pytorch',
        'machine learning', 'deep learning', 'data science', 'android', 'ios', 'flutter', 'kotlin',
        'swift', 'ui', 'ux', 'figma', 'adobe xd', 'photoshop', 'illustrator', 'sql', 'mysql', 'mongodb',
        'node js', 'angular js', 'c#', 'laravel', 'wordpress', 'xml', 'kivy', 'cocoa', 'xcode'
    ]
    extracted_skills = [token for token in tokens if token in skill_keywords and token not in stop_words]
    return list(set(extracted_skills))  # Remove duplicates

def extract_education(text):
    """Extract degree names and determine eligibility based solely on degree."""
    # Define eligible and non-eligible degrees (lowercase for matching)
    eligible_degrees = [
        'be', 'b.e', 'b.tech', 'bachelor of engineering', 
        'm.tech', 'master of technology', 'master of engineering'
    ]
    not_eligible_degrees = [
        'ba', 'bba', 'bcom', 'mba', 'ma', 'mcom', 
        'business administration', 'bachelor of arts',
        'master of arts', 'bachelor of commerce'
    ]
    # Regex to extract degree phrases
    degree_pattern = r'(?i)\b(' + '|'.join(eligible_degrees + not_eligible_degrees) + r')\b'
    found_degrees = re.findall(degree_pattern, text.lower())
    found_degrees = [deg.lower() for deg in found_degrees]
    # Remove duplicates
    found_degrees = list(set(found_degrees))
    # Determine eligibility
    is_eligible = any(deg in eligible_degrees for deg in found_degrees)
    is_not_eligible = any(deg in not_eligible_degrees for deg in found_degrees)
    # Decide which degree to display
    degree_found = ""
    if is_eligible:
        for deg in eligible_degrees:
            if deg in found_degrees:
                degree_found = deg
                break
    elif is_not_eligible:
        for deg in not_eligible_degrees:
            if deg in found_degrees:
                degree_found = deg
                break
    else:
        degree_found = "No recognized degree found"
    return {
        'qualifications': found_degrees,
        'is_eligible': is_eligible,
        'degree_found': degree_found,
        'status': "QUALIFIED" if is_eligible else "NOT QUALIFIED - Non-Engineering Degree"
    }

def count_pdf_pages(file_path):
    """Count the number of pages in a PDF."""
    with open(file_path, 'rb') as fh:
        return len(list(PDFPage.get_pages(fh, caching=True, check_extractable=True)))

def show_pdf(file_path):
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="1000px" style="border:none;" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def course_recommender(course_list):
    st.subheader("**Courses & Certificates🎓 Recommendations**")
    c = 0
    rec_course = []
    no_of_reco = st.slider('Choose Number of Course Recommendations:', 1, 10, 4)
    random.shuffle(course_list)
    for c_name, c_link in course_list:
        c += 1
        st.markdown(f"({c}) [{c_name}]({c_link})")
        rec_course.append(c_name)
        if c == no_of_reco:
            break
    return rec_course

def generate_pdf_report(resume_data, resume_score, reco_field, cand_level, recommended_skills, rec_course):
    """Generate a PDF report of the resume analysis."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica", 12)
    y = 750  # Starting y position
    c.drawString(100, y, "Resume Analysis Report")
    c.setFont("Helvetica-Bold", 14)
    y -= 30
    c.drawString(100, y, f"Name: {resume_data['name']}")
    y -= 20
    c.drawString(100, y, f"Email: {resume_data['email']}")
    y -= 20
    c.drawString(100, y, f"Contact: {resume_data['mobile_number']}")
    y -= 20
    c.drawString(100, y, f"Resume Pages: {resume_data['no_of_pages']}")
    y -= 30
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, y, "Candidate Level:")
    c.setFont("Helvetica", 12)
    y -= 20
    c.drawString(100, y, cand_level)
    y -= 30
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, y, "Extracted Skills:")
    c.setFont("Helvetica", 12)
    y -= 20
    skills_text = ", ".join(resume_data['skills'])
    for line in skills_text.split(", "):
        if y < 50:
            c.showPage()
            y = 750
        c.drawString(100, y, line)
        y -= 20
    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, y, "Recommended Skills:")
    c.setFont("Helvetica", 12)
    y -= 20
    rec_skills_text = ", ".join(recommended_skills)
    for line in rec_skills_text.split(", "):
        if y < 50:
            c.showPage()
            y = 750
        c.drawString(100, y, line)
        y -= 20
    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, y, "Recommended Courses:")
    c.setFont("Helvetica", 12)
    y -= 20
    for course in rec_course:
        if y < 50:
            c.showPage()
            y = 750
        c.drawString(100, y, course)
        y -= 20
    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, y, f"Resume Score: {resume_score}")
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

def send_report_email(recipient_email, resume_data, resume_score, reco_field, cand_level, recommended_skills, rec_course):
    """Send the resume analysis report as a PDF attachment via email."""
    sender_email = "airesumeforce@gmail.com"
    sender_password = "olnr ubyx omeb dbqz"
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    subject = "Your Resume Analysis Report"
    body = f"""
Dear {resume_data['name']},

Thank you for using the Smart Resume Analyzer. Attached is your detailed resume analysis report, including your skills, recommended skills, course recommendations, and resume score.

Best regards,
Smart Resume Analyzer Team
"""
    pdf_buffer = generate_pdf_report(resume_data, resume_score, reco_field, cand_level, recommended_skills, rec_course)
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = recipient_email
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain'))
    pdf_attachment = MIMEApplication(pdf_buffer.getvalue(), _subtype="pdf")
    pdf_attachment.add_header('Content-Disposition', 'attachment', filename="Resume_Analysis_Report.pdf")
    message.attach(pdf_attachment)
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, message.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

try:
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='',
        port=3307,
        charset='utf8mb4'
    )
    cursor = connection.cursor()
except pymysql.err.OperationalError as e:
    st.error(f"Failed to connect to MySQL: {e}")
    st.info("Please ensure MySQL is running and the credentials (username: root, password: 1234, port: 3307) are correct.")
    st.stop()

def insert_data(name, email, res_score, timestamp, no_of_pages, reco_field, cand_level, skills, recommended_skills, courses):
    DB_table_name = 'user_data'
    if not email or email.strip() == "":
        st.error("Email cannot be empty. Please check the uploaded resume.")
        return
    insert_sql = "insert into " + DB_table_name + """
    values (0,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
    rec_values = (name, email, str(res_score), timestamp, str(no_of_pages), reco_field, cand_level, skills, recommended_skills, courses)
    cursor.execute(insert_sql, rec_values)
    connection.commit()

st.set_page_config(
    page_title="Smart Resume Analyzer",
    page_icon='./Logo/SRA_Logo.ico',
)

def run():
    img = Image.open('./Logo/SRA_Logo.jpg')
    img = img.resize((300, 300), Image.Resampling.LANCZOS)
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    st.markdown(
        f"""
        <div style="text-align: center;">
            <img src="data:image/png;base64,{img_base64}" width="300">
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown(
        "<h1 style='text-align: center;'>Smart Resume Analyser</h1>",
        unsafe_allow_html=True
    )
    st.sidebar.markdown("# Choose User")
    activities = ["Normal User", "Admin"]
    choice = st.sidebar.selectbox("Choose among the given options:", activities)
    if choice != "Admin":
        upload_disabled = True
        user_name = st.text_input("Enter your Name:", "", key="user_name_input")
        if not user_name.strip():
            st.warning("Please enter your name to enable resume upload.")
        else:
            st.write(f"**Hello, {user_name}!** 👋")
            upload_disabled = False

    db_sql = """CREATE DATABASE IF NOT EXISTS SRA;"""
    cursor.execute(db_sql)
    connection.select_db("sra")
    DB_table_name = 'user_data'
    table_sql = "CREATE TABLE IF NOT EXISTS " + DB_table_name + """
                    (ID INT NOT NULL AUTO_INCREMENT,
                     Name varchar(100) NOT NULL,
                     Degree VARCHAR(100) NOT NULL,
                     Email_ID VARCHAR(50) NOT NULL,
                     resume_score VARCHAR(8) NOT NULL,
                     Timestamp VARCHAR(50) NOT NULL,
                     Page_no VARCHAR(5) NOT NULL,
                     Predicted_Field VARCHAR(25) NOT NULL,
                     User_level VARCHAR(30) NOT NULL,
                     Actual_skills VARCHAR(300) NOT NULL,
                     Recommended_skills VARCHAR(300) NOT NULL,
                     Recommended_courses VARCHAR(600) NOT NULL,
                     PRIMARY KEY (ID));
                    """
    cursor.execute(table_sql)
    if choice == 'Normal User':
        send_report = st.checkbox("Send Resume Analysis Report to Email")
        pdf_file = st.file_uploader("Choose your Resume", type=["pdf"], disabled=upload_disabled)
        if pdf_file is not None:
            with st.spinner('Uploading your Resume....'):
                time.sleep(4)
            save_image_path = './Uploaded_Resumes/' + pdf_file.name
            with open(save_image_path, "wb") as f:
                f.write(pdf_file.getbuffer())
            show_pdf(save_image_path)
            resume_text = pdf_reader(save_image_path)
            resume_data = {
                'name': user_name,
                'email': extract_email(resume_text),
                'mobile_number': extract_phone(resume_text),
                'skills': extract_skills(resume_text),
                'education': extract_education(resume_text),  # This now returns the full education info
                'no_of_pages': count_pdf_pages(save_image_path)
            }
            if resume_data:
                st.header("**Resume Analysis**")
                st.success("Hello " + user_name)
                st.subheader("**Your Basic info**")
                try:
                    st.text('Name: ' + resume_data['name'])
                    st.text('Email: ' + resume_data['email'])
                    st.text('Contact: ' + resume_data['mobile_number'])
                    st.text('Resume pages: ' + str(resume_data['no_of_pages']))
                except:
                    pass
                st.subheader("**Qualification Status**")
                education_info = resume_data['education']

                # Display eligibility status first
                if education_info['is_eligible']:
                    st.markdown(
                        f"""
                        <div style='background-color: #1ed760; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
                            <h3 style='color: white; margin: 0;'>✅ ELIGIBLE</h3>
                            <p style='color: white; margin: 10px 0 0 0;'>Engineering Degree Found: {education_info['degree_found']}</p>
                            <p style='color: white; margin: 5px 0 0 0;'>Your degree meets our Company requirements.</p>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                else:
                    status_color = "#d73b5c"  # Red for not eligible
                    message = "This position requires an engineering degree (BE/B.Tech/M.Tech)"
                    if education_info['degree_found'] != "No recognized degree found":
                        message = f"Found {education_info['degree_found']}, but this position requires an engineering degree."

                    st.markdown(
                        f"""
                        <div style='background-color: {status_color}; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
                            <h3 style='color: white; margin: 0;'>❌ NOT ELIGIBLE</h3>
                            <p style='color: white; margin: 10px 0 0 0;'>{message}</p>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )

                cand_level = ''
                if resume_data['no_of_pages'] == 1:
                    cand_level = "Fresher"
                    st.markdown('''<h4 style='text-align: left; color: #d73b5c;'>You are looking Fresher.</h4>''', unsafe_allow_html=True)
                elif resume_data['no_of_pages'] == 2:
                    cand_level = "Intermediate"
                    st.markdown('''<h4 style='text-align: left; color: #1ed760;'>You are at intermediate level!</h4>''', unsafe_allow_html=True)
                elif resume_data['no_of_pages'] >= 3:
                    cand_level = "Experienced"
                    st.markdown('''<h4 style='text-align: left; color: #fba171;'>You are at experience level!''', unsafe_allow_html=True)
                st.subheader("**Skills Recommendation💡**")
                keywords = st_tags(label='### Skills that you have', text='See our skills recommendation', value=resume_data['skills'], key='1')
                ds_keyword = ['tensorflow', 'keras', 'pytorch', 'machine learning', 'deep learning', 'flask', 'streamlit']
                web_keyword = ['react', 'django', 'node js', 'react js', 'php', 'laravel', 'magento', 'wordpress', 'javascript', 'angular js', 'c#', 'flask']
                android_keyword = ['android', 'android development', 'flutter', 'kotlin', 'xml', 'kivy']
                ios_keyword = ['ios', 'ios development', 'swift', 'cocoa', 'cocoa touch', 'xcode']
                uiux_keyword = ['ux', 'adobe xd', 'figma', 'zeplin', 'balsamiq', 'ui', 'prototyping', 'wireframes', 'storyframes', 'adobe photoshop', 'photoshop', 'editing', 'adobe illustrator', 'illustrator', 'adobe after effects', 'after effects', 'adobe premier pro', 'premier pro', 'adobe indesign', 'indesign', 'wireframe', 'solid', 'grasp', 'user research', 'user experience']
                recommended_skills = []
                reco_field = ''
                rec_course = ''
                for i in resume_data['skills']:
                    if i.lower() in ds_keyword:
                        reco_field = 'Data Science'
                        st.success("**Our analysis says you are looking for Data Science Jobs.**")
                        recommended_skills = ['Data Visualization', 'Predictive Analysis', 'Statistical Modeling', 'Data Mining', 'Clustering & Classification', 'Data Analytics', 'Quantitative Analysis', 'Web Scraping', 'ML Algorithms', 'Keras', 'Pytorch', 'Probability', 'Scikit-learn', 'Tensorflow', 'Flask', 'Streamlit']
                        recommended_keywords = st_tags(label='### Recommended skills for you.', text='Recommended skills generated from System', value=recommended_skills, key='2')
                        st.markdown('''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h4>''', unsafe_allow_html=True)
                        rec_course = course_recommender(ds_course)
                        break
                    elif i.lower() in web_keyword:
                        reco_field = 'Web Development'
                        st.success("**Our analysis says you are looking for Web Development Jobs**")
                        recommended_skills = ['React', 'Django', 'Node JS', 'React JS', 'php', 'laravel', 'Magento', 'wordpress', 'Javascript', 'Angular JS', 'c#', 'Flask', 'SDK']
                        recommended_keywords = st_tags(label='### Recommended skills for you.', text='Recommended skills generated from System', value=recommended_skills, key='3')
                        st.markdown('''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h4>''', unsafe_allow_html=True)
                        rec_course = course_recommender(web_course)
                        break
                    elif i.lower() in android_keyword:
                        reco_field = 'Android Development'
                        st.success("**Our analysis says you are looking for Android App Development Jobs**")
                        recommended_skills = ['Android', 'Android development', 'Flutter', 'Kotlin', 'XML', 'Java', 'Kivy', 'GIT', 'SDK', 'SQLite']
                        recommended_keywords = st_tags(label='### Recommended skills for you.', text='Recommended skills generated from System', value=recommended_skills, key='4')
                        st.markdown('''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h4>''', unsafe_allow_html=True)
                        rec_course = course_recommender(android_course)
                        break
                    elif i.lower() in ios_keyword:
                        reco_field = 'IOS Development'
                        st.success("** Our analysis says you are looking for IOS App Development Jobs **")
                        recommended_skills = ['IOS', 'IOS Development', 'Swift', 'Cocoa', 'Cocoa Touch', 'Xcode', 'Objective-C', 'SQLite', 'Plist', 'StoreKit', 'UI-Kit', 'AV Foundation', 'Auto-Layout']
                        recommended_keywords = st_tags(label='### Recommended skills for you.', text='Recommended skills generated from System', value=recommended_skills, key='5')
                        st.markdown('''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h4>''', unsafe_allow_html=True)
                        rec_course = course_recommender(ios_course)
                        break
                    elif i.lower() in uiux_keyword:
                        reco_field = 'UI-UX Development'
                        st.success("** Our analysis says you are looking for UI-UX Development Jobs **")
                        recommended_skills = ['UI', 'User Experience', 'Adobe XD', 'Figma', 'Zeplin', 'Balsamiq', 'Prototyping', 'Wireframes', 'Storyframes', 'Adobe Photoshop', 'Editing', 'Illustrator', 'After Effects', 'Premier Pro', 'Indesign', 'Wireframe', 'Solid', 'Grasp', 'User Research']
                        recommended_keywords = st_tags(label='### Recommended skills for you.', text='Recommended skills generated from System', value=recommended_skills, key='6')
                        st.markdown('''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h4>''', unsafe_allow_html=True)
                        rec_course = course_recommender(uiux_course)
                        break
                ts = time.time()
                cur_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                cur_time = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                timestamp = str(cur_date + '_' + cur_time)
                print("Extracted and Cleaned Resume Text:\n", resume_text)
                st.subheader("**Resume Tips & Ideas💡**")
                resume_score = 0
                resume_text_lower = resume_text.lower()
                if "experience" in resume_text_lower or "work experience" in resume_text_lower:
                    resume_score += 20
                    st.markdown("<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Experience</h4>", unsafe_allow_html=True)
                else:
                    st.markdown("<h4 style='text-align: left; color: #fabc10;'>[-] Please add Experience to your resume.</h4>", unsafe_allow_html=True)
                if "summary" in resume_text_lower or "objective" in resume_text_lower:
                    resume_score += 20
                    st.markdown("<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added a Summary</h4>", unsafe_allow_html=True)
                else:
                    st.markdown("<h4 style='text-align: left; color: #fabc10;'>[-] Consider adding a branded Summary section.</h4>", unsafe_allow_html=True)
                if "hobbies" in resume_text_lower or "interests" in resume_text_lower:
                    resume_score += 20
                    st.markdown("<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Hobbies</h4>", unsafe_allow_html=True)
                else:
                    st.markdown("<h4 style='text-align: left; color: #fabc10;'>[-] Consider adding Hobbies or Interests.</h4>", unsafe_allow_html=True)
                if "achievements" in resume_text_lower or "awards" in resume_text_lower:
                    resume_score += 20
                    st.markdown("<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Achievements</h4>", unsafe_allow_html=True)
                else:
                    st.markdown("<h4 style='text-align: left; color: #fabc10;'>[-] Consider adding Achievements.</h4>", unsafe_allow_html=True)
                if "project" in resume_text_lower or "projects" in resume_text_lower:
                    resume_score += 20
                    st.markdown("<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Projects</h4>", unsafe_allow_html=True)
                else:
                    st.markdown("<h4 style='text-align: left; color: #fabc10;'>[-] Consider adding Projects.</h4>", unsafe_allow_html=True)
                st.subheader("**Resume Score📝**")
                st.markdown(
                    """
                    <style>
                        .stProgress > div > div > div > div {
                            background-color: #d73b5c;
                        }
                    </style>""",
                    unsafe_allow_html=True,
                )
                my_bar = st.progress(0)
                score = 0
                for percent_complete in range(1, resume_score + 1):
                    score += 1
                    time.sleep(0.05)
                    my_bar.progress(percent_complete)
                st.success('** Your Resume Writing Score: ' + str(score) + '**')
                st.warning("** Note: This score is calculated based on the content that you have added in your Resume. **")
                st.balloons()
                insert_data(user_name, resume_data['email'], str(resume_score), timestamp,
                            str(resume_data['no_of_pages']), reco_field, cand_level, str(resume_data['skills']),
                            str(recommended_skills), str(rec_course))
                if send_report and resume_data['email']:
                    with st.spinner('Generating and sending your resume analysis report...'):
                        success = send_report_email(resume_data['email'], resume_data, resume_score, reco_field, cand_level, recommended_skills, rec_course)
                        if success:
                            st.success(f"Resume analysis report sent to {resume_data['email']} successfully!")
                        else:
                            st.error("Failed to send the resume analysis report. Please try again later.")
                elif send_report and not resume_data['email']:
                    st.error("Cannot send report: No email address found in the resume.")
                st.header("**Bonus Video for Resume Writing Tips💡**")
                resume_videos = [
                    "https://youtu.be/Tt08KmFfIYQ?si=kVAqqZ2uaR0SAWlu",
                    "https://youtu.be/peiPQzRIxpI?si=uXKCHzxfRogwuAj3",
                    "https://youtu.be/u75hUSShvnc?si=EWBz_FlCyHypl-_s"
                ]
                resume_vid = random.choice(resume_videos)
                res_vid_title = fetch_yt_video(resume_vid)
                st.subheader("✅ **" + res_vid_title + "**")
                st.video(resume_vid)
                st.header("**Bonus Video for Interview👨‍💼 Tips💡**")
                interview_videos = [
                    "https://youtu.be/EzGH3hZuJVk?si=0arCeaDUOlBJ5BEk",
                    "https://youtu.be/kayOhGRcNt4?si=X6fBhEyPvk2obvjm",
                    "https://youtu.be/1mHjMNZZvFo?si=Nqvg7_GvJ-UNWUPx",
                    "https://youtu.be/seVxXHi2YMs?si=_b-haEs1CQtRBAwa"
                ]
                interview_vid = random.choice(interview_videos)
                int_vid_title = fetch_yt_video(interview_vid)
                st.subheader("✅ **" + int_vid_title + "**")
                st.video(interview_vid)
                connection.commit()
            else:
                st.error('Something went wrong..')
    else:
        if 'admin_logged_in' not in st.session_state:
            st.session_state.admin_logged_in = False
        if 'login_attempted' not in st.session_state:
            st.session_state.login_attempted = False
        if not st.session_state.admin_logged_in:
            st.success('Welcome to Admin Side')
            ad_user = st.text_input("Username")
            ad_password = st.text_input("Password", type='password')
            login_clicked = st.button('Login')
            if login_clicked:
                st.session_state.login_attempted = True
                if ad_user and ad_password:
                    if ad_user == 'airesumeteam' and ad_password == 'aiml1234':
                        st.session_state.admin_logged_in = True
                        st.session_state.admin_attempted = False
                        st.success("Welcome Team")
                        st.rerun()
                    else:
                        st.error("Wrong ID & Password Provided")
                else:
                    st.warning("Please enter both Username and Password.")
        if st.session_state.admin_logged_in:
            st.header("📊 **Admin Dashboard**")
            cursor.execute('''SELECT * FROM user_data''')
            data = cursor.fetchall()
            df = pd.DataFrame(columns=['ID', 'Name', 'Email', 'Resume Score', 'Timestamp', 'Total Page',
                                       'Predicted Field', 'User Level', 'Actual Skills', 'Recommended Skills',
                                       'Recommended Course'])
            if data:
                df = pd.DataFrame(data, columns=df.columns)
            else:
                st.warning("📢 No user data available.")
            df['Resume Score'] = pd.to_numeric(df['Resume Score'], errors='coerce')
            st.dataframe(df)
            st.markdown("📥 " + get_table_download_link(df, 'User_Data.csv', 'Download Report'), unsafe_allow_html=True)
            if st.button("🗑️ Delete All User Data"):
                try:
                    cursor.execute("DELETE FROM user_data;")
                    connection.commit()
                    st.success("✅ All user data has been deleted successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error deleting data: {e}")
            query = 'SELECT * FROM user_data;'
            plot_data = pd.read_sql(query, connection)
            st.subheader("📈 **Pie-Chart for Predicted Field Recommendations**")
            if not plot_data.empty:
                fig = px.pie(plot_data, names='Predicted_Field', title='Predicted Field according to the Skills')
                st.plotly_chart(fig)
            st.subheader("📈 **Pie-Chart for User's👨‍💻 Experienced Level**")
            if not plot_data.empty:
                fig = px.pie(plot_data, names='User_level', title="Pie-Chart📈 for User's👨‍💻 Experienced Level")
                st.plotly_chart(fig)
            st.subheader("📧 Sending Emails to Eligible Users")
            eligible_users = df[df['Resume Score'] >= 50]
            st.write(f"Number of users with Resume Score > 50: {len(eligible_users)}")
            unique_emails = eligible_users.drop_duplicates(subset=['Email'])
            sender_email = "airesumeforce@gmail.com"
            sender_password = "olnr ubyx omeb dbqz"
            smtp_server = "smtp.gmail.com"
            smtp_port = 587
            try:
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
                server.login(sender_email, sender_password)
                for index, row in unique_emails.iterrows():
                    recipient_email = row['Email']
                    subject = "Congratulations on Your Resume Score!"
                    body = f"Dear {row['Name']},\n\n" \
                           f"Congratulations! Your resume score is {row['Resume Score']}, which is outstanding. " \
                           f"We recommend you explore the following course: {row['Recommended Course']}.\n\n" \
                           f"Best regards,\nAdmin Team"
                    message = MIMEMultipart()
                    message['From'] = sender_email
                    message['To'] = recipient_email
                    message['Subject'] = subject
                    message.attach(MIMEText(body, 'plain'))
                    server.sendmail(sender_email, recipient_email, message.as_string())
                    st.write(f"Email sent to {row['Name']} at {recipient_email}")
                server.quit()
                st.success("Emails sent successfully!")
            except Exception as e:
                st.error(f"Error while sending emails: {e}")
            st.markdown("---")
            if st.button("🚪 Logout"):
                st.session_state.admin_logged_in = False
                st.success("You have been logged out.")
                st.rerun()

def extract_email(text):
    """Extract email from text using regex."""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(email_pattern, text)
    return match.group(0) if match else ""

def extract_phone(text):
    """Extract phone number from text using regex."""
    phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
    match = re.search(phone_pattern, text)
    return match.group(0) if match else ""

run()