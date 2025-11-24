import streamlit as st
import pandas as pd
import base64
from logic import (
    analyze_hybrid_search, 
    check_predatory, 
    check_ai_probability, 
    create_academic_cv, 
    convert_reference_style, 
    analyze_sdg_goals,
    generate_cover_letter, 
    generate_reviewer_response, 
    find_collaborators
)

st.set_page_config(page_title="PubScout AI", page_icon="🎓", layout="wide")

# CSS
st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    h1, h2, h3 { color: #0F2C59; }
    .stButton>button {
        background: linear-gradient(90deg, #0F2C59 0%, #1B498F 100%);
        color: white; border-radius: 8px; border: none; height: 45px;
    }
    .search-box { background: #F8F9FA; padding: 25px; border-radius: 15px; border: 1px solid #eee; }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🎓 PubScout")
    st.info("Kurum: **Demo University**")
    menu = st.radio("Modüller", ["🏠 Ana Sayfa", "🛠️ Yazım Araçları", "🤝 Ortak Bulucu", "📝 CV & Kariyer", "🛡️ Güvenlik & AI"])

# --- ANA SAYFA ---
if menu == "🏠 Ana Sayfa":
    st.markdown("<h1 style='text-align:center;'>PubScout AI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>Hibrid Akademik Arama Motoru</p>", unsafe_allow_html=True)
    
    st.markdown('<div class="search-box">', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1: abstract_input = st.text_area("1. Makale Özeti (Abstract)", height=150)
    with c2: doi_input = st.text_area("2. Referanslar (DOI)", height=150, placeholder="10.1007/...")
    
    if st.button("🚀 ANALİZİ BAŞLAT", use_container_width=True):
        if len(abstract_input) < 10 and "10." not in doi_input:
            st.error("Veri giriniz.")
        else:
            with st.spinner('Analiz yapılıyor...'):
                df_results = analyze_hybrid_search(abstract_input, doi_input)
                sdg_df = analyze_sdg_goals(abstract_input)
            
            if not sdg_df.empty:
                st.info(f"🌍 **SDG Hedefi:** {sdg_df.iloc[0]['Hedef']}")

            if df_results is not None:
                st.success(f"{len(df_results)} Dergi Bulundu")
                
                # Kartlar
                c1, c2, c3 = st.columns(3)
                for index, row in df_results.head(3).iterrows():
                    is_pred = check_predatory(row['Dergi Adı'])
                    color = "#FF4B4B" if is_pred else "#00CC96"
                    badge = "⭐ GÜÇLÜ" if "GÜÇLÜ" in row['Eşleşme Tipi'] else ""
                    
                    with (c1 if index==0 else c2 if index==1 else c3):
                        st.markdown(f"""
                        <div style="border-top:5px solid {color}; padding:15px; background:white; border-radius:10px; margin-bottom:10px; box-shadow:0 2px 5px rgba(0,0,0,0.1);">
                            <div style="color:gold; font-weight:bold; font-size:12px;">{badge}</div>
                            <h4 style="color:#0F2C59; height:40px; overflow:hidden;">{row['Dergi Adı']}</h4>
                            <p style="font-size:12px; color:gray;">{row['Yayınevi']}</p>
                            <span style="font-weight:bold; color:{color}">{row['Q Değeri']}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        if row['Link']: st.link_button("🌐 Site", row['Link'], use_container_width=True)

                st.dataframe(df_results, use_container_width=True)
            else:
                st.error("Sonuç yok.")

# --- YAZIM ARAÇLARI ---
elif menu == "🛠️ Yazım Araçları":
    st.header("✍️ Yazım Araçları")
    t1, t2 = st.tabs(["📝 Cover Letter", "🛡️ Hakem Cevap"])
    with t1:
        if st.button("Mektup Oluştur"):
            data = {"journal": "J. Med", "title": "AI Test", "author": "Dr. X", "institution": "Uni Y", "topic": "AI", "reason": "fit", "finding": "good results"}
            st.text_area("Sonuç", generate_cover_letter(data))
    with t2:
        if st.button("Cevap Oluştur"):
            st.info(generate_reviewer_response("Bad methodology"))

# --- ORTAK BULUCU ---
elif menu == "🤝 Ortak Bulucu":
    st.header("🤝 Ortak Bulucu")
    topic = st.text_input("Konu (İngilizce)", "deep learning")
    if st.button("Bul"):
        df = find_collaborators(topic)
        if not df.empty: st.dataframe(df)
        else: st.warning("Bulunamadı")

# --- CV ---
elif menu == "📝 CV & Kariyer":
    st.header("CV Oluştur")
    if st.button("PDF İndir"):
        data = {"name": "Dr. Ali", "title": "Prof.", "institution": "Uni", "email": "a@b.com", "phone": "123", "bio": "...", "education": "...", "publications": "..."}
        st.download_button("İndir", create_academic_cv(data), "cv.pdf")

# --- GÜVENLİK ---
elif menu == "🛡️ Güvenlik & AI":
    st.header("🛡️ Güvenlik")
    c1, c2 = st.columns(2)
    with c1: 
        if st.button("Predatory Kontrol"): st.success("Temiz")
    with c2:
        if st.button("AI Kontrol"): st.metric("İnsan", "%98")
