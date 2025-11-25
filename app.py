import streamlit as st
import pandas as pd
import plotly.express as px
from logic import (
    get_journals_from_openalex, 
    check_predatory, 
    check_ai_probability, 
    create_academic_cv, 
    convert_reference_style, 
    analyze_sdg_goals,
    generate_cover_letter, 
    generate_reviewer_response, 
    find_collaborators,
    analyze_trends,   # YENİ
    find_funders,     # YENİ
    analyze_concepts  # YENİ
)

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="PubScout", page_icon="🎓", layout="wide")

# --- CSS TASARIM ---
st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    h1, h2, h3 { color: #0F2C59; }
    .stButton>button {
        background: linear-gradient(90deg, #0F2C59 0%, #1B498F 100%);
        color: white; border-radius: 8px; border: none; height: 45px;
    }
    .search-area { background: #F8F9FA; padding: 20px; border-radius: 10px; border: 1px solid #eee; margin-bottom: 20px;}
    </style>
""", unsafe_allow_html=True)

# --- YAN MENÜ ---
with st.sidebar:
    st.title("🎓 PubScout")
    st.info("Kurum: **Demo University**")
    
    # MENÜ SIRALAMASI
    menu = st.radio("Modüller", [
        "🏠 Ana Sayfa", 
        "🚀 Strateji ve Trendler", 
        "🛠️ Yazım Araçları", 
        "🤝 Ortak Bulucu", 
        "📝 CV & Kariyer", 
        "🛡️ Güvenlik & AI"
    ])

# --- 1. ANA SAYFA ---
if menu == "🏠 Ana Sayfa":
    st.markdown("<h1 style='text-align:center;'>PubScout AI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:gray;'>Akademik Arama ve Analiz Motoru</p>", unsafe_allow_html=True)
    
    # SEKMELER
    tab_abstract, tab_doi = st.tabs(["📄 ÖZET (Abstract) İLE ARA", "🔗 REFERANS (DOI) İLE ARA"])
    
    # --- SEKME 1: ÖZET ---
    with tab_abstract:
        st.markdown('<div class="search-area">', unsafe_allow_html=True)
        st.write("#### 1. Makalenizin Özetini Girin")
        abstract_input = st.text_area("Buraya yapıştırın (Türkçe veya İngilizce)", height=150, placeholder="Bu çalışma...")
        
        if st.button("🚀 ÖZETİ ANALİZ ET"):
            if len(abstract_input) < 10:
                st.warning("Lütfen daha uzun bir özet girin.")
            else:
                with st.spinner('Analiz yapılıyor...'):
                    df_results = get_journals_from_openalex(abstract_input, mode="abstract")
                    sdg_df = analyze_sdg_goals(abstract_input)
                
                if not sdg_df.empty and sdg_df.iloc[0]['Skor'] > 0:
                    st.info(f"🌍 **Sürdürülebilirlik Hedefi:** {sdg_df.iloc[0]['Hedef']}")
                
                if not df_results.empty:
                    st.success(f"✅ {len(df_results)} Dergi Bulundu")
                    st.dataframe(df_results, use_container_width=True,
                        column_config={
                            "Link": st.column_config.LinkColumn("Web Sitesi", display_text="🌐 Siteye Git"),
                            "Atıf Gücü": st.column_config.ProgressColumn("Atıf", format="%d", min_value=0, max_value=1000)
                        })
                else: st.error("Sonuç bulunamadı.")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- SEKME 2: DOI ---
    with tab_doi:
        st.markdown('<div class="search-area">', unsafe_allow_html=True)
        st.write("#### 2. Referans DOI'lerini Girin")
        doi_input = st.text_area("DOI Listesi", height=150)
        if st.button("🔗 REFERANSLARI TARA"):
            if "10." not in doi_input: st.warning("Geçerli DOI bulunamadı.")
            else:
                with st.spinner('Taranıyor...'):
                    df_doi = get_journals_from_openalex(doi_input, mode="doi")
                if not df_doi.empty:
                    st.success(f"✅ {len(df_doi)} Sonuç")
                    st.dataframe(df_doi, use_container_width=True,
                        column_config={
                            "Link": st.column_config.LinkColumn("Web Sitesi", display_text="🌐 Siteye Git"),
                            "Atıf Gücü": st.column_config.ProgressColumn("Atıf", format="%d", min_value=0, max_value=1000)
                        })
                else: st.error("Veri bulunamadı.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- 2. STRATEJİ VE TRENDLER (YENİ MODÜL) ---
elif menu == "🚀 Strateji ve Trendler":
    st.header("📈 Akademik Trend ve Strateji Analizi")
    st.info("Bu modül, küresel veri tabanlarını tarayarak stratejik raporlar sunar.")
    
    col_search, col_btn = st.columns([3, 1])
    with col_search:
        topic = st.text_input("Araştırma Konusu (Örn: Artificial Intelligence)", "Artificial Intelligence")
    with col_btn:
        st.write("###")
        btn_trend = st.button("Analiz Et", use_container_width=True)
    
    if btn_trend:
        with st.spinner('Küresel veriler analiz ediliyor...'):
            df_trends = analyze_trends(topic)
            df_funders = find_funders(topic)
            df_concepts = analyze_concepts(topic)
        
        # Grafikler
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader(f"📊 '{topic}' Yükseliş Trendi")
            if not df_trends.empty:
                fig_trend = px.area(df_trends, x='Yıl', y='Makale Sayısı', title="Yayın Hacmi", color_discrete_sequence=["#00DFA2"])
                st.plotly_chart(fig_trend, use_container_width=True)
            else: st.warning("Trend verisi yok.")

        with col2:
            st.subheader("💰 Fon Sağlayıcılar")
            if not df_funders.empty:
                st.dataframe(df_funders, hide_index=True, use_container_width=True,
                    column_config={"Destek Sayısı": st.column_config.ProgressColumn("Proje", format="%d", min_value=0, max_value=int(df_funders['Destek Sayısı'].max()))})
            else: st.info("Fon verisi yok.")
        
        st.divider()
        st.subheader("🧠 İlişkili Kavram Haritası")
        if not df_concepts.empty:
            fig_tree = px.treemap(df_concepts, path=['Ana Kategori', 'Kavram'], values='Makale Sayısı', color='Alaka Skoru', title="Alt Dallar")
            st.plotly_chart(fig_tree, use_container_width=True)
        else: st.warning("Harita oluşturulamadı.")

# --- 3. DİĞER MODÜLLER ---
elif menu == "🛠️ Yazım Araçları":
    st.header("✍️ Yazım Araçları")
    t1, t2 = st.tabs(["📝 Cover Letter", "🔄 Çevirici"])
    with t1:
        if st.button("Örnek Mektup"): st.code(generate_cover_letter({"title":"Paper", "journal":"Nature", "topic":"Science", "author":"Dr. X", "institution":"Y"}))
    with t2:
        if st.button("Referans Örneği"): st.code(convert_reference_style("Yilmaz (2023)", "IEEE"))

elif menu == "🤝 Ortak Bulucu":
    st.header("🤝 Ortak Bulucu")
    t = st.text_input("Konu", "deep learning")
    if st.button("Bul"): st.dataframe(find_collaborators(t))

elif menu == "📝 CV & Kariyer":
    st.header("CV")
    if st.button("CV İndir"): st.download_button("İndir", create_academic_cv({"name":"Ali", "title":"Dr.", "institution":"Uni", "email":"a@b.com", "phone":"123", "bio":".", "education":".", "publications":"."}), "cv.pdf")

elif menu == "🛡️ Güvenlik & AI":
    st.header("Güvenlik")
    c1, c2 = st.columns(2)
    with c1: 
        if st.button("Predatory Kontrol"): st.success("Temiz")
    with c2:
        if st.button("AI Kontrol"): st.metric("İnsan", "%98")
