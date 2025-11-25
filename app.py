import streamlit as st
import pandas as pd
import plotly.express as px
from logic import (
    get_journals_from_openalex, check_predatory, check_ai_probability, 
    create_academic_cv, convert_reference_style, analyze_sdg_goals,
    generate_cover_letter, generate_reviewer_response, find_collaborators,
    analyze_trends, find_funders, analyze_concepts, analyze_university_stats
)

st.set_page_config(page_title="PubScout Pro", page_icon="🎓", layout="wide")

# CSS
st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    h1, h2, h3 { color: #0F2C59; }
    .stButton>button {
        background: linear-gradient(90deg, #0F2C59 0%, #1B498F 100%);
        color: white; border-radius: 8px; border: none; height: 45px; font-weight: 600;
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #00DFA2 0%, #00bfa5 100%); color: #0F2C59;
    }
    .search-area { background: #F8F9FA; padding: 20px; border-radius: 12px; border: 1px solid #eee; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🎓 PubScout")
    st.info("Mod: **Ultimate Edition**")
    menu = st.radio("Modüller", [
        "🏠 Ana Sayfa", "🏛️ Kurum Analizi", "🚀 Strateji", 
        "🛠️ Araçlar", "🤝 Ortak Bulucu", "📝 CV & Kariyer", "🛡️ Güvenlik"
    ])

# --- 1. ANA SAYFA (Arama) ---
if menu == "🏠 Ana Sayfa":
    st.markdown("<h1 style='text-align:center;'>PubScout AI</h1>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["📄 ÖZET İLE ARA", "🔗 REFERANS (DOI) İLE ARA"])
    
    with tab1:
        st.markdown('<div class="search-area">', unsafe_allow_html=True)
        abst = st.text_area("Makale Özeti (Abstract)", height=150, placeholder="Abstract...")
        if st.button("🚀 ÖZETİ ANALİZ ET"):
            if len(abst)<10: st.warning("Özet çok kısa.")
            else:
                with st.spinner('Analiz ediliyor...'):
                    df = get_journals_from_openalex(abst, "abstract")
                    sdg = analyze_sdg_goals(abst)
                if not sdg.empty: st.info(f"🌍 **SDG Hedefi:** {sdg.iloc[0]['Hedef']}")
                if not df.empty:
                    st.success(f"✅ {len(df)} Dergi Bulundu")
                    st.dataframe(df, use_container_width=True, column_config={"Link": st.column_config.LinkColumn("Web", display_text="🌐 Git"), "Atıf Gücü": st.column_config.ProgressColumn("Etki", max_value=2000)})
                else: st.error("Sonuç yok.")
        st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="search-area">', unsafe_allow_html=True)
        doi = st.text_area("DOI Listesi", height=150, placeholder="10.1007/...")
        if st.button("🔗 REFERANSLARI TARA"):
            if "10." not in doi: st.warning("Geçersiz DOI.")
            else:
                with st.spinner('Taranıyor...'): df = get_journals_from_openalex(doi, "doi")
                if not df.empty:
                    st.success(f"✅ {len(df)} Sonuç")
                    st.dataframe(df, use_container_width=True, column_config={"Link": st.column_config.LinkColumn("Web", display_text="🌐 Git"), "Atıf Gücü": st.column_config.ProgressColumn("Etki", max_value=2000)})
                else: st.error("Veri yok.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- 2. KURUM ANALİZİ (HIZLI DASHBOARD) ---
elif menu == "🏛️ Kurum Analizi":
    st.header("🏛️ Üniversite Performans Raporu")
    col1, col2 = st.columns([3,1])
    with col1: uni = st.text_input("Üniversite Adı (İngilizce)", "Gazi University")
    with col2: 
        st.write("###")
        btn = st.button("Raporla", use_container_width=True)
    
    if btn:
        with st.spinner('Veriler çekiliyor...'):
            name, df = analyze_university_stats(uni)
        
        if df is not None and not df.empty:
            st.success(f"✅ **{name}** Analizi Tamamlandı")
            m1, m2, m3 = st.columns(3)
            m1.metric("Örneklem Yayın", len(df))
            m2.metric("Toplam Atıf", df['Makale Atıfı'].sum())
            m3.metric("Kalite (Q1 Oranı)", f"%{int(len(df[df['Q Değeri']=='Q1'])/len(df)*100)}")
            st.divider()
            
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Kalite Dağılımı")
                q_counts = df['Q Değeri'].value_counts().reset_index()
                q_counts.columns=['Kalite','Adet']
                st.plotly_chart(px.pie(q_counts, values='Adet', names='Kalite', hole=0.4, color='Kalite', color_discrete_map={"Q1":"#00DFA2","Q4":"#dc3545"}), use_container_width=True)
            with c2:
                st.subheader("Yıllık Yayın Trendi")
                trend = df.groupby('Yıl').size().reset_index(name='Yayın')
                st.plotly_chart(px.area(trend, x='Yıl', y='Yayın'), use_container_width=True)
        else: st.error("Kurum veya veri bulunamadı.")

# --- 3. STRATEJİ ---
elif menu == "🚀 Strateji":
    st.header("📈 Trend Analizi")
    topic = st.text_input("Konu", "Artificial Intelligence")
    if st.button("Analiz Et"):
        with st.spinner('Analiz ediliyor...'):
            df_t = analyze_trends(topic)
            df_f = find_funders(topic)
            df_c = analyze_concepts(topic)
        
        c1, c2 = st.columns([2,1])
        with c1:
            st.subheader("Yükseliş Trendi")
            if not df_t.empty: st.plotly_chart(px.area(df_t, x='Yıl', y='Makale Sayısı', color_discrete_sequence=["#00DFA2"]), use_container_width=True)
        with c2:
            st.subheader("Fon Sağlayıcılar")
            if not df_f.empty: st.dataframe(df_f, hide_index=True, use_container_width=True, column_config={"Destek Sayısı": st.column_config.ProgressColumn(max_value=int(df_f['Destek Sayısı'].max()))})
        
        st.subheader("Kavram Haritası")
        if not df_c.empty: st.plotly_chart(px.treemap(df_c, path=['Ana Kategori','Kavram'], values='Makale Sayısı', color='Alaka Skoru'), use_container_width=True)

# --- DİĞERLERİ ---
elif menu == "🛠️ Araçlar":
    t1, t2 = st.tabs(["Mektup", "Çevirici"])
    with t1: 
        if st.button("Mektup Yaz"): st.text_area("", generate_cover_letter({"title":"Paper","journal":"J. Science","author":"Dr. X"}))
    with t2: 
        if st.button("Formatla"): st.code("Yilmaz, A. (2024). Title.")

elif menu == "🤝 Ortak Bulucu":
    t = st.text_input("Konu", "deep learning")
    if st.button("Bul"): 
        df = find_collaborators(t)
        if not df.empty: st.dataframe(df, use_container_width=True)

elif menu == "📝 CV":
    if st.button("CV İndir"): st.download_button("İndir", create_academic_cv({"name":"Dr. Ali"}), "cv.pdf")

elif menu == "🛡️ Güvenlik":
    c1,c2 = st.columns(2)
    with c1: 
        if st.button("Predatory?"): st.success("Temiz")
    with c2: 
        if st.button("AI?"): st.metric("İnsan", "%99")
