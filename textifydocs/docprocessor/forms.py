from django import forms
from .models import DocFile
from django.core.validators import FileExtensionValidator

class DocUploadForm(forms.ModelForm):
    class Meta:
        model = DocFile
        fields = ['file']
        widgets = {
            'file': forms.ClearableFileInput(attrs={
                'accept': '.docx',
                'class': 'file-input',
            })
        }
        validators = [FileExtensionValidator(allowed_extensions=['docx'])]