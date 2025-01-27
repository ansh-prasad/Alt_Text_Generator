import os
import base64
import time
import fitz  # PyMuPDF
from flask import Flask, render_template, request, redirect, url_for
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image
from io import BytesIO

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'temp_uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash-latest')

ALT_TEXT_PROMPT = """Analyze this scientific figure and create detailed alt text including:
1. Figure type (chart, diagram, microscopy, etc.)
2. Main components and their spatial relationships
3. Key annotations/text (preserve mathematical notation)
4. Data representation method
5. Significant color coding if present
Use concise, descriptive language under 280 characters. Structure as:
[Type]: [Brief description]. Key elements: [List]. Notable features: [Details]."""

def validate_and_convert_image(image_bytes):
    """Convert image to JPEG format and validate integrity"""
    try:
        img = Image.open(BytesIO(image_bytes))
        
        # Convert to RGB for JPEG compatibility
        if img.mode in ('RGBA', 'P', 'CMYK'):
            img = img.convert('RGB')
            
        # Resize if too large (max 4096px on any side)
        max_size = 4096
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size))
            
        # Convert to JPEG bytes
        output_buffer = BytesIO()
        img.save(output_buffer, format='JPEG', quality=85)
        return output_buffer.getvalue(), 'image/jpeg'
        
    except Exception as e:
        print(f"Image validation failed: {str(e)}")
        return None, None

def generate_alt_text(image_bytes, max_retries=3):
    """Generate alt text with robust image handling"""
    for attempt in range(max_retries):
        try:
            # Validate and convert image
            processed_image, mime_type = validate_and_convert_image(image_bytes)
            if not processed_image:
                return "Invalid image format - could not process"
                
            # Create data URL
            encoded_image = base64.b64encode(processed_image).decode("utf-8")
            image_data = f"data:{mime_type};base64,{encoded_image}"
            
            response = model.generate_content(
                contents=[ALT_TEXT_PROMPT, image_data],
                generation_config={
                    "temperature": 0.3,
                    "top_p": 0.95,
                    "max_output_tokens": 400
                }
            )
            
            if response.prompt_feedback.block_reason:
                return f"Content blocked: {response.prompt_feedback.block_reason.name}"
                
            return response.text.strip().replace("**", "").replace("*", "")
            
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt + 5
                time.sleep(wait_time)
                continue
            return f"API Error: {str(e)}"

def process_pdf(pdf_path):
    """Process PDF with enhanced image validation"""
    doc = fitz.open(pdf_path)
    results = []
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        images = page.get_images(full=True)
        
        for img_index, img in enumerate(images):
            xref = img[0]
            base_image = doc.extract_image(xref)
            
            if not base_image.get("image"):
                continue
                
            try:
                # Generate preview (original image)
                preview = base64.b64encode(base_image["image"]).decode("utf-8")
                preview = f"data:image/jpeg;base64,{preview}"
                
                # Generate alt text with validated image
                alt_text = generate_alt_text(base_image["image"])
                
                results.append({
                    "page": page_num + 1,
                    "position": img_index + 1,
                    "alt_text": alt_text,
                    "preview": preview
                })
                
            except Exception as e:
                print(f"Error processing image {img_index} on page {page_num}: {str(e)}")
                continue
    
    doc.close()
    return results

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'pdf' not in request.files:
            return redirect(url_for('index'))
            
        pdf_file = request.files['pdf']
        if not pdf_file or pdf_file.filename == '':
            return redirect(url_for('index'))
            
        if not pdf_file.filename.lower().endswith('.pdf'):
            return "Invalid file type - PDF required", 400
            
        try:
            # Create upload directory if not exists
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            # Create unique temporary filename
            timestamp = int(time.time())
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{timestamp}.pdf")
            pdf_file.save(pdf_path)
            
            # Process PDF
            results = process_pdf(pdf_path)
            
            return render_template('results.html', results=results)
            
        except Exception as e:
            return f"Processing Error: {str(e)}", 500
            
        finally:
            # Cleanup temporary file
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
    
    return render_template('upload.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)