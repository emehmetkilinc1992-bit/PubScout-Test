import requests
import pandas as pd
import streamlit as st
from transformers import pipeline
from deep_translator import GoogleTranslator
from fpdf import FPDF
import re

# --- 1. TEMEL ARAMA MOTORU ---
def get_journals_from_openalex(text_input, mode="abstract"):
    base_url = "https://api.openalex.org/works"
    journal_list = []

    # MOD A: ABSTRACT
    if mode == "abstract" and text_input and len(text_input) > 10:
        try:
            # Çeviri işlemi
            translated = GoogleTranslator(source='auto', target='en').translate(text_input)
            if not translated:
                translated = text_input
        except:
            translated = text_input
            
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

    # MOD B: DOI
    elif mode == "doi" and text_input and "10." in text_input:
        raw_dois = re.findall(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', text_input, re.IGNORECASE)
        results = []
        for doi in raw_dois[:15]: 
            try:
                clean = "https://doi.org/" + doi
                res = requests.get(f"https://api.openalex.org/works/{clean}")
                if res.status_code == 200:
                    results.append(res.json())
            except:
                pass
    else:
        return pd.DataFrame()

    # SONUÇLARI İŞLE
    for work in results:
        loc = work.get('primary_location', {})
        if loc and loc.get('source'):
            source = loc.get('source')
            name = source.get('display_name')
            pub = source.get('host_organization_name')
            link = source.get('homepage_url')
            imp = work.get('cited_by_count', 0)
            
            if imp > 50: q_val = "Q1"
            elif imp > 20: q_val = "Q2"
            elif imp > 5: q_val = "Q3"
            else: q_val = "Q4"

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

# --- 2. HİBRİD ANALİZ FONKSİYONU ---
def analyze_hybrid_search(abstract_text, doi_text):
    df_abs = pd.DataFrame()
    df_doi = pd.DataFrame()

    if abstract_text and len(abstract_text) > 20:
        df_abs = get_journals_from_openalex(abstract_text, mode="abstract")
    
    if doi_text and "10." in doi_text:
        df_doi = get_journals_from_openalex(doi_text, mode="doi")

    full_df = pd.concat([df_abs, df_doi])
    
    if full_df.empty:
        return None

    # Puanlama
    grouped = full_df.groupby(['Dergi Adı', 'Yayınevi', 'Q Değeri', 'Link']).size().reset_index(name='Skor')
    
    def get_source_tag(row):
        sources = full_df[full_df['Dergi Adı'] == row['Dergi Adı']]['Kaynak'].unique()
        if len(sources) > 1:
            return "🔥 GÜÇLÜ EŞLEŞME"
        else:
            return f"Kaynak: {sources[0]}"

    grouped['Eşleşme Tipi'] = grouped.apply(get_source_tag, axis=1)
    # Sıralama
    grouped = grouped.sort_values(by=['Skor', 'Q Değeri'], ascending=[False, True])
    
    return grouped

# --- DİĞER ARAÇLAR ---
def check_predatory(journal_name):
    fake = ["International Journal of Advanced Science", "Predatory Reports", "Fake Science"]
    return any(x.lower() in str(journal_name).lower() for x in fake)

@st.cache_resource
def load_ai_detector():
    return pipeline("text-classification", model="roberta-base-openai-detector")

def check_ai_probability(text):
    if not text or len(text) < 50:
        return None
    try:
        clf = load_ai_detector()
        res = clf(text[:512])[0]
        
        if res['label'] == 'Fake':
            lbl = "Yapay Zeka (AI)"
            clr = "#FF4B4B"
        else:
            lbl = "İnsan (Doğal)"
            clr = "#00CC96"
            
        return {"label": lbl, "score": res['score'], "color": clr}
    except:
        return None

def convert_reference_style(ref_text, target_format):
    if not ref_text: return ""
    if target_format == "APA 7":
        return f"[APA] {ref_text} (Otomatik Düzenlendi)"
    elif target_format == "IEEE":
        return f"[1] {ref_text}."
    return ref_text

def create_academic_cv(data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    
    def clean(t):
        return str(t).encode('latin-1', 'replace').decode('latin-1')
    
    pdf.set_font("Helvetica", 'B', 20)
    pdf.cell(0, 15, txt=clean(data['name']), ln=True, align='C')
    pdf.set_font("Helvetica", 'I', 14)
    pdf.cell(0, 10, txt=clean(data['title']), ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 5, txt=clean(f"{data['email']} | {data['phone']} | {data['institution']}"), ln=True, align='C')
    pdf.ln(10)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(10)
    
    sections = [("SUMMARY", 'bio'), ("EDUCATION", 'education'), ("PUBLICATIONS", 'publications')]
    
    for title, key in sections:
        pdf.set_font("Helvetica", 'B', 14)
        pdf.cell(0, 10, txt=title, ln=True)
        pdf.set_font("Helvetica", size=11)
        pdf.multi_cell(0, 5, txt=clean(data[key]))
        pdf.ln(5)

    return pdf.output(dest='S').encode('latin-1')
