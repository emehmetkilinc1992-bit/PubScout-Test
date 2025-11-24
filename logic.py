import requests
import pandas as pd
import streamlit as st
from deep_translator import GoogleTranslator
from fpdf import FPDF
import re
from datetime import date

# --- STANDART ARAMA MOTORU ---
def get_journals_from_openalex(text_input, mode="abstract"):
    base_url = "https://api.openalex.org/works"
    
    # 1. TEMEL HAZIRLIK
    # Boş dönerse hata vermemesi için standart sütunlar
    empty_df = pd.DataFrame(columns=["Dergi Adı", "Yayınevi", "Q Değeri", "Link", "Atıf Gücü", "Kaynak"])
    journal_list = []

    # --- SENARYO A: ABSTRACT (ÖZET) ---
    if mode == "abstract" and text_input and len(text_input) > 5:
        # Çeviri (Hata verirse orijinal metni kullan)
        try:
            translated = GoogleTranslator(source='auto', target='en').translate(text_input)
            if not translated: translated = text_input
        except:
            translated = text_input
            
        # Sadece ilk 15 kelimeyi al (Çok uzun sorgu API'yi bozar)
        keywords = " ".join(translated.split()[:15])
        
        params = {
            "search": keywords,
            "per-page": 30, # Çok fazla veri çekip sistemi yorma
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

    # --- SENARYO B: DOI (REFERANS) ---
    elif mode == "doi" and text_input:
        # DOI Temizliği (Basit Regex)
        # Sadece "10." ile başlayan ve boşluğa kadar devam eden kısımları al
        raw_dois = re.findall(r'(10\.\d{4,9}/[^,\s]+)', text_input)
        results = []
        
        for doi in list(set(raw_dois))[:10]: # İlk 10 tanesi yeterli
            doi = doi.rstrip(".,)") # Sonundaki nokta virgülü temizle
            try:
                # Doğrudan ID ile çağır
                res = requests.get(f"https://api.openalex.org/works/https://doi.org/{doi}")
                if res.status_code == 200:
                    results.append(res.json())
            except: pass
            
    else:
        return empty_df

    # --- SONUÇLARI LİSTELE (VERİ AYIKLAMA) ---
    for work in results:
        try:
            loc = work.get('primary_location', {})
            if loc and loc.get('source'):
                source = loc.get('source')
                name = source.get('display_name')
                
                # Eğer dergi adı yoksa listeye ekleme
                if not name: continue

                pub = source.get('host_organization_name')
                link = source.get('homepage_url')
                imp = work.get('cited_by_count', 0)
                
                # Q Değeri
                q = "Q1" if imp > 50 else "Q2" if imp > 20 else "Q3" if imp > 5 else "Q4"

                journal_list.append({
                    "Dergi Adı": name,
                    "Yayınevi": pub,
                    "Q Değeri": q,
                    "Link": link,
                    "Atıf Gücü": imp,
                    "Kaynak": "DOI" if mode == "doi" else "ÖZET"
                })
        except: continue
            
    if not journal_list:
        return empty_df
        
    return pd.DataFrame(journal_list)

# --- 2. HİBRİD ANALİZ (BASİTLEŞTİRİLMİŞ MERGE) ---
def analyze_hybrid_search(abstract_text, doi_text):
    
    # İki tarafı da ayrı ayrı çalıştır
    df_abs = get_journals_from_openalex(abstract_text, mode="abstract")
    df_doi = get_journals_from_openalex(doi_text, mode="doi")

    # Basitçe alt alta birleştir (Karmaşık işlem yok)
    # ignore_index=True ÇOK ÖNEMLİ, yoksa hata verir
    full_df = pd.concat([df_abs, df_doi], ignore_index=True)
    
    if full_df.empty:
        return None

    # Aynı dergileri birleştirip sayısını bulalım (Skorlama)
    # as_index=False diyerek DataFrame yapısını koruyoruz
    grouped = full_df.groupby(['Dergi Adı', 'Yayınevi', 'Q Değeri', 'Link'], as_index=False).size()
    
    # Sütun adını 'size' yerine 'Skor' yapalım
    grouped = grouped.rename(columns={'size': 'Skor'})
    
    # En yüksek skor en üstte olsun
    grouped = grouped.sort_values(by='Skor', ascending=False)
    
    # Eşleşme Tipi sütunu ekleyelim (Basit Versiyon)
    grouped['Eşleşme Tipi'] = grouped['Skor'].apply(lambda x: "🔥 GÜÇLÜ EŞLEŞME" if x > 1 else "Standart")

    return grouped

# --- DİĞER YARDIMCI ARAÇLAR ---
# (Hata vermemesi için bunları da ekliyoruz)

def analyze_sdg_goals(text):
    # Basit Placeholder
    if not text: return pd.DataFrame()
    return pd.DataFrame([{"Hedef": "Genel Bilim", "Skor": 1}])

def generate_cover_letter(data):
    return f"Dear Editor,\nI submit '{data['title']}' to {data['journal']}."

def generate_reviewer_response(comment, tone="Polite"):
    return "Response generated."

def find_collaborators(topic):
    return pd.DataFrame()

def check_predatory(name):
    fake = ["International Journal of Advanced Science", "Predatory Reports", "Fake Science"]
    return any(x.lower() in str(name).lower() for x in fake)

def check_ai_probability(text):
    return {"label": "Analiz Edilemedi", "score": 0, "color": "gray"}

def create_academic_cv(data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "CV", ln=True)
    return pdf.output(dest='S').encode('latin-1')

def convert_reference_style(text, fmt):
    return text
