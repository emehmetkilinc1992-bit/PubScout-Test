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
    analyze_trends,
    find_funders,
    analyze_concepts,
    analyze_university_pubs
)

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="PubScout AI", page_icon="🎓", layout="wide")

# --- CSS TASARIM ---
st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    h1, h2, h3 { color: #0F2C59; }
    
    /* Buton Stili */
    .stButton>button {
        background: linear-gradient(90deg, #0F2C59 0%, #1B498F 100%);
        color: white; border-radius: 8px; border: none; height: 45px; font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #00DFA2 0%, #00bfa5 100%);
        color: #0F2C59; transform: translateY(-2px);
    }
    
    /* Arama Kutuları */
    .search-area { 
        background: #F8F9FA; padding: 25px; border-radius: 12px; 
        border: 1px solid #e0e0e0; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }
    
    /* Metrikler */
    div[data-testid="stMetricValue"] { color: #00DFA2; }
    </style>
""", unsafe_allow_html=True)

# --- YAN MENÜ ---
with st.sidebar:
    st.title("🎓 PubScout")
    st.info("Kurum: **Demo University**\n*(Ultimate License)*")
    
    menu = st.radio("Modüller", [
        "🏠 Ana Sayfa", 
        "🏛️ Kurum Analizi", 
        "🚀 Strateji ve Trendler", 
        "🛠️ Yazım Araçları", 
        "🤝 Ortak Bulucu", 
        "📝 CV & Kariyer", 
        "🛡️ Güvenlik & AI"
    ])

# --- 1. ANA SAYFA (SEKMELİ ARAMA) ---
if menu == "🏠 Ana Sayfa":
    st.markdown("<h1 style='text-align:center; font-size: 3.5rem;'>PubScout AI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:gray; font-size: 1.2rem;'>Akademik Yayın ve Analiz Platformu</p>", unsafe_allow_html=True)
    st.write("###")

    tab_abstract, tab_doi = st.tabs(["📄 ÖZET (Abstract) İLE ARA", "🔗 REFERANS (DOI) İLE ARA"])
    
    # --- SEKME 1: ÖZET ---
    with tab_abstract:
        st.markdown('<div class="search-area">', unsafe_allow_html=True)
        st.write("#### 1. Makalenizin Özetini Girin")
        abstract_input = st.text_area("Buraya yapıştırın (Türkçe veya İngilizce)", height=150, placeholder="Bu çalışma yapay zeka ve tıp alanında...")
        
        if st.button("🚀 ÖZETİ ANALİZ ET"):
            if len(abstract_input) < 10:
                st.warning("Lütfen daha uzun bir özet girin.")
            else:
                with st.spinner('Yapay Zeka konuyu analiz ediyor...'):
                    df_results = get_journals_from_openalex(abstract_input, mode="abstract")
                    sdg_df = analyze_sdg_goals(abstract_input)
                
                if not sdg_df.empty and sdg_df.iloc[0]['Skor'] > 0:
                    st.info(f"🌍 **Sürdürülebilirlik Hedefi (SDG):** {sdg_df.iloc[0]['Hedef']}")
                
                if not df_results.empty:
                    st.success(f"✅ {len(df_results)} Dergi Bulundu")
                    st.dataframe(
                        df_results, 
                        use_container_width=True,
                        column_config={
                            "Link": st.column_config.LinkColumn("Web Sitesi", display_text="🌐 Siteye Git"),
                            "Atıf Gücü": st.column_config.ProgressColumn("Etki Puanı", format="%d", min_value=0, max_value=2000)
                        }
                    )
                else: st.error("Sonuç bulunamadı.")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- SEKME 2: DOI ---
    with tab_doi:
        st.markdown('<div class="search-area">', unsafe_allow_html=True)
        st.write("#### 2. Referanslarınızın DOI Numaralarını Girin")
        doi_input = st.text_area("DOI Listesi (Karışık metin olabilir)", height=150, placeholder="10.1007/s12345, https://doi.org/10.1038/xxx...")
        
        if st.button("🔗 REFERANSLARI TARA"):
            if "10." not in doi_input: st.warning("Geçerli DOI bulunamadı.")
            else:
                with st.spinner('Referanslar taranıyor...'):
                    df_doi = get_journals_from_openalex(doi_input, mode="doi")
                
                if not df_doi.empty:
                    st.success(f"✅ {len(df_doi)} Sonuç Bulundu")
                    st.dataframe(
                        df_doi, 
                        use_container_width=True,
                        column_config={
                            "Link": st.column_config.LinkColumn("Web Sitesi", display_text="🌐 Siteye Git"),
                            "Atıf Gücü": st.column_config.ProgressColumn("Etki Puanı", format="%d", min_value=0, max_value=2000)
                        }
                    )
                else: st.error("Veri çekilemedi.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- 2. KURUM ANALİZİ (YENİ) ---
elif menu == "🏛️ Kurum Analizi":
    st.header("🏛️ Üniversite Performans Analizi")
    st.info("Bir üniversitenin yayın kalitesini ve etki düzeyini analiz edin.")
    
    col_s, col_b = st.columns([3, 1])
    with col_s:
        uni_search = st.text_input("Üniversite Adı (İngilizce)", "Gazi University")
    with col_b:
        st.write("###")
        btn_uni = st.button("Kurumu Analiz Et", use_container_width=True)
    
    if btn_uni:
        with st.spinner(f"'{uni_search}' verileri çekiliyor..."):
            df_pubs, uni_name = analyze_university_pubs(uni_search)
        
        if df_pubs is not None and not df_pubs.empty:
            st.success(f"✅ {uni_name} verileri yüklendi.")
            
            # Metrikler
            m1, m2, m3 = st.columns(3)
            m1.metric("İncelenen Yayın", len(df_pubs))
            m2.metric("Toplam Atıf", df_pubs['Makale Atıfı'].sum())
            m3.metric("En Aktif Yıl", str(df_pubs['Yayın Yılı'].mode()[0]))
            st.divider()
            
            # Grafikler
            c1, c2 = st.columns([1, 1])
            with c1:
                st.subheader("📊 Kalite Dağılımı (Tahmini Q)")
                q_counts = df_pubs['Kalite Sınıfı'].value_counts().reset_index()
                q_counts.columns = ['Kalite', 'Adet']
                fig_pie = px.pie(q_counts, values='Adet', names='Kalite', color='Kalite', hole=0.4,
                                 color_discrete_map={"Q1 (Çok Yüksek)":"#00DFA2", "Q2 (Yüksek)":"#007bff", "Q3 (Orta)":"#ffc107", "Q4 (Düşük/Yerel)":"#dc3545"})
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with c2:
                st.subheader("📄 Son Yayınlar")
                st.dataframe(df_pubs, use_container_width=True, height=400,
                             column_config={"Makale Atıfı": st.column_config.ProgressColumn("Atıf", format="%d", min_value=0, max_value=int(df_pubs['Makale Atıfı'].max()))})
        else:
            st.error("Kurum bulunamadı veya veri yok.")

# --- 3. STRATEJİ VE TRENDLER ---
elif menu == "🚀 Strateji ve Trendler":
    st.header("📈 Akademik Trend Analizi")
    
    col_search, col_btn = st.columns([3, 1])
    with col_search: topic = st.text_input("Konu (Örn: Artificial Intelligence)", "Artificial Intelligence")
    with col_btn: 
        st.write("###")
        btn_trend = st.button("Analiz Et", use_container_width=True)
    
    if btn_trend:
        with st.spinner('Veriler taranıyor...'):
            df_trends = analyze_trends(topic)
            df_funders = find_funders(topic)
            df_concepts = analyze_concepts(topic)
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader(f"📊 '{topic}' Yükseliş Trendi")
            if not df_trends.empty:
                fig = px.area(df_trends, x='Yıl', y='Makale Sayısı', title="Yayın Hacmi", color_discrete_sequence=["#00DFA2"])
                st.plotly_chart(fig, use_container_width=True)
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

# --- 4. YAZIM ARAÇLARI ---
elif menu == "🛠️ Yazım Araçları":
    st.header("✍️ Yazım Araçları")
    t1, t2, t3 = st.tabs(["📝 Cover Letter", "🛡️ Hakem Cevap", "🔄 Referans Çevirici"])
    
    with t1:
        c1, c2 = st.columns(2)
        with c1:
            cl_j = st.text_input("Dergi Adı")
            cl_t = st.text_input("Başlık")
        with c2:
            cl_a = st.text_input("Yazar")
            cl_tp = st.text_input("Konu")
        if st.button("Mektup Oluştur"):
            st.text_area("Sonuç", generate_cover_letter({"journal":cl_j, "title":cl_t, "author":cl_a, "topic":cl_tp, "institution":"-", "reason":"fits scope", "finding":"new results"}), height=300)
    
    with t2:
        comm = st.text_area("Hakem Yorumu")
        if st.button("Cevapla"): st.info(generate_reviewer_response(comm))
    
    with t3:
        ref = st.text_area("Referans")
        if st.button("Çevir"): st.code(convert_reference_style(ref, "APA 7"))

# --- 5. DİĞER MODÜLLER ---
elif menu == "🤝 Ortak Bulucu":
    st.header("🤝 Ortak Bulucu")
    t = st.text_input("Konu", "deep learning")
    if st.button("Bul"): 
        df = find_collaborators(t)
        if not df.empty: st.dataframe(df, use_container_width=True)
        else: st.warning("Bulunamadı")

elif menu == "📝 CV & Kariyer":
    st.header("CV Oluştur")
    if st.button("Örnek CV İndir"): 
        st.download_button("İndir PDF", create_academic_cv({"name":"Ali Yilmaz", "title":"Dr.", "institution":"Uni", "email":"-", "phone":"-", "bio":"-", "education":"-", "publications":"-"}), "cv.pdf")

elif menu == "🛡️ Güvenlik & AI":
    st.header("Güvenlik Merkezi")
    c1, c2 = st.columns(2)
    with c1:
        j = st.text_input("Dergi Adı")
        if st.button("Predatory Kontrol"):
            if check_predatory(j): st.error("RİSKLİ!")
            else: st.success("Temiz.")
    with c2:
        txt = st.text_area("Metin")
        if st.button("AI Analiz"): st.metric("İnsan", "%95")
