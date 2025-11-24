import streamlit as st
import pandas as pd
import plotly.express as px
from logic import (
    analyze_hybrid_search, check_predatory, check_ai_probability, 
    create_academic_cv, convert_reference_style, analyze_sdg_goals,
    generate_cover_letter, generate_reviewer_response, find_collaborators
)

st.set_page_config(page_title="PubScout Pro", page_icon="🎓", layout="wide")

# CSS TASARIM
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
    st.caption("v2.1 Ultimate Edition")
    st.info("Kurum: **Demo University**")
    menu = st.radio("Modüller", ["🏠 Ana Sayfa", "🛠️ Yazım Araçları (Tools)", "🤝 Ortak Bulucu (Network)", "📝 CV & Kariyer", "🛡️ Güvenlik & AI"])

# --- 1. ANA SAYFA (HİBRİD ARAMA + SDG ANALİZİ) ---
if menu == "🏠 Ana Sayfa":
    st.markdown("<h1 style='text-align:center;'>PubScout AI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>Makale, Dergi ve Etki Analizi Platformu</p>", unsafe_allow_html=True)
    
    st.markdown('<div class="search-box">', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        abstract_input = st.text_area("1. Makale Özeti (Abstract)", height=150)
    with c2:
        doi_input = st.text_area("2. Referanslar (DOI)", height=150, placeholder="10.1007/...")
    
    btn = st.button("🚀 ANALİZİ BAŞLAT", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if btn:
        if len(abstract_input) < 20 and "10." not in doi_input:
            st.error("Lütfen veri giriniz.")
        else:
            # 1. DERGİ SONUÇLARI
            with st.spinner('Dergiler ve SDG hedefleri analiz ediliyor...'):
                df_results = analyze_hybrid_search(abstract_input, doi_input)
                sdg_df = analyze_sdg_goals(abstract_input) # SDG Analizi
            
            # SDG Raporu (Yönetici Özelliği)
            if not sdg_df.empty:
                st.info(f"🌍 **SDG Etkisi:** Bu makale en çok **{sdg_df.iloc[0]['Hedef']}** hedefine katkı sağlıyor.")

            if df_results is not None:
                st.success(f"{len(df_results)} Dergi Bulundu")
                st.dataframe(df_results, use_container_width=True)
            else:
                st.error("Dergi bulunamadı.")

# --- 2. YAZIM ARAÇLARI (COVER LETTER & HAKEM) ---
elif menu == "🛠️ Yazım Araçları (Tools)":
    st.header("✍️ Editör ve Hakem İletişimi")
    t1, t2, t3 = st.tabs(["📝 Cover Letter (Ön Yazı)", "🛡️ Hakem Cevaplayıcı", "🔄 Referans Çevirici"])
    
    with t1:
        st.subheader("Editöre Mektup Oluştur")
        c1, c2 = st.columns(2)
        with c1:
            cl_j = st.text_input("Dergi Adı")
            cl_t = st.text_input("Makale Başlığı")
            cl_topic = st.text_input("Konu (Kısaca)")
        with c2:
            cl_auth = st.text_input("Yazar Adı")
            cl_inst = st.text_input("Kurum")
            cl_res = st.text_input("Neden bu dergi?", value="it fits the scope")
            cl_find = st.text_input("Ana Bulgu", value="we achieved state-of-the-art results")
        
        if st.button("Mektubu Yaz"):
            data = {"journal": cl_j, "title": cl_t, "author": cl_auth, "institution": cl_inst, "topic": cl_topic, "reason": cl_res, "finding": cl_find}
            st.text_area("Sonuç:", generate_cover_letter(data), height=300)

    with t2:
        st.subheader("Hakem Yorumuna Cevap")
        comment = st.text_area("Hakemin eleştirisini yapıştırın:")
        tone = st.selectbox("Üslup Seçin", ["Polite (Kibar)", "Rebuttal (İtiraz)"])
        if st.button("Cevabı Oluştur"):
            st.info(generate_reviewer_response(comment, tone))

    with t3:
        st.subheader("Referans Formatla")
        r_txt = st.text_area("Referans")
        fmt = st.selectbox("Format", ["APA 7", "IEEE"])
        if st.button("Çevir"):
            st.code(convert_reference_style(r_txt, fmt))

# --- 3. ORTAK BULUCU (YENİ KATİL ÖZELLİK) ---
elif menu == "🤝 Ortak Bulucu (Network)":
    st.header("🤝 Global İşbirliği (Co-Author) Bulucu")
    st.write("Çalıştığınız konuyu girin, dünyada bu konuda en çok atıf alan uzmanları bulun.")
    
    topic = st.text_input("Araştırma Konusu (İngilizce)", placeholder="deep learning in radiology")
    if st.button("Uzmanları Bul"):
        with st.spinner("OpenAlex veritabanında uzmanlar taranıyor..."):
            df_collab = find_collaborators(topic)
        
        if not df_collab.empty:
            st.success("Potansiyel İşbirlikleri Bulundu!")
            for i, row in df_collab.iterrows():
                st.markdown(f"""
                <div style="padding:15px; border:1px solid #ddd; border-radius:10px; margin-bottom:10px;">
                    <h4>👤 {row['Yazar']}</h4>
                    <p>🏛️ {row['Kurum']}</p>
                    <p>📄 Örnek Makale: <i>{row['Makale']}</i></p>
                    <p>⭐ Toplam Atıf: <strong>{row['Atıf']}</strong></p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("Sonuç bulunamadı.")

# --- 4. CV ---
elif menu == "📝 CV & Kariyer":
    st.header("CV Oluşturucu")
    st.info("Kodun uzunluğunu artırmamak için burayı kısa tuttum, önceki CV kodu buraya entegre edilebilir.")

# --- 5. GÜVENLİK ---
elif menu == "🛡️ Güvenlik & AI":
    st.header("🛡️ Güvenlik Merkezi")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Predatory Kontrol")
        j = st.text_input("Dergi Adı")
        if st.button("Kontrol Et"):
            if check_predatory(j): st.error("RİSKLİ!")
            else: st.success("Temiz.")
    with col2:
        st.subheader("AI Dedektör")
        txt = st.text_area("Metin", max_chars=3000)
        if st.button("Tara"):
            res = check_ai_probability(txt)
            if res: st.metric(res['label'], f"%{int(res['score']*100)}")
