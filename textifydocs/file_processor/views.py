import os
import uuid
from django.conf import settings
from django.shortcuts import render
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .models import UploadedFile, ExtractedImage
from docx import Document

def upload_file(request):
    extracted_images = ExtractedImage.objects.all()  # Load existing images

    if request.method == "POST" and request.FILES.get("file"):
        file = request.FILES["file"]

        # Save the uploaded DOCX file
        uploaded_file = UploadedFile(file=file)
        uploaded_file.save()

        # Extract images from the DOCX file
        doc_path = uploaded_file.file.path  # Get full path of uploaded file
        doc = Document(doc_path)  # Open DOCX file

        # Find all image relationships in the document
        for rel in doc.part.rels:
            if "image" in doc.part.rels[rel].target_ref:
                image_part = doc.part.rels[rel].target_part
                image_data = image_part.blob

                # Check if this image is referenced as a "Figure"
                is_figure = False
                for p in doc.paragraphs:
                    if "figure" in p.text.lower() or "fig." in p.text.lower():
                        is_figure = True
                        break  # Stop checking after finding one valid reference

                if not is_figure:
                    continue  # Skip images that are NOT figures

                # Generate unique filename
                img_filename = f"{uuid.uuid4()}.jpg"
                img_path = os.path.join(settings.MEDIA_ROOT, "extracted_images", img_filename)

                # Ensure "extracted_images/" folder exists
                os.makedirs(os.path.dirname(img_path), exist_ok=True)

                # Save image to media folder
                with open(img_path, "wb") as img_file:
                    img_file.write(image_data)

                # Save in the database
                extracted_image = ExtractedImage(file=uploaded_file, image=f"extracted_images/{img_filename}")
                extracted_image.save()

    # Refresh extracted_images after processing
    extracted_images = ExtractedImage.objects.all()

    return render(request, "file_processor/upload.html", {"extracted_images": extracted_images})
   