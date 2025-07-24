import requests
import re
import streamlit as st
from typing import Optional

def _clean_wikipedia_html(html: str) -> str:
    """Helper to clean up Wikipedia HTML and artifacts."""
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
    html = re.sub(r'<sup[^>]*>.*?</sup>', '', html, flags=re.DOTALL)
    html = re.sub(r'<a [^>]+>(.*?)</a>', r'\1', html, flags=re.DOTALL)
    clean_text = re.sub('<[^<]+?>', '', html)
    clean_text = re.sub(r'\[[^\]]*\]', '', clean_text)
    clean_text = '\n'.join([line for line in clean_text.splitlines() if not line.strip().startswith('^')])
    clean_text = re.sub(r'/\*.*?\*/', '', clean_text, flags=re.DOTALL)
    clean_text = re.sub(r'\{[^\}]*\}', '', clean_text, flags=re.DOTALL)
    clean_text = '\n'.join([line for line in clean_text.splitlines() if line.strip()])
    return clean_text.strip()

def get_wikipedia_section(scientific_name: str, section_title: str) -> Optional[str]:
    """
    Fetches a specific section (by title) from a Wikipedia page for the given scientific name.
    Returns the section text if found, else None.
    """
    api_base = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "parse",
        "page": scientific_name,
        "prop": "sections",
        "format": "json"
    }
    try:
        resp = requests.get(api_base, params=params)
        if resp.status_code != 200:
            return None
        data = resp.json()
        sections = data.get("parse", {}).get("sections", [])
        section_index = None
        for sec in sections:
            if sec.get("line", "").lower() == section_title.lower():
                section_index = sec.get("index")
                break
        if not section_index:
            return None
        params2 = {
            "action": "parse",
            "page": scientific_name,
            "prop": "text",
            "section": section_index,
            "format": "json"
        }
        resp2 = requests.get(api_base, params=params2)
        if resp2.status_code != 200:
            return None
        data2 = resp2.json()
        html = data2.get("parse", {}).get("text", {}).get("*", "")
        return _clean_wikipedia_html(html)
    except Exception as e:
        st.error(f"Wikipedia section fetch failed: {e}")
        return None

def get_wikipedia_summary(scientific_name: str) -> Optional[dict]:
    wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{scientific_name.replace(' ', '_')}"
    try:
        resp = requests.get(wiki_url)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        st.error(f"Wikipedia request failed: {e}")
    return None
