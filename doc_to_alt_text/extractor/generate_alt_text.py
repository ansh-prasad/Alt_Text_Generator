import google.generativeai as genai
from PIL import Image
import io

# Set up the API key
genai.configure(api_key="AIzaSyAjSx9UCghBstQeX0oPJ72egOV5IjUOZCQ")

def generate_alt_text(image_path):
    """Generates alt text for an image using Google Gemini API."""
    model = genai.GenerativeModel("gemini-1.5-flash")  # Switch to the new model

    # Open the image using PIL and keep it open until processing
    with open(image_path, "rb") as img_file:
        img = Image.open(img_file)
        img.load()  # Ensure image is fully loaded before passing

    # Send the image to Gemini API
    response = model.generate_content([img])  # Gemini expects a list of images

    if response and hasattr(response, "text"):
        return response.text.strip()
    return "No alt text generated"
