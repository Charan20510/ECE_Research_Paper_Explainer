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


class SectionExplanation(models.Model):
    """
    Stores the line-by-line structured explanations for a specific section of a paper.
    
    We use a JSONField to store the array of explanations to maintain a highly 
    flexible and performant schema without creating thousands of individual
    SentenceExplanation rows for a single paper.
    """
    paper = models.ForeignKey(UploadedPaper, on_delete=models.CASCADE, related_name='explanations')
    section_name = models.CharField(max_length=100)
    original_text = models.TextField()
    
    # Structure of JSON:
    # [
    #   {
    #     "sentence": "Original sentence here",
    #     "explanation": "Beginner friendly explanation",
    #     "background_concepts": "Key theoretical concepts needed to understand this"
    #   }, ...
    # ]
    explanations = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # Prevent generating explanations for the exact same section twice
        unique_together = ('paper', 'section_name')
        
    def __str__(self):
        return f"{self.paper.title} - {self.section_name} Explanation"
