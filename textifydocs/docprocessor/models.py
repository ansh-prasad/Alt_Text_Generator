from django.db import models

class DocFile(models.Model):
    file = models.FileField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

class ProcessedImage(models.Model):
    doc_file = models.ForeignKey(DocFile, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='processed_images/')
    alt_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)