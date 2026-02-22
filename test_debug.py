import sys
sys.path.append('.')
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ece_explainer.settings')
django.setup()

from papers.segmentation import detect_sections

text = "abstract\nabs\nIntroduction\nintro\nrelated Work\nliterature\nproposed method\nmethods"
res = detect_sections(text)
import pprint
pprint.pprint(res)
