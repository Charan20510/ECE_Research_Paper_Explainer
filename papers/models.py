from django.db import models


class UploadedPaper(models.Model):
    """Model to keep track of uploaded PDF research papers."""
    title = models.CharField(max_length=255, blank=True)
    file = models.FileField(upload_to='papers/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    extracted_text = models.TextField(blank=True)

    def __str__(self):
        return self.title or f"Paper {self.pk}"

    @property
    def text(self) -> str:
        """Convenience property used by templates.

        The UI expects `saved.text` so we expose the cleaned/extracted text
        under that attribute.
        """
        return self.extracted_text

    def save(self, *args, **kwargs):
        # override save to automatically set title if missing
        if not self.title and self.file:
            import os
            self.title = os.path.basename(self.file.name)
        super().save(*args, **kwargs)
