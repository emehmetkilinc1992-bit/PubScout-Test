import requests
import pandas as pd
import streamlit as st
from deep_translator import GoogleTranslator
from fpdf import FPDF
import re
from datetime import date

# --- YENİ: 1. TREND ANALİZİ MOTORU 📈 ---
def analyze_trends(topic):
    """
    Bir konunun son 10 yıldaki yükseliş/düşüş trendini analiz eder.
    """
    base_url = "https://api.openalex.org/works"
    headers = {'User-Agent': 'mailto:admin@pubscout.com'}
    
    # Konuyu İngilizceye çevir (Daha iyi sonuç için)
    try:
        topic_en = GoogleTranslator(source='auto', target='en').translate(topic)
    except: topic_en = topic

    params = {
        "search": topic_en,
        "group_by": "publication_year",
        "per_page": 200
    }
    
    try:
        resp = requests.get(base_url, params=params, headers=headers)
        data = resp.json().get('group_by', [])
        
        # DataFrame'e çevir ve son 10 yılı filtrele
        df = pd.DataFrame(data)
        df = df[df['key'].astype(int) >= (date.today().year - 10)]
        df = df.sort_values('key') # Yıla göre sırala
        df.columns = ['Yıl', 'Makale Sayısı']
        return df
    except:
        return pd.DataFrame()

# --- YENİ: 2. HİBE VE FON BULUCU 💰 ---
def find_funders(topic):
    """
    Bu konuyu en çok fonlayan kurumları bulur.
    """
    base_url = "https://api.openalex.org/works"
    headers = {'User-Agent': 'mailto:admin@pubscout.com'}
    
    try:
        topic_en = GoogleTranslator(source='auto', target='en').translate(topic)
    except: topic_en = topic

    params = {
        "search": topic_en,
        "select": "grants",
        "per-page": 50 
    }
    
    try:
        resp = requests.get(base_url, params=params, headers=headers)
        results = resp.json().get('results', [])
        
        funder_list = []
        for work in results:
            for grant in work.get('grants', []):
                if grant.get('funder'):
                    funder_list.append(grant['funder'])
        
        if not funder_list: return pd.DataFrame()
        
        # Sayım yap
        df = pd.DataFrame(funder_list).value_counts().reset_index()
        df.columns = ['Kurum Adı', 'Desteklediği Makale Sayısı']
        return df.head(10) # İlk 10 fon sağlayıcı
    except:
        return pd.DataFrame()

# --- YENİ: 3. LİTERATÜR HARİTASI (KAVRAMLAR) 🧠 ---
def analyze_concepts(topic):
    """
    Konuyla ilişkili diğer akademik kavramları (Concepts) bulur.
    """
    base_url = "https://api.openalex.org/concepts"
    params = {"search": topic}
    
    try:
        resp = requests.get(base_url, params=params)
        results = resp.json().get('results', [])
        
        concepts = []
        for c in results:
            concepts.append({
                "Kavram": c['display_name'],
                "Seviye": c['level'], # 0: Genel, 1: Alt Dal
                "Alaka Skoru": c['relevance_score'],
                "Makale Sayısı": c['works_count']
            })
        return pd.DataFrame(concepts).head(10)
    except:
        return pd.DataFrame()

# --- MEVCUT FONKSİYONLAR (AYNEN KORUNDU) ---
def get_journals_from_openalex(text_input, mode="abstract"):
    base_url = "https://api.openalex.org/works"
    headers = {'User-Agent': 'mailto:admin@pubscout.com'}
    columns = ["Dergi Adı", "Yayınevi", "Q Değeri", "Link", "Kaynak", "Atıf Gücü"]
    journal_list = []

    if mode == "abstract" and text_input:
        try:
            translated = GoogleTranslator(source='auto', target='en').translate(text_input)
            if not translated: translated = text_input
        except: translated = text_input
        keywords = " ".join(translated.split()[:20])
        params = {"search": keywords, "per-page": 50, "filter": "type:article", "select": "primary_location,title,cited_by_count"}
        try:
            resp = requests.get(base_url, params=params, headers=headers)
            results = resp.json().get('results', [])
            if not results:
                short = " ".join(translated.split()[:6])
                resp = requests.get(base_url, params={"search":short, "per-page":50}, headers=headers)
                results = resp.json().get('results', [])
        except: results = []

    elif mode == "doi" and text_input:
        clean = text_input.replace("https://doi.org/", "").replace("doi:", "").strip()
        dois = list(set(re.findall(r'(10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+)', clean)))
        results = []
        for d in dois[:10]:
            d = d.rstrip(".,)")
            try:
                r = requests.get(f"https://api.openalex.org/works/https://doi.org/{d}", headers=headers)
                if r.status_code == 200: results.append(r.json())
            except: pass
    else: return pd.DataFrame(columns=columns)

    for w in results:
        try:
            loc = w.get('primary_location', {})
            if loc and loc.get('source'):
                src = loc.get('source')
                nm = src.get('display_name')
                if not nm: continue
                imp = w.get('cited_by_count', 0)
                q = "Q1" if imp > 50 else "Q2" if imp > 20 else "Q3" if imp > 5 else "Q4"
                journal_list.append({"Dergi Adı": nm, "Yayınevi": src.get('host_organization_name'), "Q Değeri": q, "Link": src.get('homepage_url'), "Kaynak": mode.upper(), "Atıf Gücü": imp})
        except: continue
    df = pd.DataFrame(journal_list)
    return df.drop_duplicates('Dergi Adı') if not df.empty else pd.DataFrame(columns=columns)

def analyze_sdg_goals(text):
    if not text: return pd.DataFrame()
    keys = {"SDG 3 (Sağlık)": ["health"], "SDG 4 (Eğitim)": ["education"], "SDG 9 (Teknoloji)": ["ai"], "SDG 13 (İklim)": ["climate"]}
    txt = str(text).lower()
    m = [{"Hedef": k, "Skor": sum(1 for x in v if x in txt)} for k,v in keys.items()]
    return pd.DataFrame(m).sort_values("Skor", ascending=False)

def generate_cover_letter(data): return f"Dear Editor,\nSubmission: {data['title']}"
def generate_reviewer_response(c, t): return "Response generated."
def find_collaborators(topic):
    # Basit collaborator fonksiyonu
    return pd.DataFrame() # Şimdilik boş dönsün, trendlere odaklanalım
def check_predatory(name): return False
def check_ai_probability(text): return None
def create_academic_cv(data):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Helvetica", size=12); pdf.cell(40, 10, "CV"); return pdf.output(dest='S').encode('latin-1')
def convert_reference_style(text, fmt): return text
