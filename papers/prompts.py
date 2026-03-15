import json

# Define the system prompt once for the "Explainer Engine" identity.
SYSTEM_PROMPT = """You are an expert teacher in all subjects (like a senior ECE professor). 
Your goal is to explain complex research papers to an absolute newbie who doesn't know anything about the advanced topics.

Guidelines:
1. Every line/sentence provided must be summarized and explained.
2. The summary/explanation MUST ONLY be in key points. The explanation must be extremely CRISP.
3. Use a main bullet point for the core concept being explained, and use nested sub-bullets underneath for the detailed, crisp explanations. DO NOT use literal words like "Main Point:" or "Sub-point:". Keep it natural.
4. Maintain the tone of an expert teacher explaining to a complete newbie, but keep it snappy and crisp.
5. Provide the Prerequisites (concepts to be known) at the bottom of your explanation.
6. Give these prerequisites in a hyperlink format (e.g., [Concept Name](https://en.wikipedia.org/wiki/Concept)) along with a short word explanation listed down for each.
"""

def build_explanation_prompt(sentence: str, section_name: str) -> list[dict]:
    """
    Builds the messages list required by the OpenAI ChatCompletion API.
    
    Args:
        sentence (str): The specific sentence or chunk to explain.
        section_name (str): The name of the section this sentence belongs to (e.g. "methodology").
        
    Returns:
        list[dict]: A list containing the system and user messages.
    """
    user_prompt = f"""
I am reading the "{section_name}" section of an ECE research paper.

Please explain the following sentence or chunk of text:
"{sentence}"

Provide your output ONLY as a valid JSON object matching this schema exactly (use Markdown formatting in the string values):
{{
    "sentence": "{sentence}",
    "explanation": "- Crisp summary of the core concept.\\n  - Crisp explanation detail 1.\\n  - Crisp explanation detail 2.\\n  - ...",
    "background_concepts": "- [Prerequisite Concept](https://example.com/concept): A crisp word explanation of what this means."
}}
"""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]
