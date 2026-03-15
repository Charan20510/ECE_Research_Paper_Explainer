import os
import re

# PyMuPDF is only required when performing actual PDF extraction.  Import
# it inside the function so that management commands (makemigrations, etc.)
# can run even if the library isn't installed yet.  This also makes it easier
# to switch to an alternative parser later if needed.




def extract_text_from_pdf(file_path: str) -> str:
    """Extracts raw text from a PDF located at file_path.

    This function uses **pdfminer.six** layout analysis for extraction because 
    it natively reconstructs text from two-column research papers without interleaving
    lines. It's much safer than generic horizontal extraction.
    
    If pdfminer is absolutely unavailable, it falls back to PyMuPDF.
    """
    try:
        from pdfminer.high_level import extract_text
        return extract_text(file_path)
    except ImportError:
        # try the old library as last resort
        try:
            import fitz  # PyMuPDF
        except ImportError as exc:
            raise ImportError(
                "pdfminer.six or PyMuPDF is required to extract text from PDFs. "
            ) from exc
        else:
            text_content = []
            with fitz.open(file_path) as doc:
                for page in doc:
                    text_content.append(page.get_text())
            return "\n".join(text_content)
    except Exception as e:
        raise ValueError(f"Failed to read PDF file: {e}")


def clean_text_pipeline(raw_text: str) -> str:
    """Performs normalization and light cleaning of extracted text.

    Steps:
    - Remove multiple blank lines
    - Normalize unicode and whitespace
    - Strip leading/trailing spaces
    - Collapse long runs of whitespace into single space
    """
    # collapse multiple newlines
    cleaned = re.sub(r"\n{2,}", "\n\n", raw_text)
    # remove weird characters (non-printable)
    cleaned = re.sub(r"[^\x00-\x7F]+", " ", cleaned)
    # collapse whitespace
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = cleaned.strip()
    return cleaned


def save_extracted_content(paper, text: str, sections_dict: dict = None):
    """Persist extracted text as .txt and .json files on disk.

    Creates a directory under the project root `extracted_content/` using a
    sanitized name derived from the paper title (falling back to the PK).
    The folder will contain `text.txt`, `data.json`, and `sections.json` so downstream 
    stages or external tools can consume the raw OCR/parsed output.
    """
    from django.conf import settings
    from django.utils.text import slugify
    import json
    import os

    # Use Django's configured MEDIA_ROOT for stored content instead of hardcoded paths
    root = settings.MEDIA_ROOT / 'extracted_content'
    root.mkdir(parents=True, exist_ok=True)

    # choose directory name
    if paper.title:
        slug = slugify(paper.title)[:50]
        if not slug:
            slug = f"paper_{paper.pk}"
    else:
        slug = f"paper_{paper.pk}"

    folder = root / slug
    # if folder exists, we might want to append PK to ensure uniqueness
    if folder.exists() and not (folder / 'text.txt').exists():
        # If it's a completely clean folder from another thread it might be empty, but 
        # normally we just reuse it or append PK if it belongs to a different paper.
        pass
    else:
        # Just to be safe, append PK if it exists but might conflict
        if folder.exists():
            folder = root / f"{slug}_{paper.pk}"
            
    folder.mkdir(exist_ok=True)

    # write text file
    txt_path = folder / 'text.txt'
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(text)

    # write main data json (title, raw text)
    data = {
        'title': paper.title,
        'extracted_text': text,
    }
    json_path = folder / 'data.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    # write sections file
    if sections_dict:
        sections_path = folder / 'sections.json'
        with open(sections_path, 'w', encoding='utf-8') as f:
            json.dump(sections_dict, f, ensure_ascii=False, indent=2)
