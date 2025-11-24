import requests
import pandas as pd
import streamlit as st
from deep_translator import GoogleTranslator
from fpdf import FPDF
import re
from datetime import date

# --- YARDIMCI: GEREKSİZ KELİMELERİ TEMİZLE (Özet İçin) ---
def extract_keywords(text):
    stop_words = [
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", 
        "is", "are", "was", "were", "be", "been", "this", "that", "these", "those", 
        "study", "research", "paper", "article", "thesis", "analysis", "investigation",
        "method", "result", "conclusion", "abstract", "introduction", "aim", "scope"
    ]
    # Sadece harfleri al
    text = re.sub(r'[^a-zA-Z\s]', '', str(text).lower())
    words = text.split()
    # Anlamlı kelimeleri seç
    meaningful_words = [w for w in words if w not in stop_words and len(w) > 3]
    # İlk 8 kelime yeterli
    return " ".join(meaningful_words[:8])

# --- ANA ARAMA MOTORU ---
def get_journals_from_openalex(text_input, mode="abstract"):
    base_url = "https://api.openalex.org/works"
    # API Kimliği (Engel yememek için)
    headers = {'User-Agent': 'mailto:admin@pubscout.com'}
    
    columns = ["Dergi Adı", "Yayınevi", "Q Değeri", "Link", "Kaynak", "Atıf Gücü"]
    journal_list = []

    # --- MOD A: ABSTRACT (ÖZET) ---
    if mode == "abstract" and text_input:
        # 1. Çeviri
        try:
            translated = GoogleTranslator(source='auto', target='en').translate(text_input)
            if not translated: translated = text_input
        except:
            translated = text_input
            
        # 2. Akıllı Kelime Seçimi
        keywords = extract_keywords(translated)
        
        # Eğer kelime kalmadıysa orijinalden al
        if len(keywords) < 3: keywords = translated

        params = {
            "search": keywords,
            "per-page": 50,
            "filter": "type:article",
            "select": "primary_location,title,cited_by_count"
        }
        
        try:
            resp = requests.get(base_url, params=params, headers=headers)
            results = resp.json().get('results', [])
        except:
            results = []

    # --- MOD B: DOI (REFERANS LİSTESİ) ---
    elif mode == "doi" and text_input:
        # Temizlik: https, doi:, boşluklar vs. temizle
        clean_text = text_input.replace("https://doi.org/", "").replace("doi:", "").strip()
        
        # Regex ile metindeki TÜM DOI formatlarını yakala (10.xxxx/yyyy)
        raw_dois = re.findall(r'(10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+)', clean_text)
        
        # Benzersizleri al
        unique_dois = list(set(raw_dois))
        
        results = []
        # İlk 15 DOI'yi tara (Performans için)
        for doi in unique_dois[:15]:
            doi = doi.rstrip(".,)")
            try:
                # API İsteği
                api_url = f"https://api.openalex.org/works/https://doi.org/{doi}"
                res = requests.get(api_url, headers=headers)
                
                if res.status_code == 200:
                    results.append(res.json())
                else:
                    # Yedek yöntem
                    res2 = requests.get(f"https://api.openalex.org/works?filter=doi:https://doi.org/{doi}", headers=headers)
                    if res2.status_code == 200 and res2.json()['results']:
                        results.extend(res2.json()['results'])
            except: pass
            
    else:
        return pd.DataFrame(columns=columns)

    # --- SONUÇLARI LİSTELE ---
    for work in results:
        try:
            loc = work.get('primary_location', {})
            if loc and loc.get('source'):
                source = loc.get('source')
                name = source.get('display_name')
                
                if not name: continue

                pub = source.get('host_organization_name')
                link = source.get('homepage_url')
                imp = work.get('cited_by_count', 0)
                q_val = "Q1" if imp > 50 else "Q2" if imp > 20 else "Q3" if imp > 5 else "Q4"

                journal_list.append({
                    "Dergi Adı": name,
                    "Yayınevi": pub,
                    "Q Değeri": q_val,
                    "Link": link,
                    "Kaynak": "Referans (DOI)" if mode == "doi" else "Özet (Konu)",
                    "Atıf Gücü": imp
                })
        except: continue
    
    df = pd.DataFrame(journal_list)
    if df.empty: return pd.DataFrame(columns=columns)
    
    return df

# --- DİĞER ARAÇLAR (Hatasız Çalışması İçin) ---
def analyze_sdg_goals(text):
    if not text: return pd.DataFrame()
    sdg_keywords = {"SDG 3 (Sağlık)": ["health", "cancer"], "SDG 4 (Eğitim)": ["education"], "SDG 9 (Teknoloji)": ["ai", "data"]}
    text = str(text).lower()
    matched = [{"Hedef": k, "Skor": sum(1 for w in v if w in text)} for k, v in sdg_keywords.items()]
    df = pd.DataFrame(matched).sort_values(by="Skor", ascending=False)
    return df[df['Skor'] > 0]

def generate_cover_letter(data):
    return f"Dear Editor,\n\nI submit '{data['title']}' for {data['journal']}.\nTopic: {data['topic']}.\n\nSincerely,\n{data['author']}"

def generate_reviewer_response(comment, tone="Polite"):
    return "Response generated."

def find_collaborators(topic):
    url = "https://api.openalex.org/works"
    params = {"search": topic, "per-page": 10, "sort": "cited_by_count:desc"}
    try:
        r = requests.get(url, params=params, headers={'User-Agent': 'mailto:admin@pubscout.com'})
        res = r.json().get('results', [])
        auths = []
        for w in res:
            if w.get('authorships'):
                a = w['authorships'][0]['author']
                auths.append({"Yazar": a['display_name'], "Kurum": "-", "Makale": w['title'], "Atıf": w['cited_by_count']})
        return pd.DataFrame(auths).drop_duplicates('Yazar').head(5)
    except: return pd.DataFrame()

def check_predatory(name):
    fake = ["International Journal of Advanced Science", "Predatory Reports", "Fake Science"]
    return any(x.lower() in str(name).lower() for x in fake)

@st.cache_resource
def load_ai_detector():
    return pipeline("text-classification", model="roberta-base-openai-detector")

def check_ai_probability(text):
    return {"label": "Analiz Edilemedi", "score": 0, "color": "gray"}

def create_academic_cv(data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(40, 10, f"CV: {data['name']}")
    return pdf.output(dest='S').encode('latin-1')

def convert_reference_style(text, fmt):
    return text
