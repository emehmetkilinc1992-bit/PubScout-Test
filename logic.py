import requests
import pandas as pd
import streamlit as st # Hata mesajlarını ekrana basmak için
from transformers import pipeline
from deep_translator import GoogleTranslator
from fpdf import FPDF
import re
from datetime import date

# --- 1. TEMEL ARAMA MOTORU (DEBUG MODLU) ---
def get_journals_from_openalex(text_input, mode="abstract"):
    base_url = "https://api.openalex.org/works"
    
    # OpenAlex'in bizi engellememesi için "Kibar" kimlik bilgisi
    headers = {
        'User-Agent': 'mailto:test@pubscout.com' 
    }
    
    columns = ["Dergi Adı", "Yayınevi", "Q Değeri", "Link", "Kaynak", "Atıf Gücü"]
    journal_list = []

    # --- MOD A: ABSTRACT ---
    if mode == "abstract" and text_input:
        
        # 1. Çeviri Denemesi
        try:
            translated = GoogleTranslator(source='auto', target='en').translate(text_input)
            if not translated: 
                translated = text_input
        except Exception as e:
            st.warning(f"⚠️ Çeviri Hatası: {str(e)}") # Ekrana yaz
            translated = text_input

        # 2. Arama Kelimelerini Belirle
        # Çok uzun özetlerde arama bozulur, sadece ilk 15 önemli kelimeyi alalım
        # Noktalama işaretlerini temizleyelim
        clean_text = re.sub(r'[^\w\s]', '', translated)
        keywords = " ".join(clean_text.split()[:15])
        
        # EKRANA DEBUG BİLGİSİ BASALIM (Sorunu görmek için)
        st.info(f"🔍 **Sistem Arka Planda Şunu Arıyor:** '{keywords}'")

        params = {
            "search": keywords,
            "per-page": 50,
            "filter": "type:article",
            "select": "primary_location,title,cited_by_count"
        }
        
        try:
            resp = requests.get(base_url, params=params, headers=headers)
            
            # API DURUMUNU KONTROL ET
            if resp.status_code != 200:
                st.error(f"❌ API Hatası: {resp.status_code} - OpenAlex cevap vermiyor.")
                return pd.DataFrame(columns=columns)
                
            results = resp.json().get('results', [])
            
            # Eğer sonuç yoksa, aramayı çok basitleştirip tekrar dene (FALLBACK)
            if not results:
                st.warning("⚠️ İlk aramada sonuç çıkmadı, daha genel arama yapılıyor...")
                simple_keywords = " ".join(clean_text.split()[:5]) # Sadece ilk 5 kelime
                params["search"] = simple_keywords
                resp_retry = requests.get(base_url, params=params, headers=headers)
                results = resp_retry.json().get('results', [])

        except Exception as e:
            st.error(f"Bağlantı Hatası: {str(e)}")
            results = []

    # --- MOD B: DOI ---
    elif mode == "doi" and text_input:
        # Temizlik
        clean_text = text_input.replace("https://doi.org/", "").replace("doi:", "").strip()
        
        # Daha basit regex (Sadece 10. ile başlayan her şeyi al)
        raw_dois = re.findall(r'(10\.\d{4,9}/[^,\s]+)', clean_text)
        
        # Ekrana ne bulduğunu yaz
        st.info(f"🔗 **Bulunan DOI Numaraları:** {raw_dois}")
        
        results = []
        for doi in raw_dois[:5]: # İlk 5 tanesini dene
            # Sondaki noktalamaları temizle
            doi = doi.rstrip(".,)")
            
            try:
                # 1. Yöntem: Works ID ile
                api_url = f"https://api.openalex.org/works/https://doi.org/{doi}"
                res = requests.get(api_url, headers=headers)
                
                if res.status_code == 200:
                    results.append(res.json())
                else:
                    # 2. Yöntem: Filtre ile (Daha geniş)
                    res2 = requests.get(f"https://api.openalex.org/works?filter=doi:https://doi.org/{doi}", headers=headers)
                    if res2.status_code == 200:
                        data = res2.json()
                        if data['results']:
                            results.extend(data['results'])
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
    
    # DEBUG: Kaç sonuç bulundu?
    if df.empty:
        st.error("❌ Veritabanından sonuç döndü ama işlenebilir 'Dergi Adı' bulunamadı.")
        return pd.DataFrame(columns=columns)
    else:
        # Duplicate'leri sil (Aynı dergi 50 kere gelmesin)
        return df.drop_duplicates(subset=['Dergi Adı'])

# --- 2. HİBRİD ANALİZ ---
def analyze_hybrid_search(abstract_text, doi_text):
    # Boş DataFrame oluştur (Hata önlemek için)
    empty_cols = ["Dergi Adı", "Yayınevi", "Q Değeri", "Link", "Kaynak", "Atıf Gücü"]
    df_abs = pd.DataFrame(columns=empty_cols)
    df_doi = pd.DataFrame(columns=empty_cols)

    # Arama Yap
    if abstract_text and len(abstract_text) > 5:
        df_abs = get_journals_from_openalex(abstract_text, mode="abstract")
    
    if doi_text and "10." in doi_text:
        df_doi = get_journals_from_openalex(doi_text, mode="doi")

    # Birleştir
    full_df = pd.concat([df_abs, df_doi], ignore_index=True)
    
    if full_df.empty:
        return None

    # Puanlama
    grouped = full_df.groupby(['Dergi Adı', 'Yayınevi', 'Q Değeri', 'Link']).size().reset_index(name='Skor')
    
    def get_source_tag(row):
        try:
            matches = full_df[full_df['Dergi Adı'] == row['Dergi Adı']]
            sources = matches['Kaynak'].unique()
            if len(sources) > 1: return "🔥 GÜÇLÜ EŞLEŞME"
            return f"Kaynak: {sources[0]}"
        except: return "Standart"

    grouped['Eşleşme Tipi'] = grouped.apply(get_source_tag, axis=1)
    grouped = grouped.sort_values(by=['Skor', 'Q Değeri'], ascending=[False, True])
    
    return grouped

# --- DİĞERLERİ AYNEN KALIYOR ---
# (analyze_sdg_goals, generate_cover_letter, check_predatory, vb. buraya ekli zaten)
# Dosya bütünlüğü bozulmasın diye buraya diğer fonksiyonları da eklemen gerekir.
# Önceki logic.py'deki diğer fonksiyonları buranın altına yapıştırabilirsin.
# Ben yer kaplamaması için sadece sorunlu kısmı attım.

# --- SDG ANALİZİ ---
def analyze_sdg_goals(text):
    if not text: return pd.DataFrame()
    sdg_keywords = {"SDG 3": ["health"], "SDG 4": ["education"]} # Örnek kısaltma
    # ... (Tam kodu önceki cevaptan alabilirsin)
    return pd.DataFrame() # Placeholder

# --- Eksik fonksiyonları tamamlamak için önceki logic.py dosyasındaki 
# check_predatory, check_ai_probability, create_academic_cv vb. fonksiyonları 
# buraya MUTLAKA yapıştır.
