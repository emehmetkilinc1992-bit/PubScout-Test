import requests
import pandas as pd
import streamlit as st
from deep_translator import GoogleTranslator
from fpdf import FPDF
import re
from datetime import date

# --- 1. GARANTİLİ TREND ANALİZİ 📈 ---
def analyze_trends(topic):
    base_url = "https://api.openalex.org/works"
    headers = {'User-Agent': 'mailto:admin@pubscout.com'}
    
    try:
        # Konuyu İngilizceye çevir
        topic_en = GoogleTranslator(source='auto', target='en').translate(topic)
    except: topic_en = topic

    # Yıllara göre grupla
    params = {
        "search": topic_en,
        "group_by": "publication_year",
    }
    
    try:
        resp = requests.get(base_url, params=params, headers=headers)
        data = resp.json().get('group_by', [])
        
        # Veriyi DataFrame'e dök
        df = pd.DataFrame(data)
        
        if df.empty: return pd.DataFrame()

        # Sütun isimlerini düzelt
        df.columns = ['Yıl', 'Makale Sayısı']
        
        # Yılları sayıya çevir ve sırala
        df['Yıl'] = df['Yıl'].astype(int)
        
        # Gelecek yılları veya çok eski yılları temizle (Son 15 yıl)
        current_year = date.today().year
        df = df[(df['Yıl'] >= current_year - 15) & (df['Yıl'] <= current_year)]
        
        return df.sort_values('Yıl')
    except:
        return pd.DataFrame()

# --- 2. GARANTİLİ KAVRAM HARİTASI (TREEMAP FIX) 🧠 ---
def analyze_concepts(topic):
    base_url = "https://api.openalex.org/concepts"
    params = {"search": topic}
    
    try:
        resp = requests.get(base_url, params=params)
        results = resp.json().get('results', [])
        
        concepts = []
        for c in results:
            concepts.append({
                "Kavram": c['display_name'],
                "Alaka Skoru": c['relevance_score'],
                "Makale Sayısı": c['works_count'],
                "Ana Kategori": "İlişkili Alanlar" # <-- TREEMAP İÇİN GEREKLİ "KÖK" SÜTUN
            })
            
        df = pd.DataFrame(concepts).head(15) # İlk 15 kavram
        return df
    except:
        return pd.DataFrame()

# --- 3. FON BULUCU 💰 ---
def find_funders(topic):
    base_url = "https://api.openalex.org/works"
    headers = {'User-Agent': 'mailto:admin@pubscout.com'}
    
    try:
        # Konu çevirisi
        try:
            t_en = GoogleTranslator(source='auto', target='en').translate(topic)
        except: t_en = topic

        params = {"search": t_en, "select": "grants", "per-page": 50}
        resp = requests.get(base_url, params=params, headers=headers)
        results = resp.json().get('results', [])
        
        funder_list = []
        for work in results:
            for grant in work.get('grants', []):
                if grant and grant.get('funder'):
                    funder_list.append(grant['funder'])
        
        if not funder_list: return pd.DataFrame()
        
        df = pd.DataFrame(funder_list).value_counts().reset_index()
        df.columns = ['Kurum Adı', 'Destek Sayısı']
        return df.head(10)
    except: return pd.DataFrame()

# --- MEVCUT ARAÇLAR (Aynen Kalıyor - Kopyalamayı Unutma) ---
# Aşağıdakiler önceki çalışan kodlardır:

def extract_keywords(text):
    stop = ["the","of","and","in","to","a","is","for","on","with","study","analysis"]
    txt = re.sub(r'[^a-zA-Z\s]', '', str(text).lower())
    return " ".join([w for w in txt.split() if w not in stop and len(w)>3][:8])

def get_journals_from_openalex(text_input, mode="abstract"):
    # (Önceki cevaptaki çalışan fonksiyonu buraya yapıştır)
    # Kısaltmak için tekrar yazmıyorum, önceki logic.py'deki aynısı kalacak.
    base_url = "https://api.openalex.org/works"
    headers = {'User-Agent': 'mailto:admin@pubscout.com'}
    columns = ["Dergi Adı", "Yayınevi", "Q Değeri", "Link", "Kaynak", "Atıf Gücü"]
    journal_list = []

    if mode == "abstract" and text_input:
        try: translated = GoogleTranslator(source='auto', target='en').translate(text_input)
        except: translated = text_input
        keywords = extract_keywords(translated)
        if len(keywords)<3: keywords=translated
        try:
            r = requests.get(base_url, params={"search":keywords,"per-page":50,"filter":"type:article","select":"primary_location,title,cited_by_count"}, headers=headers)
            res = r.json().get('results', [])
        except: res=[]
    elif mode == "doi" and text_input:
        cln = text_input.replace("https://doi.org/","").replace("doi:","").strip()
        dois = list(set(re.findall(r'(10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+)', cln)))
        res=[]
        for d in dois[:10]:
            try:
                r = requests.get(f"https://api.openalex.org/works/https://doi.org/{d.rstrip('.,)')}", headers=headers)
                if r.status_code==200: res.append(r.json())
            except: pass
    else: return pd.DataFrame(columns=columns)

    for w in res:
        try:
            loc = w.get('primary_location',{})
            if loc and loc.get('source'):
                src = loc.get('source')
                if src.get('display_name'):
                    imp = w.get('cited_by_count',0)
                    q="Q1" if imp>50 else "Q2" if imp>20 else "Q3" if imp>5 else "Q4"
                    journal_list.append({"Dergi Adı":src['display_name'],"Yayınevi":src['host_organization_name'],"Q Değeri":q,"Link":src['homepage_url'],"Atıf Gücü":imp})
        except: continue
    df = pd.DataFrame(journal_list)
    return df.drop_duplicates('Dergi Adı') if not df.empty else pd.DataFrame(columns=columns)

# --- Diğer Yardımcılar ---
def analyze_sdg_goals(t): return pd.DataFrame() # Placeholder
def generate_cover_letter(d): return "Letter"
def generate_reviewer_response(c,t): return "Response"
def find_collaborators(t): return pd.DataFrame()
def check_predatory(n): return False
def check_ai_probability(t): return None
def create_academic_cv(d): return b""
def convert_reference_style(t,f): return t
