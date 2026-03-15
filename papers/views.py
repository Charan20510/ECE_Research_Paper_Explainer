from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse
from django.views import View
import json

from .forms import PaperUploadForm
from .models import UploadedPaper
from .utils import extract_text_from_pdf, clean_text_pipeline
from .services import build_section_explanation


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

                # run stage 2 section segmentation
                from .segmentation import detect_sections
                sections_dict = detect_sections(cleaned)

                # persist extracted content and segmented JSON to disk
                from .utils import save_extracted_content
                try:
                    save_extracted_content(paper, cleaned, sections_dict)
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
    """Simple detail page to show uploaded paper metadata and extracted text,
    as well as the generated sections for the Explanation Engine UI."""

    template_name = 'papers/detail.html'

    def get(self, request, pk):
        from django.conf import settings
        from django.utils.text import slugify
        import os
        
        paper = get_object_or_404(UploadedPaper, pk=pk)
        
        # Read the segmented sections JSON
        sections_dict = {}
        slug = slugify(paper.title)[:50] if paper.title else f"paper_{paper.pk}"
        folder = settings.MEDIA_ROOT / 'extracted_content' / slug
        
        # fallback to the appended PK logic if standard doesn't exist
        if not folder.exists():
            folder = settings.MEDIA_ROOT / 'extracted_content' / f"{slug}_{paper.pk}"
            
        sections_path = folder / 'sections.json'
        if sections_path.exists():
            with open(sections_path, 'r', encoding='utf-8') as f:
                try:
                    sections_dict = json.load(f)
                except json.JSONDecodeError:
                    pass
        
        return render(request, self.template_name, {
            'paper': paper,
            'sections_dict': sections_dict,
            # Serialize for easy javascript consumption
            'sections_json': json.dumps(sections_dict, ensure_ascii=False)
        })


class GenerateExplanationView(View):
    """
    API View to generate explanations for a specific section via AJAX from the UI.
    Expects POST payload: { "section_name": "...", "section_text": "..." }
    """
    def post(self, request, pk):
        paper = get_object_or_404(UploadedPaper, pk=pk)
        
        try:
            data = json.loads(request.body)
            section_name = data.get('section_name')
            section_text = data.get('section_text')
            
            if not section_name or not section_text:
                return JsonResponse({"error": "Missing section_name or section_text"}, status=400)
                
            explanation_record = build_section_explanation(paper, section_name, section_text)
            
            return JsonResponse({
                "status": "success",
                "section_name": section_name,
                "explanations": explanation_record.explanations
            })
            
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON payload"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
