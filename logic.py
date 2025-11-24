import requests
import pandas as pd
import streamlit as st
from transformers import pipeline
from deep_translator import GoogleTranslator
from fpdf import FPDF
import re

# --- 1. OPENALEX DERGİ BULMA (ABSTRACT & DOI) ---
def get_journals_from_openalex(text_input, mode="abstract"):
    """
    Mode: 'abstract' -> Özetten kelime çıkarır (Çeviri destekli).
    Mode: 'doi' -> Girilen DOI listesindeki dergileri çeker.
    """
    base_url = "https://api.openalex.org/works"
    journal_list = []

    if mode == "abstract":
        # 1. Adım: Otomatik Çeviri (Türkçe -> İngilizce)
        try:
            translated_text = GoogleTranslator(source='auto', target='en').translate(text_input)
            if not translated_text: translated_text = text_input
        except:
            translated_text = text_input
            
        # 2. Adım: Anahtar Kelime Çıkarma (İlk 30 kelime)
        keywords = " ".join(translated_text.split()[:30])
        params = {
            "search": keywords,
            "per-page": 50,
            "filter": "type:article",
            "select": "primary_location,title,cited_by_count,publication_year"
        }
        try:
            response = requests.get(base_url, params=params)
            results = response.json().get('results', [])
        except:
            results = []

    elif mode == "doi":
        # DOI Listesini Temizle ve Tarat
        raw_dois = re.findall(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', text_input, re.IGNORECASE)
        results = []
        
        # İlk 10 DOI'yi kontrol et
        for doi in raw_dois[:10]: 
            try:
                clean_doi = "https://doi.org/" + doi
                res = requests.get(f"https://api.openalex.org/works/{clean_doi}")
                if res.status_code == 200:
                    results.append(res.json())
            except:
                pass

    # --- ORTAK SONUÇ İŞLEME ---
    for work in results:
        loc = work.get('primary_location', {})
        if loc and loc.get('source'):
            source = loc.get('source')
            journal_name = source.get('display_name')
            publisher = source.get('host_organization_name')
            homepage_url = source.get('homepage_url') # Dergi Ana Sayfası
            impact_score = work.get('cited_by_count', 0)
            
            # Q Değeri Simülasyonu
            if impact_score > 50: q_val = "Q1"
            elif impact_score > 20: q_val = "Q2"
            elif impact_score > 5: q_val = "Q3"
            else: q_val = "Q4"

            if journal_name:
                journal_list.append({
                    "Dergi Adı": journal_name,
                    "Yayınevi": publisher,
                    "Tahmini Q Değeri": q_val,
                    "Referans/Benzer": work.get('title'),
                    "Atıf Gücü": impact_score,
                    "Link": homepage_url
                })
    
    return pd.DataFrame(journal_list)

# --- 2. PREDATORY KONTROL ---
def check_predatory(journal_name):
    fake_predatory_list = ["International Journal of Advanced Science", "Predatory Reports", "Fake Science", "Global Scientific"]
    if any(pred.lower() in str(journal_name).lower() for pred in fake_predatory_list):
        return True
    return False

# --- 3. AI DEDEKTÖR ---
@st.cache_resource
def load_ai_detector():
    return pipeline("text-classification", model="roberta-base-openai-detector")

def check_ai_probability(text):
    if not text or len(text) < 50: return None, "Metin çok kısa."
    try:
        classifier = load_ai_detector()
        result = classifier(text[:512])[0]
        if result['label'] == 'Fake':
            return {"label": "Yapay Zeka (AI)", "score": result['score'], "color": "#FF4B4B", "message": "⚠️ AI şüphesi yüksek."}
        else:
            return {"label": "İnsan (Doğal)", "score": result['score'], "color": "#00CC96", "message": "✅ İnsan yazımı görünüyor."}
    except Exception as e:
        return None, str(e)

# --- 4. REFERANS DÖNÜŞTÜRÜCÜ ---
def convert_reference_style(ref_text, target_format):
    if not ref_text: return ""
    if target_format == "APA 7":
        return f"[APA 7] {ref_text} (Düzenlendi)"
    elif target_format == "IEEE":
        return f"[1] {ref_text.replace('(', '').replace(')', '')}."
    return ref_text

# --- 5. CV OLUŞTURUCU (PDF) ---
def create_academic_cv(data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    
    # Basit encode/decode ile Türkçe karakter hatalarını önle (replace)
    def clean_text(text):
        return str(text).encode('latin-1', 'replace').decode('latin-1')

    # Başlık
    pdf.set_font("Helvetica", 'B', 20)
    pdf.cell(0, 15, txt=clean_text(data['name']), ln=True, align='C')
    
    pdf.set_font("Helvetica", 'I', 14)
    pdf.cell(0, 10, txt=clean_text(data['title']), ln=True, align='C')
    pdf.ln(5)
    
    # İletişim
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 5, txt=clean_text(f"{data['email']} | {data['phone']} | {data['institution']}"), ln=True, align='C')
    pdf.ln(10)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(10)
    
    # Bölümler
    sections = [("ACADEMIC SUMMARY", 'bio'), ("EDUCATION", 'education'), ("PUBLICATIONS", 'publications')]
    
    for title, key in sections:
        pdf.set_font("Helvetica", 'B', 14)
        pdf.set_text_color(15, 44, 89)
        pdf.cell(0, 10, txt=title, ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", size=11)
        pdf.multi_cell(0, 5, txt=clean_text(data[key]))
        pdf.ln(5)

    return pdf.output(dest='S').encode('latin-1')
