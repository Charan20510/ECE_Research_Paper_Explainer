from django.test import TestCase
from .segmentation import detect_sections

class SegmentationTestCase(TestCase):
    
    def test_standard_headings(self):
        text = "Abstract\nThis is the abstract.\n\n1. Introduction\nIntro text.\n\n2. Methodology\nMethods here.\n\n3. Results\nWe got results."
        sections = detect_sections(text)
        self.assertEqual(sections['abstract'], "This is the abstract.")
        self.assertEqual(sections['introduction'], "Intro text.")
        self.assertEqual(sections['methodology'], "Methods here.")
        self.assertEqual(sections['results'], "We got results.")

    def test_alternative_headings(self):
        text = "Abstract\nAbst text.\n\nI. Background\nBackground text.\n\nII. Related Work\nPrev works.\n\nIII. Experimental Setup\nSetup text.\n\nIV. Conclusion and Future Work\nEnd."
        sections = detect_sections(text)
        self.assertEqual(sections['abstract'], "Abst text.")
        self.assertEqual(sections['introduction'], "Background text.")
        self.assertEqual(sections['literature_review'], "Prev works.")
        self.assertEqual(sections['results'], "Setup text.")
        self.assertEqual(sections['conclusion'], "End.")

    def test_lowercase_and_mixed_case(self):
        text = "abstract\nabs\n\nIntroduction\nintro\n\nrelated Work\nliterature\n\nproposed method\nmethods"
        sections = detect_sections(text)
        self.assertEqual(sections['abstract'], "abs")
        self.assertEqual(sections['introduction'], "intro")
        self.assertEqual(sections['literature_review'], "literature")
        self.assertEqual(sections['methodology'], "methods")

    def test_missing_abstract(self):
        # Even without a formal heading, text at the very top is typically part of the abstract/intro
        text = "Some title text\nAuthor Name\nThis is implicit abstract text.\n\n1. Introduction\nIntro starts."
        sections = detect_sections(text)
        self.assertIn("implicit abstract text", sections['abstract'])
        self.assertEqual(sections['introduction'], "Intro starts.")

    def test_references_cutoff(self):
        text = "Abstract\nAbstract.\n\nReferences\n[1] Paper 1\n[2] Paper 2\n\n1. Introduction\nThis is an appendix masquerading as intro."
        sections = detect_sections(text)
        self.assertEqual(sections['abstract'], "Abstract.")
        self.assertIn("[1] Paper 1\n[2] Paper 2\n\n1. Introduction\nThis is an appendix masquerading as intro.", sections['references'])
        self.assertEqual(sections['introduction'], "")

from .services import split_into_sentences
from .models import UploadedPaper, SectionExplanation
import json

class ExplanationEngineTestCase(TestCase):
    
    def test_split_into_sentences_basic(self):
        text = "This is the first sentence. And here is the second! Is this the third?"
        sentences = split_into_sentences(text)
        self.assertEqual(len(sentences), 3)
        self.assertEqual(sentences[0], "This is the first sentence.")
        self.assertEqual(sentences[1], "And here is the second!")
        self.assertEqual(sentences[2], "Is this the third?")

    def test_split_into_sentences_abbreviations(self):
        text = "Dr. Smith presented Fig. 1 at the conference. The model (i.e. the transformer) works well, e.g. for NLP tasks. Wait, does it?"
        sentences = split_into_sentences(text)
        self.assertEqual(len(sentences), 3)
        # Should not split on 'Dr.', 'Fig.', 'i.e.', 'e.g.'
        self.assertTrue(sentences[0].startswith("Dr. Smith"))
        self.assertIn("Fig. 1", sentences[0])
        self.assertTrue(sentences[1].startswith("The model"))
        self.assertIn("e.g.", sentences[1])
        self.assertEqual(sentences[2], "Wait, does it?")

    def test_split_into_sentences_newlines(self):
        text = "This is sentence one.\nThis is sentence two.\n\nThis is a new paragraph."
        sentences = split_into_sentences(text)
        self.assertEqual(len(sentences), 3)
        self.assertEqual(sentences[0], "This is sentence one.")
        self.assertEqual(sentences[1], "This is sentence two.")
        self.assertEqual(sentences[2], "This is a new paragraph.")
        
    def test_db_model_saving(self):
        paper = UploadedPaper.objects.create(title="Test Paper", extracted_text="Dummy text")
        exp_data = [
            {"sentence": "Hello world.", "explanation": "A greeting.", "background_concepts": None}
        ]
        db_record = SectionExplanation.objects.create(
            paper=paper, 
            section_name="introduction", 
            original_text="Hello world.",
            explanations=exp_data
        )
        self.assertEqual(db_record.paper.title, "Test Paper")
        self.assertEqual(len(db_record.explanations), 1)
        self.assertEqual(db_record.explanations[0]['explanation'], "A greeting.")
