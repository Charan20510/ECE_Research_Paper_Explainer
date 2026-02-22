from django import forms

from .models import UploadedPaper


class PaperUploadForm(forms.ModelForm):
    class Meta:
        model = UploadedPaper
        fields = ['file']
