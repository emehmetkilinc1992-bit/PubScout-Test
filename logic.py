import requests
import pandas as pd
import streamlit as st
from transformers import pipeline
from deep_translator import GoogleTranslator
from fpdf import FPDF
import re

# --- 1. TEMEL ARAMA MOTORU (TEKLİ MODLAR) ---
def get_journals_from_openalex(text_input, mode="abstract"):
    base_url = "https://api.openalex.org/works"
    journal_list = []

    # --- MOD A: ABSTRACT ---
    if mode == "abstract" and text_input and len(text_input) > 10:
        try:
            # Çeviri
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

    # --- MOD B: DOI ---
    elif mode == "doi" and text_input and "10." in text_input:
        raw_dois = re.findall(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', text_input, re.IGNORECASE)
        results = []
        for doi in raw_dois[:15]: # İlk 15 DOI'ye bak
            try:
                clean = "https://doi.org/" + doi
                res = requests.get(f"https://api.openalex.org/works/{clean}")
                if res.status_code == 200: results.append(res.json())
            except: pass
    else:
        return pd.DataFrame() # Boş döner

    # --- SONUÇLARI LİSTELE ---
    for work in results:
        loc = work.get('primary_location', {})
        if loc and loc.get('source'):
            source = loc.get('source')
            name = source.get('display_name')
            pub = source.get('host_organization_name')
            link = source.get('homepage_url')
            # Q Değeri (Simülasyon)
            imp = work.get('cited_by_count', 0)
            q_val = "Q1" if imp > 50 else "Q2" if imp > 20 else "Q3" if imp > 5 else "Q4"

            if name:
                journal_list.append({
                    "Dergi Adı": name,
                    "Yayınevi": pub,
                    "Q Değeri": q_val,
                    "Link": link,
                    "Kaynak": mode.upper() # "ABSTRACT" veya "DOI" yazar
                })
    
    return pd.DataFrame(journal_list)

# --- 2. HİBRİD ARAMA MOTORU (YENİ SÜPER FONKSİYON) 🚀 ---
def analyze_hybrid_search(abstract_text, doi_text):
    """
    Hem Abstract hem DOI sonuçlarını alır, birleştirir ve puanlar.
    """
    df_abs = pd.DataFrame()
    df_doi = pd.DataFrame()

    # 1. Abstract Taraması
    if abstract_text and len(abstract_text) > 20:
        df_abs = get_journals_from_openalex(abstract_text, mode="abstract")
    
    # 2. DOI Taraması
    if doi_text and "10." in doi_text:
        df_doi = get_journals_from_openalex(doi_text, mode="doi")

    # 3. Birleştirme (Merging)
    full_df = pd.concat([df_abs, df_doi])
    
    if full_df.empty:
        return None

    # 4. Puanlama Algoritması
    # Her dergi kaç kere geçti? (Hem Abstract hem DOI'de varsa puanı 2 olur)
    grouped = full_df.groupby(['Dergi Adı', 'Yayınevi', 'Q Değeri', 'Link']).size().reset_index(name='Skor')
    
    # Kaynak bilgisini birleştir (Örn: "ABSTRACT + DOI")
    # Bunu yapmak için karmaşık işlem yerine basit bir hile yapıyoruz:
    # Eğer Skor > 1 ise, demek ki iki tarafta da bulundu.
    def get_source_tag(row, original_df):
        sources = original_df[original_df['Dergi Adı'] == row['Dergi Adı']]['Kaynak'].unique()
        if len(sources) > 1:
            return "🔥 GÜÇLÜ EŞLEŞME (Konu + Referans)"
        return f"Tek Yönlü: {sources[0]}"

    grouped['Eşleşme Tipi'] = grouped.apply(lambda x: get_source_tag(x, full_df), axis=1)
    
    # Skora göre sırala (En yüksek puan en üstte)
    grouped = grouped.sort_values(by='Skor', ascending=False)
    
    return grouped

# --- DİĞER YARDIMCI ARAÇLAR (Aynen Kalıyor) ---
def check_predatory(journal_name):
    fake_list = ["International Journal of Advanced Science", "Predatory Reports", "Fake Science"]
    return any(x.lower() in str(journal_name).lower() for x in fake_list)

@st.cache_resource
def load_ai_detector():
    return pipeline("text-classification", model="roberta-base-openai-detector")

def check_ai_probability(text):
    if not text or len(text) < 50: return None
    try:
        clf = load_ai_detector()
        res = clf(text[:512])[0]
        label = "Yapay Zeka (AI)" if res['label']=='Fake' else "İnsan (Doğal)"
        color = "#FF4B4B" if res['label']=='Fake' else "#00CC96"
        return {"label": label, "score": res['score'], "color": color}
    except: return None

def convert_reference_style(ref, fmt):
    return f"[{fmt}] {ref} (Converted)"

def create_academic_cv(data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    def clean(t): return str(t).encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(0, 10, txt=clean(data['name']), ln=True, align='C')
    return pdf.output(dest='S').encode('latin-1')
