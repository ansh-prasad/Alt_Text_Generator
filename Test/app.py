import os
import fitz  # PyMuPDF
from flask import Flask, request, render_template, send_from_directory
import google.generativeai as genai
from base64 import b64encode
from dotenv import load_dotenv

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file!")
genai.configure(api_key=API_KEY)

UPLOAD_FOLDER = "static"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def pdf_to_images(pdf_path, output_folder):
    image_paths = []
    pdf_document = None
    try:
        pdf_document = fitz.open(pdf_path)
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            pix = page.get_pixmap(dpi=300)
            output_file = os.path.join(output_folder, f"page_{page_num + 1}.png")
            pix.save(output_file)
            image_paths.append(output_file)
        
        return image_paths
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return image_paths
    finally:
        if pdf_document is not None:
            pdf_document.close()

def generate_alt_text(image_path):
    try:
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
            image_base64 = b64encode(image_data).decode("utf-8")
        
        prompt = "Generate alternative text (alt text) describing any figures, diagrams, or illustrations in this image. List each figure separately with 'Figure X:' followed by its description (e.g., 'Figure 1: An aerial view...'). If no figures are present, return 'No figures present in the image.'"
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content([
            {"mime_type": "image/png", "data": image_base64},
            {"text": prompt}
        ])
        
        alt_text = response.text.strip()
        if alt_text == "No figures present in the image.":
            return [alt_text]
        
        # Split the response into individual figure descriptions
        figures = []
        for line in alt_text.split("\n"):
            line = line.strip()
            if line.startswith("Figure ") and ":" in line:
                figures.append(line)
        if not figures:
            return ["No figures present in the image."]
        return figures
    except Exception as e:
        return [f"Error generating alt text: {str(e)}"]

@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        if "file" not in request.files:
            return render_template("upload.html", error="No file part")
        file = request.files["file"]
        if file.filename == "":
            return render_template("upload.html", error="No file selected")
        if file and file.filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(pdf_path)
            
            # Process PDF and generate alt text
            output_folder = os.path.join(app.config["UPLOAD_FOLDER"], "extracted_pages")
            image_paths = pdf_to_images(pdf_path, output_folder)
            results = []
            figure_count = 0
            
            for img_path in image_paths:
                alt_texts = generate_alt_text(img_path)
                relative_path = os.path.relpath(img_path, app.config["UPLOAD_FOLDER"])
                # Store all alt texts for this image
                results.append({"path": relative_path, "alt_texts": alt_texts})
                # Count figures (exclude "No figures" and errors)
                for alt_text in alt_texts:
                    if not alt_text.startswith("No figures") and not alt_text.startswith("Error"):
                        figure_count += 1
            
            # Clean up uploaded PDF
            os.remove(pdf_path)
            
            return render_template("results.html", images=results, figure_count=figure_count)
        return render_template("upload.html", error="Please upload a PDF file")
    return render_template("upload.html")

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

if __name__ == "__main__":
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)