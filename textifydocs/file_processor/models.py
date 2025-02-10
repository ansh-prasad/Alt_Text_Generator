from django.db import models
import os
from django.conf import settings

class UploadedFile(models.Model):
    file = models.FileField(upload_to="uploads/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def delete(self, *args, **kwargs):
        if os.path.exists(self.file.path):
            os.remove(self.file.path)  # Delete file from storage
        super().delete(*args, **kwargs)

class ExtractedImage(models.Model):
    file = models.ForeignKey(UploadedFile, on_delete=models.CASCADE)
    image = models.ImageField(upload_to="extracted_images/")
    extracted_at = models.DateTimeField(auto_now_add=True)

    def delete(self, *args, **kwargs):
        if os.path.exists(self.image.path):
            os.remove(self.image.path)  # Delete image from storage
        super().delete(*args, **kwargs)
