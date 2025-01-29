# app.py
from flask import Flask, render_template, request
import fitz  # PyMuPDF
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration, logging
import os
import uuid

# Suppress unnecessary transformer warnings
logging.set_verbosity_error()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'temp'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

# Initialize BLIP model with memory optimization
try:
    processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    model = BlipForConditionalGeneration.from_pretrained(
        "Salesforce/blip-image-captioning-base",
        low_cpu_mem_usage=True
    )
except Exception as e:
    print(f"Failed to load model: {str(e)}")
    exit(1) 

def generate_alt_text(image_path):
    """Generate alt text using BLIP model with error handling"""
    try:
        # Validate image size first
        with Image.open(image_path) as img:
            if img.size[0] * img.size[1] > 10_000_000:  # 10MP limit
                return "Image too large for processing"
            
            inputs = processor(
                images=img.convert('RGB'),  # Explicit image parameter
                return_tensors="pt",
                padding=True  # Required for batch processing
            )
            
        outputs = model.generate(**inputs, max_length=100)
        return processor.decode(outputs[0], skip_special_tokens=True)
    
    except Exception as e:
        return f"Alt-text generation error: {str(e)}"

def extract_images_from_pdf(pdf_path):
    """Extract images from PDF using PyMuPDF"""
    doc = fitz.open(pdf_path)
    image_data = []
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        images = page.get_images(full=True)
        
        for img_index, img in enumerate(images):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            
            # Generate unique filename
            filename = f"img_{page_num+1}_{img_index}.{image_ext}"
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'static', filename)
            
            # Save image to temp/static
            with open(image_path, "wb") as f:
                f.write(image_bytes)
            
            # Generate alt text
            alt_text = generate_alt_text(image_path)
            image_data.append({
                "page": page_num + 1,
                "filename": filename,
                "alt_text": alt_text,
                "path": image_path
            })
    
    return image_data

# app.py (fixed indentation)
# ... [previous code remains the same]

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'pdf' not in request.files:
            return "No file uploaded", 400
            
        pdf_file = request.files['pdf']
        if pdf_file.filename == '':
            return "No file selected", 400
            
        if not pdf_file.filename.lower().endswith('.pdf'):
            return "Invalid file type", 400
            
        # Save uploaded PDF
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], 'uploaded.pdf')
        pdf_file.save(pdf_path)
        
        # Process PDF
        try:
            results = extract_images_from_pdf(pdf_path)
            return render_template('results.html', images=results)
        except Exception as e:
            return f"Processing error: {str(e)}", 500
        finally:
            # Cleanup: Remove uploaded PDF
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
    
    return render_template('upload.html')

# Fix: Properly indent the main block
if __name__ == '__main__':
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'static'), exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)  # This line MUST be indented


# flask run --host=0.0.0.0 --port=5000