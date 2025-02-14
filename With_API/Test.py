import google.generativeai as genai
import logging
import os
from docx import Document
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

def extract_figures_from_docx(docx_path, media_folder):
    doc = Document(docx_path)
    images = []
    os.makedirs(media_folder, exist_ok=True)
    
    for shape in doc.inline_shapes:
        if shape._inline.graphic.graphicData.pic:
            image_data = shape._inline.graphic.graphicData.pic.blipFill.blip.embed
            image_part = doc.part.related_parts[image_data]
            image_bytes = image_part.blob
            
            image_path = os.path.join(media_folder, f"figure_{len(images)+1}.png")
            with open(image_path, "wb") as img_file:
                img_file.write(image_bytes)
            
            images.append(image_path)
    
    return images

def analyze_images_with_gemini(api_key, image_paths):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name="gemini-1.5-flash")
    
    responses = []
    for i, image_path in enumerate(image_paths[:10]):  # Limit to 10 images to prevent overload
        try:
            with open(image_path, "rb") as img_file:
                img_bytes = img_file.read()
                
            response = model.generate_content([
                {"parts": [
                    {"text": "Describe the figure in this document."},
                    {"inline_data": {"mime_type": "image/png", "data": img_bytes}}
                ]}
            ])
            
            responses.append(response.text if response and response.text else "No description available.")
        except Exception as img_error:
            responses.append(f"Error processing image {i+1}: {img_error}")
    
    return responses

def count_figures_with_gemini(api_key):
    try:
        while True:
            docx_path = input("Enter the path of the DOCX file (or type 'exit' to quit): ")
            if docx_path.lower() == "exit":
                print("Exiting the program.")
                break
            
            media_folder = "media"
            
            try:
                image_paths = extract_figures_from_docx(docx_path, media_folder)
                actual_count = len(image_paths)
                print(f"The document contains {actual_count} detected figures.")
                
                if image_paths:
                    descriptions = analyze_images_with_gemini(api_key, image_paths)
                    for idx, desc in enumerate(descriptions, start=1):
                        print(f"Figure {idx}: {desc}")
            except Exception as file_error:
                print("Error processing the file:", file_error)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: Missing API key. Please set GEMINI_API_KEY in the .env file.")
    else:
        count_figures_with_gemini(api_key)
