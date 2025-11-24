import requests
import pandas as pd
import streamlit as st
from deep_translator import GoogleTranslator
from fpdf import FPDF
import re
from datetime import date

# --- YARDIMCI: GEREKSİZ KELİMELERİ TEMİZLE ---
def extract_keywords(text):
    # Bu kelimeler aramayı bozar, bunları atacağız
    stop_words = [
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", 
        "is", "are", "was", "were", "be", "been", "this", "that", "these", "those", 
        "study", "research", "paper", "article", "thesis", "analysis", "investigation",
        "method", "result", "conclusion", "abstract", "introduction"
    ]
    
    # Sadece harfleri al, küçük harfe çevir
    text = re.sub(r'[^a-zA-Z\s]', '', text.lower())
    words = text.split()
    
    # Yasaklı kelimeleri ve 3 harften kısa kelimeleri at
    meaningful_words = [w for w in words if w not in stop_words and len(w) > 3]
    
    # En önemli ilk 5 kelimeyi döndür
    return " ".join(meaningful_words[:5])

# --- 1. TEMEL ARAMA MOTORU ---
def get_journals_from_openalex(text_input, mode="abstract"):
    base_url = "https://api.openalex.org/works"
    headers = {'User-Agent': 'mailto:admin@pubscout.com'}
    columns = ["Dergi Adı", "Yayınevi", "Q Değeri", "Link", "Kaynak", "Atıf Gücü"]
    journal_list = []

    # --- SENARYO A: ABSTRACT (ÖZET) ---
    if mode == "abstract" and text_input:
        # 1. Çeviri
        try:
            translated = GoogleTranslator(source='auto', target='en').translate(text_input)
            if not translated: translated = text_input
        except:
            translated = text_input # Çeviri bozulursa olduğu gibi dene
            
        # 2. AKILLI AYIKLAMA (YENİ ÖZELLİK)
        # Bütün cümleyi değil, sadece "et" kısmını alıyoruz
        keywords = extract_keywords(translated)
        
        # Eğer çok az kelime kaldıysa (bazen olur), orijinalden parça al
        if len(keywords) < 3: 
            keywords = translated.split()[:3]
            if isinstance(keywords, list): keywords = " ".join(keywords)

        params = {
            "search": keywords, # Artık temiz kelimeler gidiyor
            "per-page": 50,
            "filter": "type:article",
            "select": "primary_location,title,cited_by_count"
        }
        
        try:
            resp = requests.get(base_url, params=params, headers=headers)
            results = resp.json().get('results', [])
            
            # Sonuç yoksa TEK KELİME ile dene (En geniş arama)
            if not results:
                single_keyword = keywords.split()[0] if keywords else "science"
                params["search"] = single_keyword
                resp2 = requests.get(base_url, params=params, headers=headers)
                results = resp2.json().get('results', [])
        except:
            results = []

    # --- SENARYO B: DOI (REFERANS) ---
    elif mode == "doi" and text_input:
        clean_text = text_input.replace("https://doi.org/", "").replace("doi:", "").strip()
        raw_dois = re.findall(r'(10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+)', clean_text)
        unique_dois = list(set(raw_dois))
        
        results = []
        for doi in unique_dois[:10]:
            doi = doi.rstrip(".,)")
            try:
                # API ÇAĞRISI
                api_url = f"https://api.openalex.org/works/https://doi.org/{doi}"
                res = requests.get(api_url, headers=headers)
                if res.status_code == 200:
                    results.append(res.json())
                else:
                    # Alternatif Çağrı
                    res2 = requests.get(f"https://api.openalex.org/works?filter=doi:https://doi.org/{doi}", headers=headers)
                    if res2.status_code == 200 and res2.json()['results']:
                        results.extend(res2.json()['results'])
            except: pass
    else:
        return pd.DataFrame(columns=columns)

    # --- SONUÇLARI İŞLE ---
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
                    "Dergi Adı": name, "Yayınevi": pub, "Q Değeri": q_val,
                    "Link": link, "Kaynak": mode.upper(), "Atıf Gücü": imp
                })
        except: continue
    
    df = pd.DataFrame(journal_list)
    if df.empty: return pd.DataFrame(columns=columns)
    
    # Aynı dergileri tekilleştir (Daha temiz liste için)
    return df.drop_duplicates(subset=['Dergi Adı'])

# --- 2. HİBRİD ANALİZ ---
def analyze_hybrid_search(abstract_text, doi_text):
    empty_cols = ["Dergi Adı", "Yayınevi", "Q Değeri", "Link", "Kaynak", "Atıf Gücü"]
    df_abs = pd.DataFrame(columns=empty_cols)
    df_doi = pd.DataFrame(columns=empty_cols)

    if abstract_text and len(abstract_text) > 3: # Eşik değerini düşürdüm
        df_abs = get_journals_from_openalex(abstract_text, mode="abstract")
    
    if doi_text and "10." in doi_text:
        df_doi = get_journals_from_openalex(doi_text, mode="doi")

    full_df = pd.concat([df_abs, df_doi], ignore_index=True)
    if full_df.empty: return None

    # Basit Skorlama
    grouped = full_df.groupby(['Dergi Adı', 'Yayınevi', 'Q Değeri', 'Link']).size().reset_index(name='Skor')
    grouped = grouped.sort_values(by=['Skor', 'Q Değeri'], ascending=[False, True])
    
    # Basit Eşleşme Etiketi
    grouped['Eşleşme Tipi'] = grouped['Skor'].apply(lambda x: "🔥 GÜÇLÜ EŞLEŞME" if x > 1 else "Standart")

    return grouped

# --- DİĞER ARAÇLAR (HATA VERMEMESİ İÇİN TAM LİSTE) ---
def analyze_sdg_goals(text):
    if not text: return pd.DataFrame()
    sdg_keywords = {"SDG 3 (Sağlık)": ["health", "cancer"], "SDG 4 (Eğitim)": ["education"], "SDG 9 (Teknoloji)": ["ai", "data"]}
    text = str(text).lower()
    matched = [{"Hedef": k, "Skor": sum(1 for w in v if w in text)} for k, v in sdg_keywords.items()]
    df = pd.DataFrame(matched).sort_values(by="Skor", ascending=False)
    return df[df['Skor'] > 0]

def generate_cover_letter(data):
    return f"Dear Editor,\nSubmission: {data['title']}.\nSincerely, {data['author']}"

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
        return pd.DataFrame(auths).head(5)
    except: return pd.DataFrame()

def check_predatory(name):
    return False

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
