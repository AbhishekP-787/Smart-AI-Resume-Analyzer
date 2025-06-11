# 🧠 Smart AI Resume Analyzer

An intelligent resume screening web application built using **Streamlit** and **Machine Learning**. This tool automatically analyzes resumes to extract key details, match skills to job roles, and provide candidate recommendations — ideal for recruiters or HR automation systems.

---

## 🚀 Features

- 📄 **Resume Parsing** – Extracts name, contact, education, experience, and skills
- 🤖 **Machine Learning Scoring** – Evaluates resumes based on trained models
- 🔍 **Skill Matching** – Matches resumes to suitable job profiles using NLP
- 📊 **Streamlit UI** – Clean, interactive interface for uploading and analyzing resumes
- 📁 **Multiple Formats Supported** – PDF and DOCX resume uploads

---

## 🎯 Use Cases

- HR tech for automated candidate screening  
- Career portals and job boards  
- University placement cells  
- Personal projects showcasing ML + NLP

---

## 🛠 Tech Stack

- **Frontend**: Streamlit  
- **Backend**: Python 3, scikit-learn, spaCy, NLTK, Pandas  
- **IDE**: Visual Studio Code  
- **Other Tools**: Resume Parser, Pretrained ML Models  

---

## 📁 Project Structure

📦 Smart-AI-Resume-Analyzer/
├── app.py # Main Streamlit app
├── models/ # Machine learning model files
├── resume_samples/ # Sample resumes (PDF/DOCX)
├── utils/ # Helper functions and scripts
├── requirements.txt # Python dependencies
└── README.md # Project documentation


---

## ⚙️ Installation & Usage

### 🔧 Prerequisites

- Python 3.7+
- pip
- Git
- Virtualenv (optional but recommended)

### 📥 1. Clone the Repository

```bash
git clone https://github.com/AbhishekP-787/Smart-AI-Resume-Analyzer.git
cd Smart-AI-Resume-Analyzer

## Create Virtual Environment

python -m venv venv
# Activate:
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

## Install Dependencies
pip install -r requirements.txt

## Run the applicaton
streamlit run app.py
