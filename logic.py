import requests
import pandas as pd
import streamlit as st
from deep_translator import GoogleTranslator
from fpdf import FPDF
import re
from datetime import date
from transformers import pipeline

# --- YARDIMCI: GEREKSİZ KELİMELERİ TEMİZLE ---
def extract_keywords(text):
    stop_words = [
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", 
        "is", "are", "was", "were", "be", "been", "this", "that", "these", "those", 
        "study", "research", "paper", "article", "thesis", "analysis", "investigation",
        "method", "result", "conclusion", "abstract", "introduction", "aim", "scope"
    ]
    text = re.sub(r'[^a-zA-Z\s]', '', str(text).lower())
    words = text.split()
    meaningful_words = [w for w in words if w not in stop_words and len(w) > 3]
    return " ".join(meaningful_words[:8])

# --- 1. TEMEL ARAMA MOTORU ---
def get_journals_from_openalex(text_input, mode="abstract"):
    base_url = "https://api.openalex.org/works"
    headers = {'User-Agent': 'mailto:admin@pubscout.com'}
    columns = ["Dergi Adı", "Yayınevi", "Q Değeri", "Link", "Kaynak", "Atıf Gücü"]
    journal_list = []

    # --- MOD A: ABSTRACT ---
    if mode == "abstract" and text_input:
        try:
            translated = GoogleTranslator(source='auto', target='en').translate(text_input)
            if not translated: translated = text_input
        except: translated = text_input
            
        keywords = extract_keywords(translated)
        if len(keywords) < 3: keywords = translated

        params = {"search": keywords, "per-page": 50, "filter": "type:article", "select": "primary_location,title,cited_by_count"}
        
        try:
            resp = requests.get(base_url, params=params, headers=headers)
            results = resp.json().get('results', [])
        except: results = []

    # --- MOD B: DOI ---
    elif mode == "doi" and text_input:
        clean_text = text_input.replace("https://doi.org/", "").replace("doi:", "").strip()
        raw_dois = re.findall(r'(10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+)', clean_text)
        unique_dois = list(set(raw_dois))
        results = []
        for doi in unique_dois[:15]:
            doi = doi.rstrip(".,)")
            try:
                api_url = f"https://api.openalex.org/works/https://doi.org/{doi}"
                res = requests.get(api_url, headers=headers)
                if res.status_code == 200: results.append(res.json())
                else:
                    res2 = requests.get(f"https://api.openalex.org/works?filter=doi:https://doi.org/{doi}", headers=headers)
                    if res2.status_code == 200 and res2.json()['results']:
                        results.extend(res2.json()['results'])
            except: pass
    else: return pd.DataFrame(columns=columns)

    # SONUÇLARI İŞLE
    for work in results:
        try:
            loc = work.get('primary_location', {})
            if loc and loc.get('source'):
                source = loc.get('source')
                name = source.get('display_name')
                if not name: continue
                
                imp = work.get('cited_by_count', 0)
                q_val = "Q1" if imp > 50 else "Q2" if imp > 20 else "Q3" if imp > 5 else "Q4"

                journal_list.append({
                    "Dergi Adı": name, "Yayınevi": source.get('host_organization_name'), "Q Değeri": q_val,
                    "Link": source.get('homepage_url'), "Kaynak": "DOI" if mode == "doi" else "ÖZET", "Atıf Gücü": imp
                })
        except: continue
    
    df = pd.DataFrame(journal_list)
    if df.empty: return pd.DataFrame(columns=columns)
    return df

# --- 2. KURUMSAL ANALİZ (ÜNİVERSİTE) ---
def analyze_university_pubs(uni_name):
    base_url = "https://api.openalex.org"
    headers = {'User-Agent': 'mailto:admin@pubscout.com'}
    try:
        r_inst = requests.get(f"{base_url}/institutions", params={"search": uni_name}, headers=headers)
        inst_data = r_inst.json().get('results', [])
        if not inst_data: return None, "Kurum bulunamadı."
            
        best_match = inst_data[0]
        inst_id = best_match['id']
        
        work_params = {"filter": f"institutions.id:{inst_id},type:article", "sort": "publication_date:desc", "per-page": 100}
        r_works = requests.get(f"{base_url}/works", params=work_params, headers=headers)
        
        pub_list = []
        for work in r_works.json().get('results', []):
            if not work.get('primary_location') or not work['primary_location'].get('source'): continue
            src = work['primary_location']['source']
            imp = src.get('cited_by_count', 0)
            
            if imp > 50000: q = "Q1 (Çok Yüksek)"
            elif imp > 10000: q = "Q2 (Yüksek)"
            elif imp > 2000: q = "Q3 (Orta)"
            else: q = "Q4 (Düşük/Yerel)"
            
            pub_list.append({
                "Makale Başlığı": work['title'], "Dergi": src.get('display_name'), 
                "Yayın Yılı": work.get('publication_year'), "Makale Atıfı": work.get('cited_by_count', 0), "Kalite Sınıfı": q
            })
        return pd.DataFrame(pub_list), best_match['display_name']
    except Exception as e: return None, str(e)

# --- 3. TREND ANALİZİ ---
def analyze_trends(topic):
    base_url = "https://api.openalex.org/works"
    headers = {'User-Agent': 'mailto:admin@pubscout.com'}
    try:
        try: topic_en = GoogleTranslator(source='auto', target='en').translate(topic)
        except: topic_en = topic
        params = {"search": topic_en, "group_by": "publication_year"}
        resp = requests.get(base_url, params=params, headers=headers)
        df = pd.DataFrame(resp.json().get('group_by', []))
        if df.empty: return pd.DataFrame()
        df.columns = ['Yıl', 'Makale Sayısı']
        df['Yıl'] = df['Yıl'].astype(int)
        df = df[(df['Yıl'] >= date.today().year - 15) & (df['Yıl'] <= date.today().year)]
        return df.sort_values('Yıl')
    except: return pd.DataFrame()

# --- 4. KAVRAM HARİTASI ---
def analyze_concepts(topic):
    base_url = "https://api.openalex.org/concepts"
    try:
        resp = requests.get(base_url, params={"search": topic})
        concepts = [{"Kavram": c['display_name'], "Alaka Skoru": c['relevance_score'], "Makale Sayısı": c['works_count'], "Ana Kategori": "İlişkili Alanlar"} for c in resp.json().get('results', [])]
        return pd.DataFrame(concepts).head(15)
    except: return pd.DataFrame()

# --- 5. FON BULUCU ---
def find_funders(topic):
    base_url = "https://api.openalex.org/works"
    headers = {'User-Agent': 'mailto:admin@pubscout.com'}
    try:
        try: t_en = GoogleTranslator(source='auto', target='en').translate(topic)
        except: t_en = topic
        resp = requests.get(base_url, params={"search": t_en, "select": "grants", "per-page": 50}, headers=headers)
        funder_list = [g['funder'] for w in resp.json().get('results', []) for g in w.get('grants', []) if g.get('funder')]
        if not funder_list: return pd.DataFrame()
        df = pd.DataFrame(funder_list).value_counts().reset_index()
        df.columns = ['Kurum Adı', 'Destek Sayısı']
        return df.head(10)
    except: return pd.DataFrame()

# --- 6. DİĞER ARAÇLAR ---
def analyze_sdg_goals(text):
    if not text: return pd.DataFrame()
    sdg_keywords = {"SDG 3 (Sağlık)": ["health", "cancer"], "SDG 4 (Eğitim)": ["education"], "SDG 9 (Teknoloji)": ["ai", "data"], "SDG 13 (İklim)": ["climate"]}
    text = str(text).lower()
    matched = [{"Hedef": k, "Skor": sum(1 for w in v if w in text)} for k, v in sdg_keywords.items()]
    return pd.DataFrame(matched).sort_values(by="Skor", ascending=False)[pd.DataFrame(matched)['Skor'] > 0]

def generate_cover_letter(data): return f"Dear Editor,\nSubmission: {data.get('title','')}\nSincerely, {data.get('author','')}"
def generate_reviewer_response(comment): return f"Thank you. Regarding '{comment[:20]}...', we have revised accordingly."
def find_collaborators(topic):
    try:
        r = requests.get("https://api.openalex.org/works", params={"search": topic, "per-page": 10, "sort": "cited_by_count:desc"}, headers={'User-Agent': 'mailto:admin@pubscout.com'})
        auths = [{"Yazar": w['authorships'][0]['author']['display_name'], "Kurum": w['authorships'][0]['institutions'][0]['display_name'] if w['authorships'][0].get('institutions') else "-", "Makale": w['title'], "Atıf": w['cited_by_count']} for w in r.json().get('results', []) if w.get('authorships')]
        return pd.DataFrame(auths).drop_duplicates('Yazar').head(5)
    except: return pd.DataFrame()

def check_predatory(name): return False
@st.cache_resource
def load_ai_detector(): return pipeline("text-classification", model="roberta-base-openai-detector")
def check_ai_probability(text):
    if not text or len(text)<50: return None
    try:
        res = load_ai_detector()(text[:512])[0]
        return {"label": "Yapay Zeka (AI)" if res['label']=='Fake' else "İnsan", "score": res['score'], "color": "#FF4B4B" if res['label']=='Fake' else "#00CC96"}
    except: return None
def create_academic_cv(data):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Helvetica", size=12); pdf.cell(40, 10, f"CV: {data.get('name')}"); return pdf.output(dest='S').encode('latin-1')
def convert_reference_style(text, fmt): return text
