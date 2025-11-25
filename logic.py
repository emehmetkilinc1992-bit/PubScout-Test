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

# --- YARDIMCI: FREKANS TABANLI KELİME AYIKLAYICI ---
def extract_keywords_frequency(text):
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
    
    text_clean = re.sub(r'[^a-zA-Z0-9\-\s]', '', str(text).lower())
    words = text_clean.split()
    
    meaningful_words = [w for w in words if w not in stop_words and len(w) > 2]
    word_counts = Counter(meaningful_words)
    top_items = word_counts.most_common(15)
    top_keywords = [item[0] for item in top_items]
    
    return " ".join(top_keywords[:10])

# --- 1. REFERANS BULUCU ---
def find_relevant_references(text_input):
    try:
        try:
            if " ve " in text_input or " bir " in text_input:
                translated = GoogleTranslator(source='auto', target='en').translate(text_input)
            else: translated = text_input
        except: translated = text_input
        
        keywords = extract_keywords_frequency(translated)
        if len(keywords) < 3: keywords = " ".join(translated.split()[:5])

        params = {
            "search": keywords,
            "per-page": 15,
            "sort": "relevance_score:desc", 
            "filter": "type:article",
            "select": "title,publication_year,cited_by_count,authorships,doi,id,primary_location"
        }
        
        r = requests.get(f"{BASE_URL}/works", params=params, headers=HEADERS)
        results = r.json().get('results', [])
        
        # Fallback
        if not results:
             params["sort"] = "cited_by_count:desc"
             params["search"] = " ".join(keywords.split()[:3])
             r = requests.get(f"{BASE_URL}/works", params=params, headers=HEADERS)
             results = r.json().get('results', [])

        ref_list = []
        for work in results:
            author = work['authorships'][0]['author']['display_name'] if work.get('authorships') else "Unknown"
            link = work.get('doi') if work.get('doi') else work.get('id')
            journal = work['primary_location']['source'].get('display_name', 'Unknown') if work.get('primary_location') and work['primary_location'].get('source') else "Unknown Journal"

            ref_list.append({
                "Başlık": work['title'],
                "Yazar": author,
                "Yıl": work.get('publication_year'),
                "Dergi": journal,
                "Atıf": work.get('cited_by_count'),
                "Link": link,
                "APA": f"{author.split()[-1]}, {author[0]}. ({work.get('publication_year')}). {work['title']}. {journal}."
            })
        return pd.DataFrame(ref_list)
    except: return pd.DataFrame()

# --- 2. KURUMSAL ANALİZ ---
def analyze_university_stats(uni_name):
    try:
        r_inst = requests.get(f"{BASE_URL}/institutions", params={"search": uni_name}, headers=HEADERS)
        inst_data = r_inst.json().get('results', [])
        if not inst_data: return None, pd.DataFrame()
            
        best_match = inst_data[0]
        inst_id = best_match['id']
        uni_display_name = best_match['display_name']
        
        params = {
            "filter": f"institutions.id:{inst_id},type:article,from_publication_date:{date.today().year - 10}-01-01",
            "select": "primary_location,publication_year,cited_by_count",
            "per-page": 200,
        }

        stats_data = []
        for page in range(1, 6):
            params['page'] = page
            r = requests.get(f"{BASE_URL}/works", params=params, headers=HEADERS)
            data = r.json().get('results', [])
            if not data: break
            stats_data.extend(data)
            
        if not stats_data: return uni_display_name, pd.DataFrame()

        processed_list = []
        for item in stats_data:
            if not item.get('primary_location') or not item['primary_location'].get('source'): continue
            src = item['primary_location']['source']
            imp = src.get('cited_by_count', 0)
            if imp > 20000: q = "Q1"
            elif imp > 5000: q = "Q2"
            elif imp > 1000: q = "Q3"
            else: q = "Q4"
            processed_list.append({"Yıl": item.get('publication_year'), "Q Değeri": q, "Makale Atıfı": item.get('cited_by_count', 0)})
        return uni_display_name, pd.DataFrame(processed_list)
    except: return None, pd.DataFrame()

# --- 3. DERGİ BULMA MOTORU ---
def get_journals_from_openalex(text_input, mode="abstract"):
    columns = ["Dergi Adı", "Yayınevi", "Q Değeri", "Link", "Kaynak", "Atıf Gücü"]
    journal_list = []

    if mode == "abstract" and text_input:
        try:
            translated = GoogleTranslator(source='auto', target='en').translate(text_input)
            if not translated: translated = text_input
        except: translated = text_input
        
        keywords = extract_keywords_frequency(translated)
        if len(keywords)<3: keywords = translated

        try:
            r = requests.get(f"{BASE_URL}/works", params={"search":keywords,"per-page":50,"filter":"type:article","select":"primary_location,title,cited_by_count","sort":"relevance_score:desc"}, headers=HEADERS)
            results = r.json().get('results', [])
            if not results:
                first_word = keywords.split()[0] if keywords else "science"
                r = requests.get(f"{BASE_URL}/works", params={"search":first_word,"per-page":50}, headers=HEADERS)
                results = r.json().get('results', [])
        except: results = []

    elif mode == "doi" and text_input:
        clean = text_input.replace("https://doi.org/","").replace("doi:","").strip()
        dois = list(set(re.findall(r'(10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+)', clean)))
        results = []
        for d in dois[:15]:
            try:
                r = requests.get(f"{BASE_URL}/works/https://doi.org/{d.rstrip('.,)')}", headers=HEADERS)
                if r.status_code==200: results.append(r.json())
            except: pass
    else: return pd.DataFrame(columns=columns)

    for w in results:
        try:
            loc = w.get('primary_location', {})
            if loc and loc.get('source'):
                src = loc.get('source')
                nm = src.get('display_name')
                if not nm: continue
                imp = w.get('cited_by_count', 0)
                q = "Q1" if imp>50 else "Q2" if imp>20 else "Q3" if imp>5 else "Q4"
                journal_list.append({"Dergi Adı":nm, "Yayınevi":src.get('host_organization_name'), "Q Değeri":q, "Link":src.get('homepage_url'), "Kaynak":mode.upper(), "Atıf Gücü":imp})
        except: continue
    
    df = pd.DataFrame(journal_list)
    return df.drop_duplicates('Dergi Adı') if not df.empty else pd.DataFrame(columns=columns)

# --- 4. STRATEJİ ARAÇLARI ---
def analyze_trends(topic):
    try:
        r = requests.get(f"{BASE_URL}/works", params={"search":topic, "group_by":"publication_year"}, headers=HEADERS)
        df = pd.DataFrame(r.json().get('group_by', []))
        if df.empty: return pd.DataFrame()
        df.columns=['Yıl','Makale Sayısı']
        df['Yıl'] = df['Yıl'].astype(int)
        return df[(df['Yıl']>=date.today().year-15) & (df['Yıl']<=date.today().year)].sort_values('Yıl')
    except: return pd.DataFrame()

def find_funders(topic):
    try:
        r = requests.get(f"{BASE_URL}/works", params={"search":topic, "select":"grants", "per-page":50}, headers=HEADERS)
        funders = [g['funder'] for w in r.json().get('results',[]) for g in w.get('grants',[]) if g.get('funder')]
        if not funders: return pd.DataFrame()
        df = pd.DataFrame(funders).value_counts().reset_index()
        df.columns=['Kurum Adı','Destek Sayısı']
        return df.head(10)
    except: return pd.DataFrame()

def analyze_concepts(topic):
    try:
        r = requests.get(f"{BASE_URL}/concepts", params={"search":topic}, headers=HEADERS)
        data = [{"Kavram":c['display_name'], "Alaka Skoru":c['relevance_score'], "Makale Sayısı":c['works_count'], "Ana Kategori":"Alanlar"} for c in r.json().get('results',[])]
        return pd.DataFrame(data).head(15)
    except: return pd.DataFrame()

# --- 5. DİĞER ARAÇLAR ---
def analyze_sdg_goals(text):
    if not text: return pd.DataFrame()
    keys = {"SDG 3 (Sağlık)":["health","cancer","car-t"], "SDG 4 (Eğitim)":["education"], "SDG 9 (AI/Tech)":["ai","data"], "SDG 13 (İklim)":["climate"]}
    m = [{"Hedef":k, "Skor":sum(1 for x in v if x in str(text).lower())} for k,v in keys.items()]
    return pd.DataFrame(m).sort_values("Skor", ascending=False)[pd.DataFrame(m)['Skor']>0]

def find_collaborators(topic):
    try:
        r = requests.get(f"{BASE_URL}/works", params={"search":topic, "per-page":10, "sort":"cited_by_count:desc"}, headers=HEADERS)
        auths = [{"Yazar":w['authorships'][0]['author']['display_name'], "Kurum":w['authorships'][0]['institutions'][0]['display_name'] if w['authorships'][0].get('institutions') else "-", "Makale":w['title'], "Atıf":w['cited_by_count']} for w in r.json().get('results',[]) if w.get('authorships')]
        return pd.DataFrame(auths).drop_duplicates('Yazar').head(5)
    except: return pd.DataFrame()

def generate_cover_letter(data): return f"Dear Editor,\nSubmission: {data.get('title','')}\nSincerely, {data.get('author','')}"
def generate_reviewer_response(c): return "Revised based on comments."
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
    pdf=FPDF(); pdf.add_page(); pdf.set_font("Arial",size=12); pdf.cell(40,10,f"CV: {data.get('name')}"); return pdf.output(dest='S').encode('latin-1')
def convert_reference_style(text, fmt): return text
