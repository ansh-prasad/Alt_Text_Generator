import os
import hashlib
import fitz  # PyMuPDF
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
import google.generativeai as genai
from PIL import Image
import io
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure Gemini API using environment variable
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['EXTRACTED_FOLDER'] = 'static/extracted_images'

# Initialize Gemini model with updated model name
model = genai.GenerativeModel('gemini-1.5-flash')  # Updated to newer model

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
if not os.path.exists(app.config['EXTRACTED_FOLDER']):
    os.makedirs(app.config['EXTRACTED_FOLDER'])

def generate_alt_text(image_path):
    """Generate alt text for an image using Gemini API"""
    try:
        # Open and prepare image for Gemini
        with open(image_path, 'rb') as img_file:
            img = Image.open(img_file)
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format=img.format)
            img_bytes = img_byte_arr.getvalue()
        
        # Generate alt text
        response = model.generate_content([
            "Provide a detailed description of this image for alt text purposes",
            {"mime_type": f"image/{img.format.lower()}", "data": img_bytes}
        ])
        
        return response.text
    except Exception as e:
        return f"Image description: Unable to generate alt text due to {str(e)}"

def extract_images_from_pdf(pdf_path, output_folder):
    pdf_document = fitz.open(pdf_path)
    image_count = 0
    seen_image_hashes = set()
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
            
            # Generate alt text for this image
            alt_text = generate_alt_text(output_file)
            extracted_images.append({
                'path': output_file,
                'alt_text': alt_text
            })
            image_count += 1
    
    pdf_document.close()
    return extracted_images

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
        
        images = extract_images_from_pdf(file_path, app.config['EXTRACTED_FOLDER'])
        return render_template('results.html', images=images)
    
    return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True)