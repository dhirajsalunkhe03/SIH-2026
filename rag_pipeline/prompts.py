#!/usr/bin/env python3
"""
System prompts for Legal RAG with Qwen3.
Simplified for better performance with qwen3:4b.
"""

# Main system prompt - concise and direct
LEGAL_RAG_SYSTEM_PROMPT = """You are an Indian legal-information assistant for Patents, Trademarks, Designs, Geographical Indications, Biodiversity, ABS, and Traditional Knowledge.

Answer ONLY from the provided legal context. Do not invent legal text, sections, rules, or interpretations.

If the context does not contain the answer: "I could not find sufficient supporting information in the available legal knowledge base."

Format your response exactly as:
**Answer**: your answer
**Sources**: your sources
**Confidence**: High/Medium/Low

Preserve legal terminology. Follow user's language. No legal advice."""

# Concise version for faster inference
LEGAL_RAG_CONCISE_PROMPT = """You are an Indian legal-information assistant for Patents, Trademarks, Designs, GI, Biodiversity, ABS, and Traditional Knowledge.

Answer ONLY from the provided legal context. Do not invent legal text.

If context is insufficient: "I could not find sufficient supporting information in the available legal knowledge base."

Format your response exactly as:
**Answer**: your answer
**Sources**: your sources
**Confidence**: High/Medium/Low

Preserve legal terminology. Follow user's language. No legal advice."""


# Language-specific instruction suffixes
# PHASE 5A: Force English-only internal generation. Multilingual output will be added later.
LANGUAGE_INSTRUCTIONS = {
    'en': "Answer in English.",
    'hi': "Answer in English. (Internal reasoning language is English)",
    'mr': "Answer in English. (Internal reasoning language is English)",
    'gu': "Answer in English. (Internal reasoning language is English)",
    'bn': "Answer in English. (Internal reasoning language is English)",
    'ta': "Answer in English. (Internal reasoning language is English)",
    'te': "Answer in English. (Internal reasoning language is English)",
    'kn': "Answer in English. (Internal reasoning language is English)",
    'ml': "Answer in English. (Internal reasoning language is English)",
    'pa': "Answer in English. (Internal reasoning language is English)",
    'auto': "Answer in English. (Internal reasoning language is English)",
}


def get_system_prompt(concise: bool = True) -> str:
    """Get the appropriate system prompt."""
    return LEGAL_RAG_CONCISE_PROMPT if concise else LEGAL_RAG_SYSTEM_PROMPT


def get_language_instruction(lang_code: str) -> str:
    """Get language instruction for the given language code."""
    return LANGUAGE_INSTRUCTIONS.get(lang_code, LANGUAGE_INSTRUCTIONS['auto'])


def build_rag_prompt(
    query: str,
    context: str,
    language: str = 'auto',
    concise: bool = True
) -> str:
    """Build the complete prompt for Qwen3."""
    system_prompt = get_system_prompt(concise)
    lang_instruction = get_language_instruction(language)
    
    # PHASE 5A: English-only internal generation with think=false
    # Strict output format, no reasoning, no thinking tags
    prompt = f"""<|system|>
{system_prompt}

{lang_instruction}
<|user|>
CONTEXT:
{context}

QUESTION: {query}<|assistant|>"""
    return prompt


if __name__ == '__main__':
    # Test
    sample_context = """SOURCE 1
Document: Patents Act, 1970 (1970)
Section: 2(1)(m) — Definition of patent
Pages: 2-3

"patent" means a patent for any invention granted under this Act;"""

    prompt = build_rag_prompt(
        query="What is a patent?",
        context=sample_context,
        language='en'
    )
    print(prompt[:1500])
    print("...")