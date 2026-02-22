from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views import View

from .forms import PaperUploadForm
from .models import UploadedPaper
from .utils import extract_text_from_pdf, clean_text_pipeline


class UploadPaperView(View):
    """Handles file upload and triggers PDF ingestion pipeline.

    The template is responsible for displaying the upload form as well as
    any immediate success/failure notice.  Instead of redirecting to a
    detail view, we render the same page with context variables as outlined
    by the provided HTML design (`message` and `saved`).
    """

    template_name = 'papers/index.html'

    def get(self, request):
        form = PaperUploadForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = PaperUploadForm(request.POST, request.FILES)
        context = {'form': form}
        if form.is_valid():
            paper: UploadedPaper = form.save()
            try:
                # extract and clean text immediately after saving
                file_path = paper.file.path
                raw_text = extract_text_from_pdf(file_path)
                cleaned = clean_text_pipeline(raw_text)
                paper.extracted_text = cleaned
                paper.save()

                # persist extracted content to disk for later stages or auditing
                from .utils import save_extracted_content
                try:
                    save_extracted_content(paper, cleaned)
                except Exception:
                    # don't break the upload if filesystem writes fail; log could be added
                    pass

                context['message'] = '✅ Upload successful!'
                context['saved'] = paper
            except Exception as e:
                # If extraction fails (e.g., malformed PDF), delete the paper record
                # and physical file to prevent orphaned entries
                paper.delete()
                context['message'] = f'❌ Error processing PDF: {str(e)}'
        else:
            context['message'] = '⚠️ Please correct the errors below.'
        return render(request, self.template_name, context)


class PaperDetailView(View):
    """Simple detail page to show uploaded paper metadata and extracted text."""

    template_name = 'papers/detail.html'

    def get(self, request, pk):
        paper = get_object_or_404(UploadedPaper, pk=pk)
        return render(request, self.template_name, {'paper': paper})
