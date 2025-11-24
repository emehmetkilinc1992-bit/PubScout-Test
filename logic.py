import requests
import pandas as pd
import streamlit as st
from transformers import pipeline
from deep_translator import GoogleTranslator
from fpdf import FPDF
import re
from datetime import date

# --- 1. TEMEL ARAMA MOTORU (API FIX + DEBUG MODU) ---
def get_journals_from_openalex(text_input, mode="abstract"):
    base_url = "https://api.openalex.org/works"
    
    # 🚨 API ENGELİNİ AŞMAK İÇİN KİMLİK BİLGİSİ
    headers = {
        'User-Agent': 'mailto:admin@pubscout.com' 
    }
    
    # Standart Sütunlar (Hata önleyici)
    columns = ["Dergi Adı", "Yayınevi", "Q Değeri", "Link", "Kaynak", "Atıf Gücü"]
    journal_list = []

    # --- SENARYO A: ABSTRACT (ÖZET) ---
    if mode == "abstract" and text_input:
        # Çeviri
        try:
            translated = GoogleTranslator(source='auto', target='en').translate(text_input)
            if not translated: translated = text_input
        except:
            translated = text_input
            
        # Strateji: Önce 20 kelime, olmazsa 6 kelime
        keywords = " ".join(translated.split()[:20])
        
        params = {
            "search": keywords,
            "per-page": 50,
            "filter": "type:article",
            "select": "primary_location,title,cited_by_count"
        }
        
        try:
            resp = requests.get(base_url, params=params, headers=headers)
            results = resp.json().get('results', [])
            
            # Sonuç yoksa daha genel arama yap (Fallback)
            if not results:
                short_keywords = " ".join(translated.split()[:6])
                params["search"] = short_keywords
                resp_retry = requests.get(base_url, params=params, headers=headers)
                results = resp_retry.json().get('results', [])
        except:
            results = []

    # --- SENARYO B: DOI (REFERANS) ---
    elif mode == "doi" and text_
