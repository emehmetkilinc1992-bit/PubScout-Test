import requests
import pandas as pd
import streamlit as st
from transformers import pipeline
from deep_translator import GoogleTranslator
from fpdf import FPDF
import re
from datetime import date

# --- 1. TEMEL ARAMA MOTORU ---
def get_journals_from_openalex(text_input, mode="abstract"):
    base_url = "https://api.openalex.org/works"
    journal_list = []

    if mode == "abstract" and text_input and len(text_input) > 10:
        try:
            translated = GoogleTranslator(source='auto', target='en').translate(text_input)
            if not translated: translated = text_input
        except:
            translated = text_input
            
        keywords = " ".join(translated.split()[:30])
        params = {"search": keywords, "per-page": 50, "filter": "type:article", "select": "primary_location,title,cited_by_count"}
        
        try:
            resp = requests.get(base_url, params=params)
            results = resp.json().get('results', [])
        except:
            results = []

    elif mode == "doi" and text_input and "10." in text_input:
        raw_dois = re.findall(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', text_input, re.IGNORECASE)
        results = []
        for doi in raw_dois[:15]: 
            try:
                clean = "https://doi.org/" + doi
                res = requests.get(f"https://api.openalex.org/works/{clean}")
                if res.status_code == 200: results.append(res.json())
            except: pass
    else:
        return pd.DataFrame()

    for work in results:
        loc = work.get('primary_location', {})
        if loc and loc.get('source'):
            source = loc.get('source')
            name = source.get('display_name')
            pub = source.get('host_organization_name')
            link = source.get('homepage_url')
            imp = work.get('cited_by_count', 0)
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
    return pd.DataFrame(journal_list)

# --- 2. HİBRİD ANALİZ ---
def analyze_hybrid_search(abstract_text, doi_text):
    df_abs = pd.DataFrame()
    df_doi = pd.DataFrame()

    if abstract_text and len(abstract_text) > 20:
        df_abs = get_journals_from_openalex(abstract_text, mode="abstract")
    if doi_text and "10." in doi_text:
        df_doi = get_journals_from_openalex(doi_text, mode="doi")

    full_df = pd.concat([df_abs, df_doi])
    if full_df.empty: return None

    grouped = full_df.groupby(['Dergi Adı', 'Yayınevi', 'Q Değeri', 'Link']).size().reset_index(name='Skor')
    
    def get_source_tag(row):
        sources = full_df[full_df['Dergi Adı'] == row['Dergi Adı']]['Kaynak'].unique()
        return "🔥 GÜÇLÜ EŞLEŞME" if len(sources) > 1 else f"Kaynak: {sources[0]}"

    grouped['Eşleşme Tipi'] = grouped.apply(get_source_tag, axis=1)
    grouped = grouped.sort_values(by=['Skor', 'Q Değeri'], ascending=[False,
