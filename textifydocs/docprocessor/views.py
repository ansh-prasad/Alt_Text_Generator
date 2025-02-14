from django.shortcuts import render, redirect
import os
from docx import Document
from django.conf import settings
from .models import DocFile, ProcessedImage
from .forms import DocUploadForm
import google.generativeai as genai

def extract_images_from_docx(docx_path):
    images = []
    doc = Document(docx_path)
    rels = doc.part.rels
    for rel in rels.values():
        if "image" in rel.target_ref:
            image_data = rel.target_part.blob
            images.append(image_data)
    return images

def generate_alt_text(image_data):
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    model = genai.GenerativeModel('gemini-pro-vision')
    response = model.generate_content(["Generate descriptive alt text for this image", image_data])
    return response.text

def home(request):
    if request.method == 'POST':
        form = DocUploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc_file = form.save()
            
            # Process DOCX
            docx_path = os.path.join(settings.MEDIA_ROOT, doc_file.file.name)
            images = extract_images_from_docx(docx_path)
            
            # Save images and generate alt text
            for idx, img_data in enumerate(images):
                img_name = f"image_{doc_file.id}_{idx}.png"
                img_path = os.path.join(settings.MEDIA_ROOT, 'processed_images', img_name)
                
                with open(img_path, 'wb') as f:
                    f.write(img_data)
                
                alt_text = generate_alt_text(img_data)
                ProcessedImage.objects.create(
                    doc_file=doc_file,
                    image=f'processed_images/{img_name}',
                    alt_text=alt_text
                )
            
            return redirect('results', doc_id=doc_file.id)
    else:
        form = DocUploadForm()
    return render(request, 'home.html', {'form': form})

def results(request, doc_id):
    doc_file = DocFile.objects.get(id=doc_id)
    images = ProcessedImage.objects.filter(doc_file=doc_file)
    return render(request, 'results.html', {'images': images})