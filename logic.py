import requests
import pandas as pd
import streamlit as st
from transformers import pipeline
from deep_translator import GoogleTranslator
from fpdf import FPDF
import re
from datetime import date

# --- 1. TEMEL ARAMA MOTORU (AKILLI FALLBACK MEKANİZMALI) ---
def get_journals_from_openalex(text_input, mode="abstract"):
    base_url = "https://api.openalex.org/works"
    
    # Standart Sütun İsimleri
    columns = ["Dergi Adı", "Yayınevi", "Q Değeri", "Link", "Kaynak", "Atıf Gücü"]
    journal_list = []

    # --- MOD A: ABSTRACT (ÖZET) ---
    if mode == "abstract" and text_input and len(text_input) > 5:
        try:
            # 1. Çeviri
            translated = GoogleTranslator(source='auto', target='en').translate(text_input)
            if not translated: translated = text_input
        except:
            translated = text_input
            
        # 2. STRATEJİ: Önce detaylı ara, bulamazsan genel ara (Fallback)
        # Önce ilk 20 kelime ile dene
        keywords = " ".join(translated.split()[:20])
        params = {"search": keywords, "per-page": 50, "filter": "type:article", "select": "primary_location,title,cited_by_count"}
        
        try:
            resp = requests.get(base_url, params=params)
            results = resp.json().get('results', [])
            
            # 3. Eğer sonuç BOŞ ise, aramayı gevşet (Sadece ilk 6 kelimeyle ara)
            if not results:
                short_keywords = " ".join(translated.split()[:6])
                params["search"] = short_keywords
                resp_retry = requests.get(base_url, params=params)
                results = resp_retry.json().get('results', [])
                
        except:
            results = []

    # --- MOD B: DOI (REFERANS) ---
    elif mode == "doi" and text_input:
        # Temizlik
        clean_text = text_input.replace("https://doi.org/", "").replace("doi:", "")
        # Esnek Regex
        raw_dois = re.findall(r'(10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+)', clean_text)
        unique_dois = list(set(raw_dois))
        
        results = []
        for doi in unique_dois[:10]: # İlk 10 DOI
            doi = doi.rstrip(".,)")
            try:
                # Yöntem 1: Doğrudan ID ile çek
                api_url = f"https://api.openalex.org/works/https://doi.org/{doi}"
                res = requests.get(api_url)
                if res.status_code == 200:
                    results.append(res.json())
                else:
                    # Yöntem 2: Filtre ile ara (Daha esnek)
                    res2 = requests.get(f"https://api.openalex.org/works?filter=doi:https://doi.org/{doi}")
                    if res2.status_code == 200 and res2.json()['results']:
                        results.extend(res2.json()['results'])
            except: pass
    else:
        return pd.DataFrame(columns=columns)

    # --- SONUÇLARI İŞLE ---
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
    
    df = pd.DataFrame(journal_list)
    if df.empty: return pd.DataFrame(columns=columns)
    return df

# --- 2. HİBRİD ANALİZ (GÜÇLENDİRİLDİ) ---
def analyze_hybrid_search(abstract_text, doi_text):
    empty_cols = ["Dergi Adı", "Yayınevi", "Q Değeri", "Link", "Kaynak", "Atıf Gücü"]
    df_abs = pd.DataFrame(columns=empty_cols)
    df_doi = pd.DataFrame(columns=empty_cols)

    # 1. Aramalar
    if abstract_text and len(abstract_text) > 10:
        df_abs = get_journals_from_openalex(abstract_text, mode="abstract")
    
    if doi_text and "10." in doi_text:
        df_doi = get_journals_from_openalex(doi_text, mode="doi")

    # 2. Birleştirme (ignore_index=True ÇOK ÖNEMLİ)
    full_df = pd.concat([df_abs, df_doi], ignore_index=True)
    
    if full_df.empty:
        return None

    # 3. Gruplama
    # Eğer 'Kaynak' sütunu kaybolursa diye önlem
    if 'Kaynak' not in full_df.columns:
        full_df['Kaynak'] = "GENEL"

    # groupby yaparken 'Kaynak' sütununu hariç tutuyoruz ki sayıları toplayabilelim
    grouped = full_df.groupby(['Dergi Adı', 'Yayınevi', 'Q Değeri', 'Link']).size().reset_index(name='Skor')
    
    # Eşleşme Tipi Belirleme
    def get_source_tag(row):
        try:
            matches = full_df[full_df['Dergi Adı'] == row['Dergi Adı']]
            sources = matches['Kaynak'].unique()
            if len(sources) > 1: return "🔥 GÜÇLÜ EŞLEŞME"
            return f"Kaynak: {sources[0]}"
        except:
            return "Tek Kaynak"

    grouped['Eşleşme Tipi'] = grouped.apply(get_source_tag, axis=1)
    
    # 4. Sıralama (Skor > Q Değeri)
    grouped = grouped.sort_values(by=['Skor', 'Q Değeri'], ascending=[False, True])
    
    return grouped

# --- 3. SDG ANALİZİ ---
def analyze_sdg_goals(text):
    if not text: return pd.DataFrame()
    sdg_keywords = {
        "SDG 3: Sağlık": ["health", "disease", "cancer", "medicine", "clinical", "virus"],
        "SDG 4: Eğitim": ["education", "school", "student", "learning", "teaching"],
        "SDG 7: Enerji": ["energy", "solar", "wind", "renewable", "power"],
        "SDG 9: Sanayi/AI": ["industry", "ai", "technology", "innovation", "data"],
        "SDG 13: İklim": ["climate", "emission", "environment", "carbon", "warming"]
    }
    text = str(text).lower()
    matched = [{"Hedef": k, "Skor": sum(1 for w in v if w in text)} for k, v in sdg_keywords.items()]
    df = pd.DataFrame(matched).sort_values(by="Skor", ascending=False)
    return df[df['Skor'] > 0] # Sadece skoru olanları döndür

# --- 4. DİĞER FONKSİYONLAR (AYNEN KALIYOR) ---
def generate_cover_letter(data):
    today = date.today().strftime("%B %d, %Y")
    return f"{today}\n\nDear Editor,\n\nI submit '{data['title']}' for {data['journal']}.\nTopic: {data['topic']}.\n\nSincerely,\n{data['author']}"

def generate_reviewer_response(comment, tone="Polite"):
    return f"Thank you. We agree that '{comment[:20]}...' is important and revised accordingly."

def find_collaborators(topic):
    url = "https://api.openalex.org/works"
    params = {"search": topic, "per-page": 20, "sort": "cited_by_count:desc"}
    try:
        r = requests.get(url, params=params)
        res = r.json().get('results', [])
        auths = []
        for w in res:
            for a in w.get('authorships', [])[:1]:
                auths.append({"Yazar": a['author']['display_name'], "Kurum": a['institutions'][0]['display_name'] if a['institutions'] else "-", "Makale": w['title'], "Atıf": w['cited_by_count']})
        return pd.DataFrame(auths).drop_duplicates('Yazar').head(5)
    except: return pd.DataFrame()

def check_predatory(name):
    fake = ["International Journal of Advanced Science", "Predatory Reports", "Fake Science"]
    return any(x.lower() in str(name).lower() for x in fake)

@st.cache_resource
def load_ai_detector():
    return pipeline("text-classification", model="roberta-base-openai-detector")

def check_ai_probability(text):
    if not text or len(text) < 50: return None
    try:
        clf = load_ai_detector()
        res = clf(text[:512])[0]
        lbl = "Yapay Zeka (AI)" if res['label']=='Fake' else "İnsan"
        clr = "#FF4B4B" if res['label']=='Fake' else "#00CC96"
        return {"label": lbl, "score": res['score'], "color": clr}
    except: return None

def convert_reference_style(text, fmt):
    return f"[{fmt}] {text} (Converted)"

def create_academic_cv(data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, str(data['name']).encode('latin-1','replace').decode('latin-1'), ln=True)
    return pdf.output(dest='S').encode('latin-1')
