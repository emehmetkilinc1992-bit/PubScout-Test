import streamlit as st
import pandas as pd
import plotly.express as px
from logic import analyze_hybrid_search, check_predatory, check_ai_probability, create_academic_cv, convert_reference_style

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="PubScout | Akademik Asistan", page_icon="🎓", layout="wide")

# --- CSS TASARIM ---
st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    h1, h2, h3 { color: #0F2C59; }
    
    /* Arama Paneli */
    .search-box {
        background-color: #F8F9FA;
        padding: 30px;
        border-radius: 15px;
        border: 1px solid #eee;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        margin-bottom: 30px;
    }
    
    /* Butonlar */
    .stButton>button {
        background: linear-gradient(90deg, #0F2C59 0%, #1B498F 100%);
        color: white;
        border-radius: 8px;
        border: none;
        height: 45px;
        font-weight: 600;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #00DFA2 0%, #00bfa5 100%);
        color: #0F2C59;
        transform: translateY(-2px);
    }
    </style>
""", unsafe_allow_html=True)

# --- MENÜ ---
with st.sidebar:
    st.title("🎓 PubScout")
    st.info("Kurum: **Demo University**\n*(Premium License)*")
    
    # MENÜ SEÇENEKLERİ (Burada tüm modüller var)
    menu = st.radio("Modüller", 
        ["🏠 Ana Sayfa", "🛠️ Utility Tools", "📝 CV Oluşturucu", "🕵️ AI Ajanı (Beta)", "🛡️ Güvenlik Kontrolü"])

# --- 1. ANA SAYFA (HİBRİD ARAMA) ---
if menu == "🏠 Ana Sayfa":
    st.markdown("<h1 style='text-align:center; font-size: 4rem; margin-bottom:10px;'>PubScout AI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:gray; font-size:1.2rem;'>Özet (Abstract) ve Referanslarınızı (DOI) birlikte analiz ederek en doğru dergiyi bulur.</p>", unsafe_allow_html=True)
    
    # Arama Paneli
    st.markdown('<div class="search-box">', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("1. Makale Özeti (Konu)")
        abstract_input = st.text_area("Özetinizi buraya yapıştırın", height=200, placeholder="Abstract metni...")
    with c2:
        st.subheader("2. Referanslar (Kültür)")
        doi_input = st.text_area("DOI Listesi (Opsiyonel)", height=200, placeholder="10.1007/xxxx, 10.1016/yyyy (Virgülle ayırın)...")
    
    analyze_btn = st.button("🚀 HİBRİD ANALİZİ BAŞLAT", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Analiz Sonuçları
    if analyze_btn:
        if len(abstract_input) < 20 and "10." not in doi_input:
            st.error("Lütfen en az bir alanı doldurun.")
        else:
            with st.spinner('Yapay Zeka konu ve atıf ağlarını çapraz analiz ediyor...'):
                df_results = analyze_hybrid_search(abstract_input, doi_input)
            
            if df_results is not None and not df_results.empty:
                st.success(f"✅ Analiz Tamamlandı! {len(df_results)} dergi bulundu.")
                st.divider()

                col1, col2, col3 = st.columns(3)
                for index, row in df_results.head(3).iterrows():
                    is_predatory = check_predatory(row['Dergi Adı'])
                    card_color = "#FF4B4B" if is_predatory else "#00CC96"
                    status_text = "⚠️ RİSKLİ" if is_predatory else "✅ GÜVENLİ"
                    
                    badge = ""
                    if "GÜÇLÜ" in row['Eşleşme Tipi']:
                        badge = "<div style='background:#FFD700; color:#000; padding:5px; border-radius:5px; font-size:11px; font-weight:bold; margin-bottom:5px; text-align:center;'>⭐ GÜÇLÜ EŞLEŞME</div>"
                    
                    g_link = f"https://www.google.com/search?q={row['Dergi Adı'].replace(' ', '+')}+author+guidelines"

                    with (col1 if index==0 else col2 if index==1 else col3):
                        st.markdown(f"""
                        <div style="background:white; border:1px solid #ddd; padding:20px; border-radius:15px; border-top:5px solid {card_color}; margin-bottom:20px;">
                            {badge}
                            <h4 style="color:#0F2C59; height:45px; overflow:hidden;">{row['Dergi Adı']}</h4>
                            <p style="color:gray; font-size:12px;">{row['Yayınevi']}</p>
                            <div style="display:flex; justify-content:space-between; margin-top:10px;">
                                <span style="font-weight:bold; color:{card_color}">{status_text}</span>
                                <span style="background:#eee; padding:2px 8px; border-radius:4px;">{row['Q Değeri']}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        b1, b2 = st.columns(2)
                        with b1:
                            if row['Link']: st.link_button("🌐 Site", row['Link'], use_container_width=True)
                            else: st.button("🚫", disabled=True)
                        with b2: st.link_button("📝 Rehber", g_link, use_container_width=True)

                st.write("### 📊 Detaylı Sıralama")
                st.dataframe(df_results, use_container_width=True)
            else:
                st.error("Sonuç bulunamadı.")

# --- 2. UTILITY TOOLS (GERİ GELDİ) ---
elif menu == "🛠️ Utility Tools":
    st.header("🛠️ Angarya Yok Edici Araçlar")
    st.write("Akademik yazım sürecindeki teknik işleri hızlandırın.")
    
    c1, c2 = st.columns(2)
    
    # Şablon Bulucu
    with c1:
        st.markdown('<div class="search-box"><h3>📂 Şablon Bulucu</h3>', unsafe_allow_html=True)
        pub = st.selectbox("Yayınevi Seçin", ["Elsevier", "Springer", "IEEE", "Taylor & Francis"])
        urls = {
            "Elsevier": "https://www.elsevier.com/authors/policies-and-guidelines/latex-instructions",
            "Springer": "https://www.springernature.com/gp/authors/campaigns/latex-author-support",
            "IEEE": "https://journals.ieeeauthorcenter.ieee.org/",
            "Taylor & Francis": "https://authorservices.taylorandfrancis.com/"
        }
        st.link_button(f"📥 {pub} Şablonuna Git", urls[pub], use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Referans Dönüştürücü
    with c2:
        st.markdown('<div class="search-box"><h3>📝 Referans Dönüştürücü</h3>', unsafe_allow_html=True)
        ref = st.text_area("Referans Metni", placeholder="Yilmaz, A. (2020)...")
        fmt = st.selectbox("Hedef Format", ["APA 7", "IEEE"])
        if st.button("Formatı Çevir"):
            st.code(convert_reference_style(ref, fmt))
        st.markdown('</div>', unsafe_allow_html=True)

# --- 3. CV OLUŞTURUCU (GERİ GELDİ) ---
elif menu == "📝 CV Oluşturucu":
    st.header("📄 Akademik CV Oluşturucu")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Ad Soyad", "Dr. Ali Yılmaz")
        title = st.selectbox("Unvan", ["Arş. Gör.", "Dr. Öğr. Üyesi", "Doç. Dr.", "Prof. Dr."])
        phone = st.text_input("Telefon")
    with col2:
        inst = st.text_input("Kurum", "Aydın Adnan Menderes Üniversitesi")
        email = st.text_input("E-Posta")
    
    bio = st.text_area("Özet (Summary)")
    edu = st.text_area("Eğitim (Education)")
    pubs = st.text_area("Yayınlar (Publications)")
    
    if st.button("CV PDF İndir"):
        data = {"name": name, "title": title, "institution": inst, "email": email, "phone": phone, "bio": bio, "education": edu, "publications": pubs}
        pdf_bytes = create_academic_cv(data)
        st.download_button("📥 İndir", pdf_bytes, "cv.pdf", "application/pdf")

# --- 4. AI AJANI (GERİ GELDİ) ---
elif menu == "🕵️ AI Ajanı (Beta)":
    st.header("🕵️ Yapay Zeka Tespit Aracı")
    txt = st.text_area("Metni buraya yapıştırın (Maks 3000 karakter)", max_chars=3000)
    if st.button("Analiz Et"):
        with st.spinner("AI Taranıyor..."):
            res = check_ai_probability(txt)
        if res:
            st.metric(label=res['label'], value=f"%{int(res['score']*100)}", delta=res['message'])

# --- 5. GÜVENLİK ---
elif menu == "🛡️ Güvenlik Kontrolü":
    st.header("🛡️ Predatory (Yağmacı) Dergi Kontrolü")
    j_name = st.text_input("Dergi Adını Girin")
    if st.button("Sorgula"):
        if check_predatory(j_name): st.error("⚠️ RİSKLİ DERGİ!")
        else: st.success("✅ Temiz görünüyor.")
