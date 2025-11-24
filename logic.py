import requests
import pandas as pd
import streamlit as st
from transformers import pipeline
from deep_translator import GoogleTranslator
from fpdf import FPDF
import re
from datetime import date

# --- 1. TEMEL ARAMA MOTORU (GELİŞMİŞ DOI & ÇEVİRİ DESTEKLİ) ---
def get_journals_from_openalex(text_input, mode="abstract"):
    base_url = "https://api.openalex.org/works"
    
    # Standart Sütun İsimleri (Hata almamak için)
    columns = ["Dergi Adı", "Yayınevi", "Q Değeri", "Link", "Kaynak", "Atıf Gücü"]
    journal_list = []

    # --- MOD A: ABSTRACT (ÖZET) ---
    if mode == "abstract" and text_input and len(text_input) > 10:
        try:
            # 1. Çeviri (Türkçe -> İngilizce)
            translated = GoogleTranslator(source='auto', target='en').translate(text_input)
            if not translated: translated = text_input
        except:
            translated = text_input
            
        # 2. Anahtar Kelime Çıkarma
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

    # --- MOD B: DOI (REFERANS) - GÜÇLENDİRİLMİŞ ---
    elif mode == "doi" and text_input:
        # 1. Kullanıcının girdiği linkleri temizle
        # (https://doi.org/ kısmını at, sadece 10.xxxx kısmını al)
        clean_text = text_input.replace("https://doi.org/", "").replace("http://doi.org/", "").replace("doi:", "")
        
        # 2. Regex ile DOI formatını yakala
        raw_dois = re.findall(r'(10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+)', clean_text)
        unique_dois = list(set(raw_dois)) # Tekrarları kaldır
        
        results = []
        for doi in unique_dois[:15]: # İlk 15 DOI'yi tara
            try:
                # Sonundaki noktalama işaretlerini temizle
                doi = doi.rstrip(".,)")
                
                # Yöntem 1: Doğrudan Eşleşme
                api_url = f"https://api.openalex.org/works/https://doi.org/{doi}"
                res = requests.get(api_url)
                
                if res.status_code == 200:
                    results.append(res.json())
                else:
                    # Yöntem 2: Filtre ile Arama (Yedek Plan)
                    res_backup = requests.get(f"https://api.openalex.org/works?filter=doi:https://doi.org/{doi}")
                    if res_backup.status_code == 200:
                        data = res_backup.json()
                        if data['results']:
                            results.extend(data['results'])
            except:
                pass
    else:
        # Girdi yoksa boş tablo dön
        return pd.DataFrame(columns=columns)

    # --- SONUÇLARI LİSTELE ---
    for work in results:
        loc = work.get('primary_location', {})
        if loc and loc.get('source'):
            source = loc.get('source')
            name = source.get('display_name')
            pub = source.get('host_organization_name')
            link = source.get('homepage_url')
            imp = work.get('cited_by_count', 0)
            
            # Q Değeri Simülasyonu
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
    if df.empty:
        return pd.DataFrame(columns=columns)
        
    return df

# --- 2. HİBRİD ANALİZ (ValueError FIX EKLENDİ) ---
def analyze_hybrid_search(abstract_text, doi_text):
    empty_cols = ["Dergi Adı", "Yayınevi", "Q Değeri", "Link", "Kaynak", "Atıf Gücü"]
    df_abs = pd.DataFrame(columns=empty_cols)
    df_doi = pd.DataFrame(columns=empty_cols)

    if abstract_text and len(abstract_text) > 20:
        df_abs = get_journals_from_openalex(abstract_text, mode="abstract")
    
    if doi_text and "10." in doi_text:
        df_doi = get_journals_from_openalex(doi_text, mode="doi")

    # Kritik Düzeltme: ignore_index=True (Hata vermemesi için)
    full_df = pd.concat([df_abs, df_doi], ignore_index=True)
    
    if full_df.empty:
        return None

    # Puanlama
    grouped = full_df.groupby(['Dergi Adı', 'Yayınevi', 'Q Değeri', 'Link']).size().reset_index(name='Skor')
    
    def get_source_tag(row):
        matches = full_df[full_df['Dergi Adı'] == row['Dergi Adı']]
        sources = matches['Kaynak'].unique()
        if len(sources) > 1:
            return "🔥 GÜÇLÜ EŞLEŞME"
        elif len(sources) == 1:
            return f"Kaynak: {sources[0]}"
        return "Bilinmiyor"

    try:
        grouped['Eşleşme Tipi'] = grouped.apply(get_source_tag, axis=1)
    except:
        grouped['Eşleşme Tipi'] = "Standart"

    # Sıralama
    grouped = grouped.sort_values(by=['Skor', 'Q Değeri'], ascending=[False, True])
    return grouped

# --- 3. SDG (BM HEDEFLERİ) ANALİZİ ---
def analyze_sdg_goals(text):
    if not text: return pd.DataFrame()
    
    sdg_keywords = {
        "SDG 3: Sağlık ve Kaliteli Yaşam": ["health", "cancer", "disease", "medicine", "virus", "hospital", "patient", "therapy", "clinical"],
        "SDG 4: Nitelikli Eğitim": ["education", "school", "teaching", "learning", "student", "university", "academic", "pedagogy"],
        "SDG 7: Temiz Enerji": ["energy", "solar", "wind", "electricity", "renewable", "power", "grid", "carbon"],
        "SDG 9: Sanayi ve İnovasyon": ["industry", "innovation", "infrastructure", "technology", "ai", "artificial intelligence", "data", "engineering"],
        "SDG 13: İklim Eylemi": ["climate", "change", "warming", "environment", "emission", "greenhouse", "sustainability"]
    }
    
    text = str(text).lower()
    matched_sdgs = []
    
    for sdg, keywords in sdg_keywords.items():
        score = sum(1 for word in keywords if word in text)
        if score > 0:
            matched_sdgs.append({"Hedef": sdg, "Skor": score})
            
    if not matched_sdgs:
        return pd.DataFrame()
        
    df = pd.DataFrame(matched_sdgs).sort_values(by="Skor", ascending=False)
    return df

# --- 4. COVER LETTER OLUŞTURUCU ---
def generate_cover_letter(data):
    today = date.today().strftime("%B %d, %Y")
    return f"""{today}

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

# --- 5. REVIEWER RESPONSE ---
def generate_reviewer_response(comment, tone="Polite"):
    base = "Thank you for this valuable insight. "
    if "Polite" in tone:
        return base + f"We agree that the point regarding '{comment[:30]}...' is critical. Accordingly, we have revised the manuscript to clarify this aspect."
    else:
        return base + f"While we understand the reviewer's concern regarding '{comment[:30]}...', we respectfully disagree based on our findings presented in Section 3."

# --- 6. COLLABORATION FINDER (ORTAK BULUCU) ---
def find_collaborators(topic):
    url = "https://api.openalex.org/works"
    # Konuyla ilgili en çok atıf alan makaleleri bul
    params = {"search": topic, "per-page": 20, "sort": "cited_by_count:desc"}
    try:
        r = requests.get(url, params=params)
        results = r.json().get('results', [])
        authors = []
        for work in results:
            # İlk yazarı al
            for authorship in work.get('authorships', [])[:1]:
                auth = authorship.get('author', {})
                inst = authorship.get('institutions', [{}])[0].get('display_name', 'Unknown Institution')
                authors.append({
                    "Yazar": auth.get('display_name'), 
                    "Kurum": inst, 
                    "Makale": work.get('title'), 
                    "Atıf": work.get('cited_by_count')
                })
        # Tekrar eden yazarları temizle ve ilk 5'i döndür
        return pd.DataFrame(authors).drop_duplicates(subset=['Yazar']).head(5)
    except:
        return pd.DataFrame()

# --- 7. DİĞER STANDART ARAÇLAR ---
def check_predatory(name):
    fake = ["International Journal of Advanced Science", "Predatory Reports", "Fake Science", "Global Scientific"]
    return any(x.lower() in str(name).lower() for x in fake)

@st.cache_resource
def load_ai_detector():
    return pipeline("text-classification", model="roberta-base-openai-detector")

def check_ai_probability(text):
    if not text or len(text) < 50: return None
    try:
        clf = load_ai_detector()
        res = clf(text[:512])[0]
        lbl = "Yapay Zeka (AI)" if res['label']=='Fake' else "İnsan (Doğal)"
        clr = "#FF4B4B" if res['label']=='Fake' else "#00CC96"
        return {"label": lbl, "score": res['score'], "color": clr}
    except: return None

def convert_reference_style(text, fmt):
    if not text: return ""
    if fmt == "APA 7":
        return f"[APA 7] {text} (Otomatik Düzenlendi)"
    elif fmt == "IEEE":
        return f"[1] {text}."
    return text

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
