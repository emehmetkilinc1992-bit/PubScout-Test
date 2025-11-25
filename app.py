# --- YENİ MODÜL: STRATEJİ VE TRENDLER (DÜZELTİLMİŞ) ---
elif menu == "🚀 Strateji ve Trendler":
    st.header("📈 Akademik Trend ve Strateji Analizi")
    st.info("Bu modül, küresel veri tabanlarını tarayarak stratejik raporlar sunar.")
    
    # Konu Girişi
    col_search, col_btn = st.columns([3, 1])
    with col_search:
        topic = st.text_input("Araştırma Konusu (Örn: Artificial Intelligence, Solar Energy)", "Artificial Intelligence")
    with col_btn:
        st.write("###") # Hizalama boşluğu
        btn_trend = st.button("Analiz Et", use_container_width=True)
    
    if btn_trend:
        with st.spinner('Küresel veriler analiz ediliyor...'):
            # 1. Verileri Çek
            df_trends = analyze_trends(topic)
            df_funders = find_funders(topic)
            df_concepts = analyze_concepts(topic)
        
        # --- GRAFİKLER ---
        
        # 1. TREND GRAFİĞİ (ÇİZGİ)
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader(f"📊 '{topic}' Konusunun Yükselişi")
            if not df_trends.empty:
                # Plotly Line Chart
                fig_trend = px.area( # Area chart daha havalı durur
                    df_trends, 
                    x='Yıl', 
                    y='Makale Sayısı', 
                    title="Yıllık Yayın Hacmi",
                    color_discrete_sequence=["#00DFA2"] # Neon Yeşil
                )
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.warning("📉 Bu konuda yeterli trend verisi bulunamadı.")

        # 2. FON SAĞLAYICILAR (TABLO)
        with col2:
            st.subheader("💰 Finansal Destekçiler")
            if not df_funders.empty:
                st.dataframe(
                    df_funders, 
                    hide_index=True, 
                    use_container_width=True,
                    column_config={
                        "Destek Sayısı": st.column_config.ProgressColumn(
                            "Proje Sayısı",
                            format="%d",
                            min_value=0,
                            max_value=df_funders['Destek Sayısı'].max()
                        )
                    }
                )
            else:
                st.info("Bu konu için fon verisi çekilemedi.")
        
        st.divider()
        
        # 3. KAVRAM HARİTASI (TREEMAP - DÜZELTİLDİ)
        st.subheader("🧠 İlişkili Kavram Haritası")
        if not df_concepts.empty:
            # Hiyerarşik Treemap
            fig_tree = px.treemap(
                df_concepts, 
                path=['Ana Kategori', 'Kavram'], # <-- İŞTE SİHİRLİ DOKUNUŞ BURASI
                values='Makale Sayısı',
                color='Alaka Skoru',
                color_continuous_scale='Blues',
                title=f"'{topic}' ile Bağlantılı Alt Dallar"
            )
            st.plotly_chart(fig_tree, use_container_width=True)
        else:
            st.warning("Kavram haritası oluşturulamadı.")
