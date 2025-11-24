import requests
import pandas as pd
import streamlit as st
from transformers import pipeline
from deep_translator import GoogleTranslator
from fpdf import FPDF
import re
from datetime import date

# --- 1. TEMEL ARAMA MOTORU (HATA ÖNLEYİCİLİ) ---
def get_journals_from_openalex(text_input, mode="abstract"):
    base_url = "https://api.openalex.org/works"
    journal_list = []

    # Standart Sütun İsimleri (Boş gelse bile hata vermemesi için)
    columns = ["Dergi Adı", "Yayınevi", "Q Değeri", "Link", "Kaynak", "Atıf Gücü"]

    # --- MOD A: ABSTRACT ---
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

    # --- MOD B: DOI ---
    elif mode == "doi" and text_input and "10." in text_input:
        # Regex ile DOI yakala
        raw_dois = re.findall(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', text_input, re.IGNORECASE)
        results = []
        # Tekrar edenleri temizle (Set kullanarak)
        unique_dois = list(set(raw_dois))
        
        for doi in unique_dois[:15]: 
            try:
                clean = "https://doi.org/" + doi
                res = requests.get(f"https://api.openalex.org/works/{clean}")
                if res.status_code == 200: results.append(res.json())
            except: pass
    else:
        # Eğer girdi boşsa boş DataFrame döndür (Sütunlar tanımlı!)
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
                    "Kaynak": mode.upper(), # 'ABSTRACT' veya 'DOI'
                    "Atıf Gücü": imp
                })
    
    # Listeden DataFrame oluştur
    df = pd.DataFrame(journal_list)
    
    # Eğer sonuç yoksa bile sütunları oluştur ki sonraki adımda hata vermesin
    if df.empty:
        return pd.DataFrame(columns=columns)
        
    return df

# --- 2. HİBRİD ANALİZ (DÜZELTİLDİ: ValueError Fix) ---
def analyze_hybrid_search(abstract_text, doi_text):
    # Başlangıçta boş ama sütunlu DataFrame'ler oluştur
    empty_cols = ["Dergi Adı", "Yayınevi", "Q Değeri", "Link", "Kaynak", "Atıf Gücü"]
    df_abs = pd.DataFrame(columns=empty_cols)
    df_doi = pd.DataFrame(columns=empty_cols)

    # 1. Abstract Taraması
    if abstract_text and len(abstract_text) > 20:
        df_abs = get_journals_from_openalex(abstract_text, mode="abstract")
    
    # 2. DOI Taraması
    if doi_text and "10." in doi_text:
        df_doi = get_journals_from_openalex(doi_text, mode="doi")

    # 3. BİRLEŞTİRME (Kritik Düzeltme: ignore_index=True)
    # Bu komut indeks çakışmasını önler!
    full_df = pd.concat([df_abs, df_doi], ignore_index=True)
    
    if full_df.empty:
        return None

    # 4. Puanlama ve Gruplama
    # groupby işlemi indeksleri değiştirir, bu yüzden dikkatli olmalıyız
    grouped = full_df.groupby(['Dergi Adı', 'Yayınevi', 'Q Değeri', 'Link']).size().reset_index(name='Skor')
    
    # Eşleşme Tipi Belirleme (Güvenli Yöntem)
    def get_source_tag(row):
        # Orijinal listeden bu derginin kaynaklarına bak
        # Filtreleme yaparken string eşleşmesi kullanıyoruz
        matches = full_df[full_df['Dergi Adı'] == row['Dergi Adı']]
        sources = matches['Kaynak'].unique()
        
        if len(sources) > 1:
            return "🔥 GÜÇLÜ EŞLEŞME"
        elif len(sources) == 1:
            return f"Kaynak: {sources[0]}"
        else:
            return "Bilinmiyor"

    # apply fonksiyonu bazen boş veri setinde hata verir, try-except ile saralım
    try:
        grouped['Eşleşme Tipi'] = grouped.apply(get_source_tag, axis=1)
    except ValueError:
        grouped['Eşleşme Tipi'] = "Tek Kaynak"

    # Sıralama (Skor yüksek olan ve Q1 olanlar üstte)
    grouped = grouped.sort_values(by=['Skor', 'Q Değeri'], ascending=[False, True])
    
    return grouped

# --- 3. SDG (BM HEDEFLERİ) ---
def analyze_sdg_goals(text):
    if not text: return pd.DataFrame()
    
    sdg_keywords = {
        "SDG 3: Sağlık ve Kaliteli Yaşam": ["health", "cancer", "disease", "medicine", "virus", "hospital", "patient", "clinical", "therapy"],
        "SDG 4: Nitelikli Eğitim": ["education", "school", "teaching", "learning", "student", "university", "academic"],
        "SDG 7: Temiz Enerji": ["energy", "solar", "wind", "electricity", "renewable", "power", "grid"],
        "SDG 9: Sanayi ve İnovasyon": ["industry", "innovation", "infrastructure", "technology", "ai", "artificial intelligence", "data"],
        "SDG 13: İklim Eylemi": ["climate", "change", "warming", "environment", "emission", "carbon"]
    }
    
    text = text.lower()
    matched_sdgs = []
    
    for sdg, keywords in sdg_keywords.items():
        score = sum(1 for word in keywords if word in text)
        if score > 0:
            matched_sdgs.append({"Hedef": sdg, "Skor": score})
            
    if not matched_sdgs:
        return pd.DataFrame()
        
    df = pd.DataFrame(matched_sdgs).sort_values(by="Skor", ascending=False)
    return df

# --- DİĞER ARAÇLAR (AYNEN KALIYOR) ---
def generate_cover_letter(data):
    today = date.today().strftime("%B %d, %Y")
    return f"""{today}\n\nEditorial Board,\n{data['journal']}\n\nDear Editor-in-Chief,\n\nI am pleased to submit an original research article entitled "{data['title']}" by {data['author']} for consideration in {data['journal']}.\n\nThis study focuses on {data['topic']}. It is appropriate for your journal because {data['reason']}.\n\nSincerely,\n{data['author']}\n{data['institution']}"""

def generate_reviewer_response(comment, tone="Polite"):
    base = "Thank you for this valuable insight. "
    if "Polite" in tone: return base + f"We agree that '{comment[:30]}...' is critical. We revised the text."
    else: return base + f"Regarding '{comment[:30]}...', we respectfully disagree based on our findings."

def find_collaborators(topic):
    url = "https://api.openalex.org/works"
    params = {"search": topic, "per-page": 20, "sort": "cited_by_count:desc"}
    try:
        r = requests.get(url, params=params)
        results = r.json().get('results', [])
        authors = []
        for work in results:
            for authorship in work.get('authorships', [])[:1]:
                auth = authorship.get('author', {})
                inst = authorship.get('institutions', [{}])[0].get('display_name', 'Unknown')
                authors.append({"Yazar": auth.get('display_name'), "Kurum": inst, "Makale": work.get('title'), "Atıf": work.get('cited_by_count')})
        return pd.DataFrame(authors).drop_duplicates(subset=['Yazar']).head(5)
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
    return f"[{fmt}] {text} (Otomatik)"

def create_academic_cv(data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    def clean(t): return str(t).encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(0, 10, txt=clean(data['name']), ln=True, align='C')
    return pdf.output(dest='S').encode('latin-1')
