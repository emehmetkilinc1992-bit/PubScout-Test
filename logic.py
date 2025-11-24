import requests
import pandas as pd
import streamlit as st
from transformers import pipeline
from deep_translator import GoogleTranslator
from fpdf import FPDF
import re
from datetime import date

# --- 1. TEMEL ARAMA MOTORU (GELİŞMİŞ DOI & ÇEVİRİ DESTEKLİ) ---
def get_journals_from_openalex(text_input, mode="abstract"):
    base_url = "https://api.openalex.org/works"
    
    # Standart Sütun İsimleri (Hata almamak için)
    columns = ["Dergi Adı", "Yayınevi", "Q Değeri", "Link", "Kaynak", "Atıf Gücü"]
    journal_list = []

    # --- MOD A: ABSTRACT (ÖZET) ---
    if mode == "abstract" and text_input and len(text_input) > 10:
        try:
            # 1. Çeviri (Türkçe -> İngilizce)
            translated = GoogleTranslator(source='auto', target='en').translate(text_input)
            if not translated: translated = text_input
        except:
            translated = text_input
            
        # 2. Anahtar Kelime Çıkarma
        keywords = " ".join(translated.split()[:30])
        params = {
            "search": keywords,
            "per-page": 50,
            "filter": "type:article",
            "select": "primary_location,title,cited_by_count"
        }
        
        try:
            resp = requests.get(base_url, params=params)
            if resp.status_code == 200:
                results = resp.json().get('results', [])
            else:
                results = []
        except:
            results = []

    # --- MOD B: DOI (REFERANS) - GÜÇLENDİRİLMİŞ ---
    elif mode == "doi" and text_input:
        # 1. Kullanıcının girdiği linkleri temizle
        # (https://doi.org/ kısmını at, sadece 10.xxxx kısmını al)
        clean_text = text_input.replace("https://doi.org/", "").replace("http://doi.org/", "").replace("doi:", "")
        
        # 2. Regex ile DOI formatını yakala
        raw_dois = re.findall(r'(10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+)', clean_text)
        unique_dois = list(set(raw_dois)) # Tekrarları kaldır
        
        results = []
        for doi in unique_dois[:15]: # İlk 15 DOI'yi tara
            try:
                # Sonundaki noktalama işaretlerini temizle
                doi = doi.rstrip(".,)")
                
                # Yöntem 1: Doğrudan Eşleşme
                api_url = f"https://api.openalex.org/works/https://doi.org/{doi}"
                res = requests.get(api_url)
                
                if res.status_code == 200:
                    results.append(res.json())
                else:
                    # Yöntem 2: Filtre ile Arama (Yedek Plan)
                    res_backup = requests.get(f"https://api.openalex.org/works?filter=doi:https://doi.org/{doi}")
                    if res_backup.status_code == 200:
                        data = res_backup.json()
                        if data['results']:
                            results.extend(data['results'])
            except:
                pass
    else:
        # Girdi yoksa boş tablo dön
        return pd.DataFrame(columns=columns)

    # --- SONUÇLARI LİSTELE ---
    for work in results:
        loc = work.get('primary_location', {})
        if loc and loc.get('source'):
            source = loc.get('source')
            name = source.get('display_name')
            pub = source.get('host_organization_name')
            link = source.get('homepage_url')
            imp = work.get('cited_by_count', 0)
            
            # Q Değeri Simülasyonu
            q_val = "Q1" if imp > 50 else "Q2" if imp > 20 else "Q3" if imp > 5 else "Q4"

            if name:
                journal_list.append({
                    "Dergi Adı": name,
                    "Yayınevi": pub,
                    "Q Değeri": q_val,
                    "Link": link,
                    "Kaynak": mode.upper(),
                    "Atıf Gücü": imp
                })
    
    df = pd.DataFrame(journal_list)
    if df.empty:
        return pd.DataFrame(columns=columns)
        
    return df

# --- 2. HİBRİD ANALİZ (ValueError FIX EKLENDİ) ---
def analyze_hybrid_search(abstract_text, doi_text):
    empty_cols = ["Dergi Adı", "Yayınevi", "Q Değeri
