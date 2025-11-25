import requests
import pandas as pd
import streamlit as st
from deep_translator import GoogleTranslator
from fpdf import FPDF
import re
from datetime import date
from transformers import pipeline
from collections import Counter

# --- API AYARLARI ---
BASE_URL = "https://api.openalex.org"
HEADERS = {'User-Agent': 'mailto:admin@pubscout.com'}

# --- YARDIMCI: FREKANS TABANLI KELİME AYIKLAYICI (TF) ---
def extract_keywords_frequency(text):
    """
    Metindeki kelimeleri sayar, en çok tekrar eden teknik terimleri bulur.
    CAR-T, COVID-19 gibi terimleri korur.
    """
    # 1. Yasaklı Kelimeler (Stop Words) - Geniş Akademik Liste
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", 
        "is", "are", "was", "were", "be", "been", "this", "that", "these", "those", "it", "its",
        "study", "research", "paper", "article", "thesis", "analysis", "investigation", "report",
        "method", "result", "results", "conclusion", "abstract", "introduction", "aim", "scope",
        "discuss", "review", "current", "future", "possibilities", "treatment", "design", "use",
        "background", "objective", "methods", "conclusions", "significant", "showed", "using",
        "based", "potential", "high", "new", "development", "application", "data", "model",
        "observed", "found", "compared", "also", "between", "during", "through", "after", "before",
        "however", "although", "therefore", "thus", "hence", "can", "could", "may", "might", "will",
        "carried", "briefly", "describes", "looks", "forward", "concluded", "increasingly", "important",
        "provide", "shown", "performed", "obtained", "different", "various", "general", "specific"
    }
    
    # 2. Metni Temizle (Tire işaretini koruyoruz!)
    # Sadece harf, rakam, boşluk ve tire kalacak.
    text_clean = re.sub(r'[^a-zA-Z0-9\-\s]', '', str(text).lower())
    
    # 3. Kelimeleri Listele
    words = text_clean.split()
    
    # 4. Filtreleme (Stop words at ve en az 3 harfli olsun)
    # "car-t" gibi kelimeler burada korunur.
    meaningful_words = [w for w in words if w not in stop_words and len(w) > 2]
    
    # 5. SAYIM İŞLEMİ (En kritik adım)
    word_counts = Counter(meaningful_words)
    
    # 6. En çok geçen 15 kelimeyi al
    top_items = word_counts.most_common(15)
    
    # Sadece kelimeleri al
    top_keywords = [item[0] for item in top_items]
    
    # Arama motoruna en popüler ilk 8-10 tanesini gönderiyoruz
    final_query = " ".join(top_keywords[:10])
    
    return final_query

# --- 1. REFERANS BULUCU (LITERATURE SEARCH) 📚 ---
def find_relevant_references(text_input):
    try:
        # 1. Çeviri (Türkçe ise İngilizceye çevir)
        try:
            if " ve " in text_input or " bir " in text_input or " çalışmada " in text_input:
                translated = GoogleTranslator(source='auto', target='en').translate(text_input)
            else: translated = text_input
        except: translated = text_input
        
        # 2. FREKANS ANALİZİ İLE ANAHTAR KELİME BUL
        keywords = extract_keywords_frequency(translated)
        
        # Eğer kelime çıkmazsa (çok kısa metin), metnin kendisinden parça al
        if len(keywords) < 3: 
            keywords
