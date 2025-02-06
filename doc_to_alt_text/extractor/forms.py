from django import forms

class UploadDocxForm(forms.Form):
    doc_file = forms.FileField()
