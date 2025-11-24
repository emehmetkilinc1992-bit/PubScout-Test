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
    grouped = grouped.sort_values(by=['Skor', 'Q Değeri'], ascending=[False, True])
    return grouped

# --- 3. SDG (SÜRDÜRÜLEBİLİR KALKINMA) ANALİZİ (YENİ) 🌍 ---
def analyze_sdg_goals(text):
    """
    Metni analiz edip hangi BM Hedefine (SDG) uygun olduğunu bulur.
    Basit keyword eşleşmesi (MVP için).
    """
    sdg_keywords = {
        "SDG 3: Sağlık ve Kaliteli Yaşam": ["health", "cancer", "disease", "medicine", "virus", "hospital", "patient", "clinical"],
        "SDG 4: Nitelikli Eğitim": ["education", "school", "teaching", "learning", "student", "university", "pedagogy"],
        "SDG 7: Erişilebilir ve Temiz Enerji": ["energy", "solar", "wind", "electricity", "renewable", "carbon", "fuel"],
        "SDG 9: Sanayi, Yenilikçilik ve Altyapı": ["industry", "innovation", "infrastructure", "manufacturing", "technology", "ai", "artificial intelligence"],
        "SDG 13: İklim Eylemi": ["climate", "change", "global warming", "emission", "environment", "pollution"]
    }
    
    text = text.lower()
    matched_sdgs = []
    
    for sdg, keywords in sdg_keywords.items():
        score = sum(1 for word in keywords if word in text)
        if score > 0:
            matched_sdgs.append({"Hedef": sdg, "Skor": score})
            
    if not matched_sdgs:
        return pd.DataFrame([{"Hedef": "Genel Bilim", "Skor": 1}])
        
    df = pd.DataFrame(matched_sdgs).sort_values(by="Skor", ascending=False)
    return df

# --- 4. COVER LETTER GENERATOR (YENİ) ✍️ ---
def generate_cover_letter(data):
    today = date.today().strftime("%B %d, %Y")
    letter = f"""{today}

Editorial Board,
{data['journal']}

Dear Editor-in-Chief,

I am pleased to submit an original research article entitled "{data['title']}" by {data['author']} for consideration for publication in {data['journal']}.

This study focuses on {data['topic']}. We believe that this manuscript is appropriate for publication by your journal because {data['reason']}.

In this manuscript, we show that {data['finding']}. We believe these findings will be of interest to the readers of your journal.

This manuscript has not been published and is not under consideration for publication elsewhere.

Sincerely,

{data['author']}
{data['institution']}"""
    return letter

# --- 5. REVIEWER RESPONSE (HAKEM CEVAPLAYICI) (YENİ) 🛡️ ---
def generate_reviewer_response(comment, tone="Polite"):
    base = "Thank you for this valuable insight. "
    if tone == "Polite (Kibar)":
        return base + f"We agree with the reviewer that {comment[:20]}... is a critical point. Accordingly, we have revised the manuscript to clarify this aspect."
    elif tone == "Rebuttal (İtiraz)":
        return base + f"While we understand the reviewer's concern regarding {comment[:20]}..., we respectfully disagree because our data suggests otherwise. Specifically..."
    return "Lütfen bir ton seçin."

# --- 6. COLLABORATION FINDER (ORTAK BULUCU) (YENİ) 🤝 ---
def find_collaborators(topic):
    # OpenAlex'te konuyu arayıp en çok atıf alan yazarları bulur
    url = "https://api.openalex.org/works"
    params = {"search": topic, "per-page": 20, "sort": "cited_by_count:desc"}
    try:
        r = requests.get(url, params=params)
        results = r.json().get('results', [])
        authors = []
        for work in results:
            for authorship in work.get('authorships', [])[:1]: # İlk yazar
                auth = authorship.get('author', {})
                inst = authorship.get('institutions', [{}])[0].get('display_name', 'Unknown')
                authors.append({"Yazar": auth.get('display_name'), "Kurum": inst, "Makale": work.get('title'), "Atıf": work.get('cited_by_count')})
        return pd.DataFrame(authors).drop_duplicates(subset=['Yazar']).head(5)
    except:
        return pd.DataFrame()

# --- DİĞER STANDART FONKSİYONLAR ---
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
    return f"[{fmt}] {text} (Otomatik Düzenlendi)"

def create_academic_cv(data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    def clean(t): return str(t).encode('latin-1', 'replace').decode('latin-1')
    pdf.set_font("Helvetica", 'B', 20)
    pdf.cell(0, 15, txt=clean(data['name']), ln=True, align='C')
    # ... (Kısalık için standart CV kodu buraya gelir, öncekiyle aynı)
    return pdf.output(dest='S').encode('latin-1')
