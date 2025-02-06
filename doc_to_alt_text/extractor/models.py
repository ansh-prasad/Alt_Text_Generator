from django.db import models

class UploadedDoc(models.Model):
    doc_file = models.FileField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
