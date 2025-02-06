import os
import uuid
from django.shortcuts import render, redirect
from django.core.files.storage import default_storage
from django.utils.text import get_valid_filename
from django.conf import settings
from .forms import UploadDocxForm
from .extract_images import extract_images_from_docx
from .generate_alt_text import generate_alt_text

def upload_docx(request):
    if request.method == 'POST':
        form = UploadDocxForm(request.POST, request.FILES)
        if form.is_valid():
            doc_file = form.cleaned_data['doc_file']
            safe_filename = get_valid_filename(doc_file.name)
            unique_filename = f"{uuid.uuid4()}_{safe_filename}"
            doc_path = default_storage.save(f"uploads/{unique_filename}", doc_file)

            images = extract_images_from_docx(os.path.join(settings.MEDIA_ROOT, doc_path))
            image_text_pairs = [(img, generate_alt_text(img)) for img in images]

            request.session['image_text_pairs'] = image_text_pairs
            return redirect('view_results')
    else:
        form = UploadDocxForm()
    
    return render(request, 'extractor/upload_form.html', {'form': form})

def view_results(request):
    image_text_pairs = request.session.get('image_text_pairs', [])
    return render(request, 'extractor/results.html', {'image_text_pairs': image_text_pairs})
