from flask import Flask, request, jsonify
import pdfplumber
import docx
import os
import requests
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def extract_text(file_path):
    if file_path.endswith('.pdf'):
        with pdfplumber.open(file_path) as pdf:
            return " ".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    elif file_path.endswith('.docx'):
        doc = docx.Document(file_path)
        return " ".join([para.text for para in doc.paragraphs])
    return ""

def analyze_with_deepseek(cv_text, jd_text):
    api_url = "https://api.deepseek.com/v1/chat/completions"  # Replace with actual Deepseek API URL
    api_key = "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"  # Replace with your actual Deepseek API Key
    
    prompt = f"""Analyze the provided candidate CV and client job description with a focus on accuracy. 
    Generate a structured comparison table that evaluates the candidate's fitness for the job based on key factors: 
    skills, experience, education, certifications, and additional preferences. Assign precise weightage to each factor, 
    ensuring that critical job requirements impact the fit percentage more than secondary criteria. 
    Highlight exact matches, partial matches, and gaps. The final fit percentage must be calculated based on a weighted 
    evaluation model. Provide insights on strengths and improvement areas and point by point JD percentage if it matches 
    the Candidate CV and what they are missing.
    
    Candidate CV:
    {cv_text}
    
    Job Description:
    {jd_text}
    """
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",  # Ensure this is the correct model name
        "messages": [{"role": "system", "content": "You are an AI specializing in resume and job description analysis."},
                     {"role": "user", "content": prompt}]
    }
    
    response = requests.post(api_url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json().get("choices", [{}])[0].get("message", {}).get("content", "Analysis failed.")
    else:
        return "Error: Unable to process request with Deepseek API."

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'cv' not in request.files or 'job_desc' not in request.files:
        return jsonify({'error': 'Both CV and Job Description are required'}), 400
    
    cv_file = request.files['cv']
    jd_file = request.files['job_desc']
    
    if cv_file.filename == '' or jd_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    cv_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(cv_file.filename))
    jd_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(jd_file.filename))
    
    cv_file.save(cv_path)
    jd_file.save(jd_path)
    
    cv_text = extract_text(cv_path)
    jd_text = extract_text(jd_path)
    
    if not cv_text or not jd_text:
        return jsonify({'error': 'Could not extract text from files'}), 400
    
    deepseek_analysis = analyze_with_deepseek(cv_text, jd_text)
    
    response = {
        'deepseek_analysis': deepseek_analysis
    }
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)
