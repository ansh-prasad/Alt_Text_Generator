import os
import hashlib
import fitz  # PyMuPDF
from flask import Flask, render_template, request, redirect, url_for, Response
from werkzeug.utils import secure_filename
import google.generativeai as genai
from PIL import Image
import io
from dotenv import load_dotenv
from itertools import cycle
import json

load_dotenv()

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
app.config['EXTRACTED_FOLDER'] = '/tmp/extracted_images'

API_KEYS = [
    os.getenv("GEMINI_API_KEY1"),
    os.getenv("GEMINI_API_KEY2"),
    os.getenv("GEMINI_API_KEY3")
]
api_key_iterator = cycle(API_KEYS)

if not all(API_KEYS):
    raise ValueError("All three GEMINI_API_KEYs must be provided in environment variables")

# Ensure tmp directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['EXTRACTED_FOLDER'], exist_ok=True)

class GeminiAPIClient:
    def __init__(self):
        self.switch_api_key()

    def switch_api_key(self):
        api_key = next(api_key_iterator)
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

def generate_alt_text(image_path, client):
    try:
        with open(image_path, 'rb') as img_file:
            img = Image.open(img_file)
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format=img.format)
            img_bytes = img_byte_arr.getvalue()
        
        response = client.model.generate_content([
            "Provide a detailed description of this image for alt text purposes",
            {"mime_type": f"image/{img.format.lower()}", "data": img_bytes}
        ])
        return response.text
    except Exception as e:
        return f"Image description: Unable to generate alt text due to {str(e)}"

def extract_images_from_pdf(pdf_path, output_folder):
    try:
        pdf_document = fitz.open(pdf_path)
        total_images = sum(len(page.get_images(full=True)) for page in pdf_document)
        image_count = 0
        seen_image_hashes = set()
        client = GeminiAPIClient()
        extracted_images = []
        
        for page_num in range(pdf_document.page_count):
            page = pdf_document[page_num]
            image_list = page.get_images(full=True)
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = pdf_document.extract_image(xref)
                image_bytes = base_image["image"]
                image_hash = hashlib.md5(image_bytes).hexdigest()
                
                if image_hash in seen_image_hashes:
                    continue
                
                seen_image_hashes.add(image_hash)
                image_ext = base_image["ext"]
                output_file = os.path.join(output_folder, f"image_{image_count}_{page_num + 1}.{image_ext}")
                
                with open(output_file, "wb") as image_file:
                    image_file.write(image_bytes)
                
                alt_text = generate_alt_text(output_file, client)
                client.switch_api_key()
                
                extracted_images.append({
                    'path': output_file,
                    'alt_text': alt_text
                })
                image_count += 1
                progress = (image_count / total_images) * 100 if total_images > 0 else 100
                yield f"data: {json.dumps({'progress': progress, 'completed': False})}\n\n"
        
        pdf_document.close()
        yield f"data: {json.dumps({'progress': 100, 'completed': True, 'images': extracted_images})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

@app.route('/', methods=['GET', 'POST'])
def upload_pdf():
    if request.method == 'POST':
        if 'pdf_file' not in request.files:
            return redirect(request.url)
        
        pdf_file = request.files['pdf_file']
        if pdf_file.filename == '':
            return redirect(request.url)
        
        filename = secure_filename(pdf_file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        pdf_file.save(file_path)
        app.config['CURRENT_FILE'] = file_path
        return redirect(url_for('process_pdf'))
    
    return render_template('upload.html')

@app.route('/process')
def process_pdf():
    file_path = app.config.get('CURRENT_FILE')
    if not file_path or not os.path.exists(file_path):
        return Response(f"data: {json.dumps({'error': 'No file uploaded or file not found'})}\n\n", mimetype='text/event-stream')
    
    return Response(extract_images_from_pdf(file_path, app.config['EXTRACTED_FOLDER']), mimetype='text/event-stream')

@app.route('/results')
def results():
    return render_template('results.html')

# Vercel handler
def handler(request):
    return app(request.environ, request.start_response)