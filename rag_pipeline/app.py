#!/usr/bin/env python3
"""
Streamlit Frontend for SIH 2026 PS45 Legal RAG.
Multilingual legal intelligence system for Indian legal provisions.
"""

import streamlit as st
import requests
import json
import time
from typing import Dict, List, Optional
from dataclasses import dataclass

# Import UI translations
try:
    from ui_translations import UI_TRANSLATIONS, LANGUAGE_OPTIONS, get_text
except ImportError:
    # Fallback if ui_translations not available
    UI_TRANSLATIONS = {}
    LANGUAGE_OPTIONS = [
        ("en", "English"),
        ("hi", "हिंदी"),
        ("mr", "मराठी"),
        ("gu", "ગુજરાતી"),
        ("bn", "বাংলা"),
        ("ta", "தமிழ்"),
        ("te", "తెలుగు"),
        ("kn", "ಕನ್ನಡ"),
        ("ml", "മലയാളം"),
        ("pa", "ਪੰਜਾਬੀ"),
    ]
    def get_text(key: str, lang: str = "en") -> str:
        return key


# API Configuration
API_BASE_URL = "http://127.0.0.1:8000"
CHAT_ENDPOINT = f"{API_BASE_URL}/api/chat"
HEALTH_ENDPOINT = f"{API_BASE_URL}/health"


@dataclass
class ChatMessage:
    role: str  # "user" or "assistant"
    content: str
    sources: Optional[List[Dict]] = None
    confidence: Optional[str] = None
    latency: Optional[Dict] = None
    detected_language: Optional[str] = None
    answer_language: Optional[str] = None


def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "selected_language" not in st.session_state:
        st.session_state.selected_language = "en"
    if "api_healthy" not in st.session_state:
        st.session_state.api_healthy = False


def check_api_health() -> bool:
    """Check if the API is healthy."""
    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("status") == "healthy"
    except Exception:
        pass
    return False


def send_chat_query(query: str, language: str, domain: str = "all", top_k: int = 5) -> Optional[Dict]:
    """Send query to the API and return response."""
    payload = {
        "query": query,
        "language": language,
        "domain": domain,
        "top_k": top_k,
        "concise": True
    }
    
    try:
        response = requests.post(CHAT_ENDPOINT, json=payload, timeout=120)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
    except requests.exceptions.Timeout:
        st.error("Request timed out. The model is taking too long to respond.")
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to API. Please ensure the backend is running.")
    except Exception as e:
        st.error(f"Error: {str(e)}")
    
    return None


def render_language_selector():
    """Render the language selector in the sidebar."""
    st.sidebar.markdown("### " + get_text("language", st.session_state.selected_language))
    
    lang_names = {code: name for code, name in LANGUAGE_OPTIONS}
    current_lang = st.session_state.selected_language
    
    selected = st.sidebar.selectbox(
        get_text("select_language", current_lang),
        options=[code for code, _ in LANGUAGE_OPTIONS],
        format_func=lambda x: lang_names.get(x, x),
        index=[code for code, _ in LANGUAGE_OPTIONS].index(current_lang) if current_lang in [code for code, _ in LANGUAGE_OPTIONS] else 0,
        key="language_selector"
    )
    
    if selected != current_lang:
        st.session_state.selected_language = selected
        st.rerun()


def render_domain_selector():
    """Render the domain selector in the sidebar."""
    st.sidebar.markdown("### " + get_text("domain", st.session_state.selected_language))
    
    domains = {
        "all": get_text("all_domains", st.session_state.selected_language),
        "biodiversity": get_text("biodiversity", st.session_state.selected_language),
        "abs": get_text("abs", st.session_state.selected_language),
        "traditional_knowledge": get_text("traditional_knowledge", st.session_state.selected_language),
        "patents": get_text("patents", st.session_state.selected_language),
        "trademarks": get_text("trademarks", st.session_state.selected_language),
        "gi": get_text("gi", st.session_state.selected_language),
        "designs": get_text("designs", st.session_state.selected_language),
        "general_legal": get_text("general_legal", st.session_state.selected_language),
    }
    
    selected = st.sidebar.selectbox(
        get_text("select_domain", st.session_state.selected_language),
        options=list(domains.keys()),
        format_func=lambda x: domains.get(x, x),
        index=0,
        key="domain_selector"
    )
    
    return selected


def render_top_k_selector():
    """Render top_k selector in sidebar."""
    st.sidebar.markdown("### " + get_text("results_count", st.session_state.selected_language))
    return st.sidebar.slider(
        get_text("number_of_sources", st.session_state.selected_language),
        min_value=1,
        max_value=20,
        value=5,
        key="top_k_slider"
    )


def render_chat_history():
    """Render the chat history."""
    for msg in st.session_state.messages:
        with st.chat_message(msg.role):
            st.markdown(msg.content)
            
            # Show sources if available
            if msg.sources:
                with st.expander(get_text("sources", st.session_state.selected_language)):
                    for i, source in enumerate(msg.sources, 1):
                        doc = source.get("document", "Unknown")
                        year = source.get("document_year", "")
                        section = source.get("section", "")
                        rule = source.get("rule", "")
                        pages = source.get("pages", [])
                        
                        citation_parts = [f"{doc} ({year})" if year else doc]
                        if section:
                            citation_parts.append(f"Section {section}")
                        elif rule:
                            citation_parts.append(f"Rule {rule}")
                        if pages:
                            citation_parts.append(f"Pages {', '.join(map(str, pages))}")
                        
                        st.markdown(f"**{i}.** {' | '.join(citation_parts)}")
            
            # Show metadata
            if msg.confidence or msg.latency:
                meta_parts = []
                if msg.confidence:
                    meta_parts.append(f"**{get_text('confidence', st.session_state.selected_language)}:** {msg.confidence}")
                if msg.latency:
                    total = msg.latency.get("total_ms", 0)
                    meta_parts.append(f"**{get_text('total_time', st.session_state.selected_language)}:** {total}ms")
                if msg.detected_language:
                    meta_parts.append(f"**{get_text('detected_language', st.session_state.selected_language)}:** {msg.detected_language}")
                if msg.answer_language:
                    meta_parts.append(f"**{get_text('answer_language', st.session_state.selected_language)}:** {msg.answer_language}")
                
                if meta_parts:
                    st.caption(" | ".join(meta_parts))


def render_footer():
    """Render footer with information."""
    st.sidebar.markdown("---")
    st.sidebar.markdown(get_text("about", st.session_state.selected_language))
    st.sidebar.markdown(get_text("about_text", st.session_state.selected_language))
    st.sidebar.markdown(f"**{get_text('version', st.session_state.selected_language)}** 1.0.0")


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="SIH 2026 PS45 - Legal AI",
        page_icon="⚖️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    init_session_state()
    
    # Check API health
    with st.spinner(get_text("checking_api", st.session_state.selected_language)):
        st.session_state.api_healthy = check_api_health()
    
    # Sidebar
    with st.sidebar:
        st.title("⚖️ SIH 2026 PS45")
        st.markdown(get_text("subtitle", st.session_state.selected_language))
        
        # API Status
        if st.session_state.api_healthy:
            st.success(get_text("api_connected", st.session_state.selected_language))
        else:
            st.error(get_text("api_disconnected", st.session_state.selected_language))
            st.markdown(get_text("start_backend", st.session_state.selected_language))
            st.code("cd rag_pipeline && PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8000")
        
        st.markdown("---")
        
        # Language selector
        render_language_selector()
        
        # Domain selector
        selected_domain = render_domain_selector()
        
        # Top-k selector
        top_k = render_top_k_selector()
        
        # Clear chat button
        if st.button(get_text("clear_chat", st.session_state.selected_language), use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        
        render_footer()
    
    # Main chat area
    current_lang = st.session_state.selected_language
    
    st.title(get_text("title", current_lang))
    st.caption(get_text("subtitle_main", current_lang))
    
    # Show example queries
    if not st.session_state.messages:
        st.markdown(f"### {get_text('example_queries', current_lang)}")
        
        examples = {
            "en": [
                "What is a patent?",
                "What does Section 11 of the Patents Act deal with?",
                "What is the Biological Diversity Act, 2002?",
                "What is a geographical indication?",
                "What is traditional knowledge?"
            ],
            "hi": [
                "पेटेंट क्या है?",
                "पेटेंट अधिनियम की धारा 11 क्या है?",
                "जैविक विविधता अधिनियम, 2002 क्या है?",
                "भौगोलिक संकेत क्या है?",
                "पारंपरिक ज्ञान क्या है?"
            ],
            "mr": [
                "पेटंट म्हणजे काय?",
                "पेटंट कायद्याची कलम ११ काय आहे?",
                "जैविक विविधता कायदा, २००२ काय आहे?",
                "भौगोलिक संकेत काय आहे?",
                "पारंपरिक ज्ञान काय आहे?"
            ],
        }
        
        lang_examples = examples.get(current_lang, examples["en"])
        cols = st.columns(len(lang_examples))
        for i, example in enumerate(lang_examples):
            if cols[i].button(example, use_container_width=True):
                st.session_state.example_query = example
                st.rerun()
    
    # Render chat history
    render_chat_history()
    
    # Chat input
    if prompt := st.chat_input(get_text("placeholder", current_lang)):
        # Add user message
        st.session_state.messages.append(ChatMessage(role="user", content=prompt))
        
        # Send to API
        with st.spinner(get_text("thinking", current_lang)):
            response = send_chat_query(prompt, current_lang, selected_domain, top_k)
        
        if response and response.get("success"):
            # Add assistant message
            msg = ChatMessage(
                role="assistant",
                content=response.get("answer", ""),
                sources=response.get("sources", []),
                confidence=response.get("confidence"),
                latency=response.get("latency"),
                detected_language=response.get("detected_language", {}).get("name"),
                answer_language=response.get("answer_language")
            )
            st.session_state.messages.append(msg)
        else:
            # Add error message
            error_msg = response.get("detail", get_text("error_generic", current_lang)) if response else get_text("error_connection", current_lang)
            st.session_state.messages.append(ChatMessage(
                role="assistant",
                content=f"{get_text('error', current_lang)}: {error_msg}"
            ))
        
        st.rerun()
    
    # Handle example query from sidebar
    if "example_query" in st.session_state:
        prompt = st.session_state.example_query
        del st.session_state.example_query
        
        st.session_state.messages.append(ChatMessage(role="user", content=prompt))
        
        with st.spinner(get_text("thinking", current_lang)):
            response = send_chat_query(prompt, current_lang, selected_domain, top_k)
        
        if response and response.get("success"):
            msg = ChatMessage(
                role="assistant",
                content=response.get("answer", ""),
                sources=response.get("sources", []),
                confidence=response.get("confidence"),
                latency=response.get("latency"),
                detected_language=response.get("detected_language", {}).get("name"),
                answer_language=response.get("answer_language")
            )
            st.session_state.messages.append(msg)
        else:
            error_msg = response.get("detail", get_text("error_generic", current_lang)) if response else get_text("error_connection", current_lang)
            st.session_state.messages.append(ChatMessage(
                role="assistant",
                content=f"{get_text('error', current_lang)}: {error_msg}"
            ))
        
        st.rerun()


if __name__ == "__main__":
    main()