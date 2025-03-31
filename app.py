from flask import Flask, request, jsonify, render_template
import os
import PyPDF2
from werkzeug.utils import secure_filename
from google import genai
from google.genai import types
import google.generativeai as genai

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

#Gemini client
genai.configure(api_key="ADD YOUR API KEY HERE")
MODEL_ID = "gemini-2.0-flash"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def analyze_with_gemini(text_content):
    
    try:
        # Combine all text content
        combined_text = " ".join(text_content)
        
        # Create a prompt for topic extraction and analysis
        prompt = f"""
        Based on the following document text, please:
        1. Identify the 3-5 most important topics or themes
        2. For each topic, provide a detailed explanation with key points
        3. Format your response in a clear, organized manner

        Document text:
        {combined_text[:10000]}  # Limiting text length to avoid token limits
        """
        
        generation_config = {
            "temperature": 0.2,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 2048,
        }
        
        model = genai.GenerativeModel(
            model_name=MODEL_ID,
            generation_config=generation_config,
        )
        
        response = model.generate_content(prompt)
        
        analysis_text = response.text
        
        return {
            'success': True,
            'analysis': analysis_text
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
def extract_pdf_content(filepath):
    """Extract text content from PDF file"""
    text_content = []
    try:
        with open(filepath, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            num_pages = len(reader.pages)
            
            # Extract text from each page
            for page_num in range(num_pages):
                page = reader.pages[page_num]
                text = page.extract_text()
                if text is None:
                    text = "" 
                text_content.append(text)
            
            analysis_result = analyze_with_gemini(text_content)
            
            if analysis_result['success']:
                return {
                    'success': True,
                    'num_pages': num_pages,
                    'content': text_content,
                    'analysis': analysis_result['analysis']
                }
            else:
                return {
                    'success': True,
                    'num_pages': num_pages,
                    'content': text_content,
                    'analysis': f"Analysis failed: {analysis_result['error']}"
                }
                
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file part'})
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'})
    
    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            file_size = os.path.getsize(filepath)
            
            # Extract content from PDF
            pdf_data = extract_pdf_content(filepath)
            
            if pdf_data['success']:
                content = [str(text) for text in pdf_data['content']]
                
                return jsonify({
                    'success': True,
                    'filename': filename,
                    'size': file_size,
                    'pages': pdf_data['num_pages'],
                    'content': content,
                    'analysis': pdf_data.get('analysis', 'No analysis available')
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f"File uploaded but content extraction failed: {pdf_data['error']}"
                })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    else:
        return jsonify({'success': False, 'error': 'Invalid file type. Only PDF files are allowed.'})

if __name__ == '__main__':
    app.run(debug=True)
