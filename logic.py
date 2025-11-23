import requests
import pandas as pd
import streamlit as st
from transformers import pipeline

# --- 1. OPENALEX DERGİ BULMA MODÜLÜ ---
def get_journals_from_openalex(abstract_text):
    """
    OpenAlex API kullanarak girilen özete benzer makaleleri bulur
    ve bu makalelerin yayınlandığı dergileri analiz eder.
    """
    base_url = "https://api.openalex.org/works"
    
    # Basit anahtar kelime çıkarma (İlk 25 kelime)
    keywords = " ".join(abstract_text.split()[:25])
    
    params = {
        "search": keywords,
        "per-page": 50,
        "filter": "type:article",
        "select": "primary_location,title,cited_by_count,publication_year"
    }

    try:
        response = requests.get(base_url, params=params)
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            
            journal_list = []
            
            for work in results:
                loc = work.get('primary_location', {})
                if loc and loc.get('source'):
                    source = loc.get('source')
                    journal_name = source.get('display_name')
                    publisher = source.get('host_organization_name')
                    
                    # Q Değeri Simülasyonu (Gerçek API'de ücretlidir, burada simüle ediyoruz)
                    impact_score = work.get('cited_by_count', 0)
                    if impact_score > 50: q_val = "Q1"
                    elif impact_score > 20: q_val = "Q2"
                    elif impact_score > 5: q_val = "Q3"
                    else: q_val = "Q4"

                    if journal_name:
                        journal_list.append({
                            "Dergi Adı": journal_name,
                            "Yayınevi": publisher,
                            "Tahmini Q Değeri": q_val,
                            "Benzer Makale": work.get('title'),
                            "Yıl": work.get('publication_year'),
                            "Atıf": impact_score
                        })
            
            return pd.DataFrame(journal_list)
        else:
            return None
    except Exception as e:
        print(f"Hata: {e}")
        return None

# --- 2. PREDATORY (YAĞMACI) KONTROL MODÜLÜ ---
def check_predatory(journal_name):
    """
    Basit Kara Liste Kontrolü.
    """
    fake_predatory_list = [
        "International Journal of Advanced Science", 
        "Predatory Reports", 
        "Fake Science Journal",
        "Global Scientific Journal"
    ]
    
    # Büyük/küçük harf duyarlılığını kaldır
    if any(pred.lower() in str(journal_name).lower() for pred in fake_predatory_list):
        return True
    return False

# --- 3. AI DEDEKTÖR MODÜLÜ (Caching ile Hızlandırılmış) ---
@st.cache_resource
def load_ai_detector():
    """
    Modeli önbelleğe alır, her seferinde tekrar indirmez.
    """
    return pipeline("text-classification", model="roberta-base-openai-detector")

def check_ai_probability(text):
    """
    Metnin AI olma olasılığını ölçer.
    """
    if not text or len(text) < 50:
        return None, "Analiz için metin çok kısa."

    try:
        classifier = load_ai_detector()
        # İlk 512 karakteri analiz et (Hız ve RAM limiti için)
        result = classifier(text[:512])[0]
        
        label = result['label']
        score = result['score']
        
        if label == 'Fake':
            return {
                "label": "Yapay Zeka (AI)",
                "score": score,
                "color": "#FF4B4B", # Kırmızı
                "message": "⚠️ Bu metin yüksek ihtimalle yapay zeka tarafından yazılmış."
            }
        else:
            return {
                "label": "İnsan (Doğal)",
                "score": score,
                "color": "#00CC96", # Yeşil
                "message": "✅ Bu metin doğal ve insan yazımı görünüyor."
            }
    except Exception as e:
        return None, str(e)