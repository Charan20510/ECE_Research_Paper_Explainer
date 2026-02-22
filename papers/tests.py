from django.test import TestCase
from .segmentation import detect_sections

class SegmentationTestCase(TestCase):
    
    def test_standard_headings(self):
        text = "Abstract\nThis is the abstract.\n1. Introduction\nIntro text.\n2. Methodology\nMethods here.\n3. Results\nWe got results."
        sections = detect_sections(text)
        self.assertEqual(sections['abstract'], "This is the abstract.")
        self.assertEqual(sections['introduction'], "Intro text.")
        self.assertEqual(sections['methodology'], "Methods here.")
        self.assertEqual(sections['results'], "We got results.")

    def test_alternative_headings(self):
        text = "Abstract\nAbst text.\nI. Background\nBackground text.\nII. Related Work\nPrev works.\nIII. Experimental Setup\nSetup text.\nIV. Conclusion and Future Work\nEnd."
        sections = detect_sections(text)
        self.assertEqual(sections['abstract'], "Abst text.")
        self.assertEqual(sections['introduction'], "Background text.")
        self.assertEqual(sections['literature_review'], "Prev works.")
        self.assertEqual(sections['results'], "Setup text.")
        self.assertEqual(sections['conclusion'], "End.")

    def test_lowercase_and_mixed_case(self):
        text = "abstract\nabs\nIntroduction\nintro\nrelated Work\nliterature\nproposed method\nmethods"
        sections = detect_sections(text)
        self.assertEqual(sections['abstract'], "abs")
        self.assertEqual(sections['introduction'], "intro")
        self.assertEqual(sections['literature_review'], "literature")
        self.assertEqual(sections['methodology'], "methods")

    def test_missing_abstract(self):
        # Even without a formal heading, text at the very top is typically part of the abstract/intro
        text = "Some title text\nAuthor Name\nThis is implicit abstract text.\n1. Introduction\nIntro starts."
        sections = detect_sections(text)
        self.assertIn("implicit abstract text", sections['abstract'])
        self.assertEqual(sections['introduction'], "Intro starts.")

    def test_references_cutoff(self):
        text = "Abstract\nAbstract.\nReferences\n[1] Paper 1\n[2] Paper 2"
        sections = detect_sections(text)
        self.assertEqual(sections['abstract'], "Abstract.")
        self.assertIn("[1] Paper 1", sections['references'])
        # A heading after references shouldn't break the rules or map to standard keys if it's just garbage
        # Our logic appends after references TO the references section.
