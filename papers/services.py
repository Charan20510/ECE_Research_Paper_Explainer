import re
import json
import logging
import os
import time
import asyncio
from typing import List, Dict, Any, Optional
from django.conf import settings
import openai

from .models import UploadedPaper, SectionExplanation
from .prompts import build_explanation_prompt

logger = logging.getLogger(__name__)

# Initialize Cerebras Client
try:
    from cerebras.cloud.sdk import Cerebras
    client = Cerebras(
        api_key=os.environ.get("CEREBRAS_API_KEY")
    )
except Exception as e:
    logger.warning(f"Failed to initialize Cerebras client initially: {e}")
    client = None

def split_into_sentences(text: str) -> List[str]:
    """
    Splits a block of text into logical sentences or chunked strings.
    Handles basic punctuation splitting while avoiding splitting on common abbreviations
    like 'e.g.', 'i.e.', 'Fig.', 'et al.', etc.
    Forces large chunks to be broken down to prevent API token limits.
    """
    if not text:
        return []

    # First split by paragraphs to retain structure
    paragraphs = re.split(r'\n\s*\n', text)
    sentences = []
    
    abbrevs = r"(?<!\bet al)(?<!\bi\.e)(?<!\be\.g)(?<!\bFig)(?<!\bEq)(?<!\bRef)(?<!\bDr)(?<!\bProf)"
    pattern = rf'{abbrevs}([.?!])(?:\s+(?=[A-Z0-9])|$)'
    
    MAX_CHUNK_LEN = 600
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        # Collapse single newlines within a paragraph
        para = re.sub(r'(?<!\n)\n(?!\n)', ' ', para)
        
        parts = re.split(pattern, para)
        para_sentences = []
        
        if len(parts) == 1:
            if parts[0].strip():
                para_sentences.append(parts[0].strip())
        else:
            for i in range(0, len(parts) - 1, 2):
                s = (parts[i] + parts[i+1]).strip()
                if s:
                    para_sentences.append(s)
            if len(parts) % 2 != 0 and parts[-1].strip():
                para_sentences.append(parts[-1].strip())
                
        # Forcefully chunk any exceptionally long sentences (e.g. assembly code blocks)
        for s in para_sentences:
            if len(s) > MAX_CHUNK_LEN:
                words = s.split()
                current_chunk = []
                current_len = 0
                for w in words:
                    if current_len + len(w) > MAX_CHUNK_LEN and current_chunk:
                        sentences.append(" ".join(current_chunk))
                        current_chunk = [w]
                        current_len = len(w) + 1
                    else:
                        current_chunk.append(w)
                        current_len += len(w) + 1
                if current_chunk:
                    sentences.append(" ".join(current_chunk))
            else:
                sentences.append(s)
                
    return sentences

async def generate_explanation_async(messages: List[Dict[str, str]], semaphore: asyncio.Semaphore, retries: int = 5) -> Optional[Dict[str, Any]]:
    """
    Calls the LLM API to generate an explanation asynchronously.
    Uses a semaphore to strictly control the maximum number of concurrent requests.
    """
    global client
    if not client:
        # Try to reinitialize in case environment was loaded late
        from cerebras.cloud.sdk import Cerebras
        client = Cerebras(
            api_key=os.environ.get("CEREBRAS_API_KEY")
        )
    
    async with semaphore:
        for attempt in range(retries):
            try:
                # Run the synchronous client call in a background thread to prevent blocking
                response = await asyncio.to_thread(
                    client.chat.completions.create,
                    model="llama3.1-8b", 
                    messages=messages,
                    response_format={ "type": "json_object" },
                    temperature=0.3,
                    max_completion_tokens=4096,
                    top_p=1,
                    stream=False
                )
                
                content = response.choices[0].message.content
                if content:
                    # Clean markdown blocks if returned by Cerebras
                    content = content.strip()
                    if content.startswith("```json"):
                        content = content[7:]
                    if content.startswith("```"):
                        content = content[3:]
                    if content.endswith("```"):
                        content = content[:-3]
                    content = content.strip()
                    
                    # Parse JSON string back into a Python dict
                    parsed_data = json.loads(content)
                    return parsed_data
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON on attempt {attempt + 1}: {e}\nContent: {content}")
                continue
            except Exception as e:
                error_str = str(e)
                logger.error(f"Cerebras API error on attempt {attempt + 1}: {error_str}")
                
                if "insufficient_quota" in error_str or "exceeded your current quota" in error_str:
                    logger.error("Cerebras API Quota Exceeded! Please check your billing details.")
                    break # Don't retry quota issues
                
                # Handle rate limiting (429) specifically with exponential backoff
                if "429" in error_str or "too_many_requests" in error_str.lower() or "queue_exceeded" in error_str.lower():
                    wait_time = (2 ** attempt) + 1  # 2s, 3s, 5s, 9s...
                    logger.info(f"Rate limited. Waiting {wait_time}s before retrying...")
                    await asyncio.sleep(wait_time)
                    continue
                    
                # For other random errors, wait briefly before retrying
                await asyncio.sleep(1)
                continue
                
        return None

def build_section_explanation(paper: UploadedPaper, section_name: str, text: str) -> SectionExplanation:
    """
    Orchestrates the generation of line-by-line explanations for a specific section.
    Saves the results directly to the database and returns the new model instance.
    """
    # Check if we already have explanations for this section to avoid duplicate billing
    existing = SectionExplanation.objects.filter(paper=paper, section_name=section_name).first()
    if existing:
        return existing
        
    sentences = split_into_sentences(text)
    
    # We will use an internal async runner to gather explanations concurrently
    async def fetch_all_explanations():
        # Limit concurrent requests to 8 to avoid instant 429 rate limit spikes
        semaphore = asyncio.Semaphore(8)
        tasks = []
        
        for sentence in sentences:
            messages = build_explanation_prompt(sentence, section_name)
            # Create a background task for each API request
            tasks.append(generate_explanation_async(messages, semaphore))
            
        # Execute all tasks concurrently and wait for all to finish
        # This will return a list of result dicts in the EXACT same order they were appended
        return await asyncio.gather(*tasks)
    
    # Run the event loop synchronously from Django's synchronous view context
    try:
        # Get existing event loop or run fresh
        results = asyncio.run(fetch_all_explanations())
    except RuntimeError:
        # Fallback if an event loop is already running in the thread
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(fetch_all_explanations())

    explanations_list = []
    
    # Map back to sentences and handle any missing fallback cases
    for idx, result_dict in enumerate(results):
        sentence = sentences[idx]
        if result_dict:
             explanations_list.append(result_dict)
        else:
             # Fallback if API continually fails for this sentence
             explanations_list.append({
                 "sentence": sentence,
                 "explanation": "- ⚠️ **Error**: Could not generate explanation due to an API rate limit or error. Please try again later.",
                 "background_concepts": None
             })
             
    # Save to database
    explanation_record = SectionExplanation.objects.create(
        paper=paper,
        section_name=section_name,
        original_text=text,
        explanations=explanations_list
    )
    
    return explanation_record
