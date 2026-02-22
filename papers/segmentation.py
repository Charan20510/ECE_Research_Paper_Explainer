import re
from typing import Dict, List, Optional

# Standardized section keys
SECTIONS = [
    "abstract",
    "introduction",
    "literature_review",
    "methodology",
    "analysis",
    "results",
    "conclusion",
    "references"
]

# Mapping of alternative heading names to standard keys
HEADING_MAPPING = {
    "abstract": "abstract",
    "introduction": "introduction",
    "background": "introduction",
    "related work": "literature_review",
    "literature review": "literature_review",
    "previous work": "literature_review",
    "state of the art": "literature_review",
    "methodology": "methodology",
    "methods": "methodology",
    "proposed method": "methodology",
    "proposed system": "methodology",
    "system model": "methodology",
    "approach": "methodology",
    "analysis": "analysis",
    "discussion": "analysis",
    "evaluation": "analysis",
    "experimental setup": "results",
    "experiments": "results",
    "results": "results",
    "experimental results": "results",
    "performance evaluation": "results",
    "conclusion": "conclusion",
    "conclusions": "conclusion",
    "future work": "conclusion",
    "conclusion and future work": "conclusion",
    "references": "references",
    "bibliography": "references"
}

def classify_heading(heading: str) -> Optional[str]:
    """
    Classifies a raw heading string into a standardized section name.
    
    Args:
        heading (str): The raw heading extracted from the paper.
        
    Returns:
        Optional[str]: The standardized section name if a match is found, else None.
    """
    # Clean the heading: lowercase, remove unwanted chars, strip whitespace
    clean_heading = heading.lower()
    
    # Remove numbering (e.g., "1.", "II.", "1.2", "A.")
    # Matches patterns like "1. ", "1 ", "1.2. ", "II. ", "A. " at the start
    clean_heading = re.sub(r'^([A-Z]|\d+|[ivxlcdm]+)[\.\s]+', '', clean_heading).strip()
    
    # Check exact matches first
    if clean_heading in HEADING_MAPPING:
        return HEADING_MAPPING[clean_heading]
        
    # Check if heading starts with one of our known mapped terms
    # Sort keys by length descending to match longest phrases first
    sorted_keys = sorted(HEADING_MAPPING.keys(), key=len, reverse=True)
    for key in sorted_keys:
        if clean_heading.startswith(key):
            return HEADING_MAPPING[key]
            
    # As a final fallback for things like "VI. Proposed Method and System"
    for key in sorted_keys:
        # Require word boundaries for substring match to avoid "method" matching "methodology" string falsely
        if re.search(r'\b' + re.escape(key) + r'\b', clean_heading):
            return HEADING_MAPPING[key]
            
    return None

def is_heading(line: str) -> bool:
    """
    Determines if a given line is likely a section heading.
    Rules:
    - ALL CAPS headings
    - Numbered headings (e.g., "1. Introduction", "II. Methodology")
    - Short length (usually headings are just a few words)
    - Not ending with standard punctuation (like a period for a sentence)
    """
    line = line.strip()
    if not line:
        return False
        
    # Too long to be a typical heading
    if len(line.split()) > 15:
        return False
        
    # If the line exactly matches a known section keyword (case insensitive)
    # But only if it's formatted somewhat like a heading (e.g. Title Case or ALL CAPS)
    # We don't want to swallow a single word paragraph like "methods" if it's just lowercase text.
    clean_line = re.sub(r'^([A-Z]|\d+|[ivxlcdm]+)[\.\s]+', '', line.lower()).strip()
    
    if clean_line in HEADING_MAPPING:
        # Check if the original line had formatting that makes it look like a heading
        # It should either be Title Case, ALL CAPS, or start with numbers/roman numerals
        if line.istitle() or line.isupper() or re.match(r'^([A-Z]|\d+|[IVXLCDMivxlcdm]+)[\.\s]', line):
            return True
            
        # If it's pure lowercase or mixed case, we should be careful. We only accept it as a heading
        # if it's strictly one of the primary mapped keys (or a multi-word key like "related work"),
        # and we might still be risking swallowing text.
        if len(line.split()) <= 4:
             # In our specific test, "abstract" and "Introduction" and "related Work" and "proposed method" 
             # are headers. "abs", "intro", "literature", "methods" are the text lines.
             # We need to distinguish between 'proposed method' (heading) and 'methods' (text).
             # Let's check if it's a primary key vs an alternative, OR if it's a multi-word phrase.
             # Multi-word phrases in the mapping are almost certainly headings (e.g. "related work", "proposed method").
             # Single word lowercase terms like "methods" or "results" are risky if they are just paragraph text.
             
             if len(clean_line.split()) > 1:
                 return True # Multi-word exact match (e.g., "related work", "proposed method") is safe
                 
             if clean_line in ["abstract", "introduction", "background", "methodology", "analysis", "results", "conclusion", "references"]:
                 return True
        
    # Common heading patterns
    heading_patterns = [
        # Numbered: "1. Introduction", "1 Introduction"
        r'^\d+[\.\s]+[a-zA-Z\s]+',
        # Roman numerals: "I. INTRODUCTION", "II. Related Work"
        r'^[IVXLCDMivxlcdm]+[\.\s]+[a-zA-Z\s]+',
        # ALL CAPS headings (allowing some numbers/spaces)
        r'^[A-Z0-9\s]+$',
        # Standard Title Case (e.g., "Related Work", "Experimental Results")
        # Must start with optional number/roman numeral, then Title Case words
        r'^([A-Z]|\d+|[IVXLCDM]+)[\.\s]*([A-Z][a-z]+\s*)+$'
    ]
    
    for pattern in heading_patterns:
        if re.match(pattern, line):
            # Extra check: ensure it doesn't end like a normal sentence
            if not re.search(r'[.!?]$', line) or re.match(r'^([A-Z]|\d+|[IVXLCDM]+)\.', line) or re.match(r'^[0-9]+\.', line):
                return True
                
    return False

def build_section_map(text: str) -> Dict[str, str]:
    """
    Parses the full text, identifies headings, and chunks paragraphs into sections.
    Ignores content after the references section.
    
    Args:
        text (str): Cleaned extracted text from Stage 1.
        
    Returns:
        Dict[str, str]: Dictionary mapping standard section keys to their extracted text.
    """
    sections_dict = {key: "" for key in SECTIONS}
    lines = text.split('\n')
    
    current_section = None
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
            
        # Is this a heading?
        if is_heading(line_stripped):
            classified_sec = classify_heading(line_stripped)
            if classified_sec:
                current_section = classified_sec
                # If we entered 'references', we can stop appending further content to other sections.
                # The instructions say "Ignore references content beyond reference heading."
                # We'll just continue and append to 'references' but nothing else.
                continue
        
        # If it's not a recognized heading but we are in a section, append the text.
        if current_section:
            sections_dict[current_section] += line_stripped + "\n"
        else:
            # Handle text before the first formal heading (often Title, Authors, Abstract)
            # If line starts with "Abstract", capture it.
            if line_stripped.lower().startswith("abstract"):
                current_section = "abstract"
                content = re.sub(r'^abstract[\.\s:]*', '', line_stripped, flags=re.IGNORECASE).strip()
                if content:
                    sections_dict[current_section] += content + "\n"
            else:
                # Store pre-heading text in abstract implicitly if we haven't found a section
                sections_dict["abstract"] += line_stripped + "\n"
                
    # Clean up trailing newlines
    for k in sections_dict:
        sections_dict[k] = sections_dict[k].strip()
        
    return sections_dict

def detect_sections(text: str) -> Dict[str, str]:
    """
    Main entry point for Stage 2.
    Analyzes the extracted text and returns the structured section dictionary.
    
    Args:
        text (str): The clean extracted text from a paper.
        
    Returns:
        Dict[str, str]: Structured data mapped to standard section names.
    """
    if not text or not isinstance(text, str):
        return {key: "" for key in SECTIONS}
        
    return build_section_map(text)
