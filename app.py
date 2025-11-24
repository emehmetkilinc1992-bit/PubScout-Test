import streamlit as st
import pandas as pd
import plotly.express as px
from logic import get_journals_from_openalex, check_predatory, check_ai_probability, create_academic_cv, convert_reference_style

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="PubScout | Akademik Asistan", page_icon="🎓", layout="wide")

# --- TASARIM (CSS) ---
st.markdown("""
    <style>
    .main { background-color: #F8F9FA; }
    h1, h2, h3 { color: #0F2C59; }
    .stButton>button { background-color: #0F2C59; color: white; border-radius: 8px; }
    .stButton>button:hover { background-color: #00DFA2; color: #0F2C59; }
    div[data-testid="stMetricValue"] { color: #00DFA2; }
    </style>
    """, unsafe_allow_html=True)

# --- YAN MENÜ ---
with st.sidebar:
    st.title("🎓 PubScout")
    st.info("Kurum: **Demo University**\n*(Premium License)*")
    menu = st.radio("Modüller", 
        ["🏠 Ana Sayfa", "🛠️ Utility Tools", "📝 CV Oluşturucu", "🕵️ AI Ajanı (Beta)", "📊 Yönetici Paneli", "🛡️ Güvenlik Kontrolü"])

# --- 1. ANA SAYFA (BANNER + DERGİ BULUCU BİR ARADA) ---
if menu == "🏠 Ana Sayfa":
    import base64

    # 1. BANNER AYARLARI
    def get_base64_of_bin_file(bin_file):
        try:
            with open(bin_file, 'rb') as f:
                data = f.read()
            return base64.b64encode(data).decode()
        except FileNotFoundError:
            return None

    img_base64 = get_base64_of_bin_file("banner.jpg")
    
    # Resim varsa onu, yoksa düz rengi kullan
    if img_base64:
        bg_style = f"background-image: url('data:image/jpeg;base64,{img_base64}');"
    else:
        bg_style = "background-color: #0F2C59;"

    # 2. CSS & HTML (Banner Yüksekliğini 550px'den 350px'e düşürdük ki arama kutusu görünsün)
    st.markdown(f"""
    <style>
        .main .block-container {{ padding-top: 0; max-width: 100%; }}
        
        .hero-container {{
            width: 100%;
            height: 350px; /* Daha kısa banner */
            {bg_style}
            background-size: cover;
            background-position: center;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            margin-bottom: 30px;
        }}
        
        .hero-overlay {{
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(15, 44, 89, 0.7);
        }}
        
        .hero-content {{
            position: relative; z-index: 1; text-align: center; color: white;
        }}
        
        .hero-title {{ font-size: 3.5rem; font-weight: 800; margin: 0; text-shadow: 2px 2px 8px rgba(0,0,0,0.6); }}
        .hero-subtitle {{ font-size: 1.2rem; font-weight: 400; opacity: 0.9; }}
    </style>
    
    <div class="hero-container">
        <div class="hero-overlay"></div>
        <div class="hero-content">
            <h1 class="hero-title">PubScout</h1>
            <p class="hero-subtitle">Makaleniz için en doğru evi bulun.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 3. ARAMA MOTORU (ANA SAYFAYA TAŞINDI)
    st.markdown("<h3 style='text-align:center; color:#0F2C59;'>🔎 Aramaya Başlayın</h3>", unsafe_allow_html=True)
    
    # Konteyner ile ortalayalım
    col_spacer1, col_main, col_spacer2 = st.columns([1, 6, 1])
    
    with col_main:
        # Sekmeli Yapı
        tab1, tab2 = st.tabs(["📄 Özet (Abstract) ile Ara", "🔗 Referans (DOI) ile Ara"])
        
        # --- TAB 1: ÖZET ARAMA ---
        with tab1:
            abstract_input = st.text_area("Makale Özeti (Türkçe veya İngilizce)", height=150, placeholder="Abstract metnini buraya yapıştırın...")
            
            # Butonu ortalamak için kolon kullanalım
            b_c1, b_c2, b_c3 = st.columns([1, 2, 1])
            with b_c2:
                search_clicked = st.button("🚀 Dergileri Bul", use_container_width=True)

        # --- TAB 2: DOI ARAMA ---
        with tab2:
            doi_input = st.text_area("DOI Listesi (Virgülle ayırın)", height=150, placeholder="10.1007/xxxx, 10.1016/yyyy...")
            d_c1, d_c2, d_c3 = st.columns([1, 2, 1])
            with d_c2:
                doi_clicked = st.button("🔗 Referanslardan Bul", use_container_width=True)

    # 4. SONUÇLARIN GÖSTERİMİ
    # Kullanıcı butona bastıysa sonuçları göster, basmadıysa alttaki metrikleri göster.
    
    if search_clicked and abstract_input:
        if len(abstract_input) < 20:
            st.warning("Lütfen daha uzun bir metin girin.")
        else:
            with st.spinner('Yapay Zeka Analiz Ediyor...'):
                df = get_journals_from_openalex(abstract_input, mode="abstract")
            
            if not df.empty:
                journal_counts = df['Dergi Adı'].value_counts().reset_index()
                journal_counts.columns = ['Dergi Adı', 'Skor']
                st.success(f"Analiz Tamamlandı! {len(journal_counts)} uygun dergi bulundu.")
                
                # Kartlar (Card Design)
                c1, c2, c3 = st.columns(3)
                top_journals = journal_counts.head(3)
                
                for index, row in top_journals.iterrows():
                    is_predatory = check_predatory(row['Dergi Adı'])
                    detail = df[df['Dergi Adı'] == row['Dergi Adı']].iloc[0]
                    card_color = "#FF4B4B" if is_predatory else "#00CC96"
                    status_text = "⚠️ RİSKLİ" if is_predatory else "✅ GÜVENLİ"
                    
                    homepage = detail.get('Link')
                    guidelines = f"https://www.google.com/search?q={row['Dergi Adı'].replace(' ', '+')}+author+guidelines"
                    
                    with (c1 if index==0 else c2 if index==1 else c3):
                        st.markdown(f"""
                        <div style="background:white; border-radius:12px; padding:20px; border-top:5px solid {card_color}; box-shadow:0 4px 12px rgba(0,0,0,0.1);">
                            <h4 style="color:#0F2C59; height:40px; overflow:hidden;">{row['Dergi Adı']}</h4>
                            <p style="font-size:12px; color:gray;">{detail['Yayınevi']}</p>
                            <p><strong>{status_text}</strong></p>
                            <p>Etki: <strong>{detail['Tahmini Q Değeri']}</strong></p>
                        </div>
                        """, unsafe_allow_html=True)
                        st.write("###")
                        bc1, bc2 = st.columns(2)
                        with bc1:
                            if homepage: st.link_button("🌐 Site", homepage, use_container_width=True)
                            else: st.button("🚫", disabled=True, use_container_width=True)
                        with bc2:
                            st.link_button("📝 Rehber", guidelines, use_container_width=True)
                
                st.write("### 📊 Tüm Liste")
                st.dataframe(df, use_container_width=True)
            else:
                st.error("Sonuç bulunamadı.")

    elif doi_clicked and doi_input:
        # (DOI Arama Kodları Buraya - Aynısı)
        with st.spinner('Referanslar taranıyor...'):
            df_doi = get_journals_from_openalex(doi_input, mode="doi")
        if not df_doi.empty:
            st.success("Referans kültürü analiz edildi!")
            st.dataframe(df_doi, use_container_width=True)
        else:
            st.error("Veri bulunamadı.")

    # 5. İSTATİSTİKLER (Sadece Arama Yapılmadıysa Göster - Ekranı Temiz Tutmak İçin)
    elif not search_clicked and not doi_clicked:
        st.write("###")
        st.write("###")
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("📚 İndeksli Dergi", "85,000+")
        m2.metric("🤖 AI Analizi", "Semantik")
        m3.metric("🛡️ Güvenlik", "%100")

# --- 2. DERGİ BULUCU (CORE) ---
elif menu == "🔍 Dergi Bulucu (Core)":
    st.header("🎯 Akıllı Dergi Eşleştirme")
    tab1, tab2 = st.tabs(["📄 Özet (Abstract) ile Ara", "🔗 Referans (DOI) ile Ara"])
    
    # --- Özet Modu ---
    with tab1:
        abstract_input = st.text_area("Makale Özeti (Türkçe veya İngilizce)", height=150)
        if st.button("Dergileri Bul"):
            if len(abstract_input) < 20:
                st.warning("Lütfen daha uzun bir metin girin.")
            else:
                with st.spinner('Çeviri yapılıyor ve veritabanı taranıyor...'):
                    df = get_journals_from_openalex(abstract_input, mode="abstract")
                
                if not df.empty:
                    # Dergi Sayacı (Hangi dergi kaç kez önerildi?)
                    journal_counts = df['Dergi Adı'].value_counts().reset_index()
                    journal_counts.columns = ['Dergi Adı', 'Skor']
                    
                    st.success(f"{len(journal_counts)} potansiyel dergi bulundu!")
                    
                    # Kart Görünümü
                    col1, col2, col3 = st.columns(3)
                    top_journals = journal_counts.head(3)
                    
                    for index, row in top_journals.iterrows():
                        is_predatory = check_predatory(row['Dergi Adı'])
                        detail = df[df['Dergi Adı'] == row['Dergi Adı']].iloc[0]
                        
                        card_color = "#FF4B4B" if is_predatory else "#00CC96"
                        status_text = "⚠️ RİSKLİ" if is_predatory else "✅ GÜVENLİ"
                        
                        # Linkler
                        homepage = detail.get('Link')
                        guidelines_url = f"https://www.google.com/search?q={row['Dergi Adı'].replace(' ', '+')}+author+guidelines"
                        
                        with (col1 if index==0 else col2 if index==1 else col3):
                            st.markdown(f"""
                            <div style="border:1px solid #ddd; padding:15px; border-radius:10px; border-top: 5px solid {card_color}; background:white; height:100%;">
                                <h4 style="color:#0F2C59; height:50px; overflow:hidden;">{row['Dergi Adı']}</h4>
                                <p style="font-size:12px; color:gray;">{detail['Yayınevi']}</p>
                                <p><strong>{status_text}</strong></p>
                                <p>Etki: <strong>{detail['Tahmini Q Değeri']}</strong></p>
                            </div>
                            """, unsafe_allow_html=True)
                            st.write("###")
                            b1, b2 = st.columns(2)
                            with b1:
                                if homepage: st.link_button("🌐 Site", homepage, use_container_width=True)
                                else: st.button("🌐 Yok", disabled=True, use_container_width=True)
                            with b2:
                                st.link_button("📝 Rehber", guidelines_url, use_container_width=True)

                    st.write("### 📊 Tüm Sonuçlar")
                    st.dataframe(df, use_container_width=True)
                else:
                    st.error("Sonuç bulunamadı.")

    # --- DOI Modu ---
    with tab2:
        st.info("Kaynakçanızdaki DOI'leri virgülle ayırarak girin.")
        doi_input = st.text_area("DOI Listesi", height=150)
        if st.button("Referanslardan Öner"):
            if "10." in doi_input:
                with st.spinner('Analiz ediliyor...'):
                    df_doi = get_journals_from_openalex(doi_input, mode="doi")
                if not df_doi.empty:
                    st.success("Referans kültürü analiz edildi!")
                    st.dataframe(df_doi, use_container_width=True)
                else:
                    st.error("Veri çekilemedi.")
            else:
                st.warning("Geçerli DOI bulunamadı.")

# --- 3. UTILITY TOOLS ---
elif menu == "🛠️ Utility Tools":
    st.header("🛠️ Araçlar")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📂 Şablon Bulucu")
        pub = st.selectbox("Yayınevi", ["Elsevier", "Springer", "IEEE", "Taylor & Francis"])
        urls = {
            "Elsevier": "https://www.elsevier.com/authors/policies-and-guidelines/latex-instructions",
            "Springer": "https://www.springernature.com/gp/authors/campaigns/latex-author-support",
            "IEEE": "https://journals.ieeeauthorcenter.ieee.org/",
            "Taylor & Francis": "https://authorservices.taylorandfrancis.com/"
        }
        st.link_button(f"{pub} Şablon Sayfasına Git", urls[pub])
    with c2:
        st.subheader("📝 Referans Dönüştürücü (Beta)")
        ref = st.text_area("Referans Metni")
        fmt = st.selectbox("Hedef Format", ["APA 7", "IEEE"])
        if st.button("Çevir"):
            st.code(convert_reference_style(ref, fmt))

# --- 4. CV OLUŞTURUCU ---
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
    
    if st.button("CV İndir (PDF)"):
        data = {"name": name, "title": title, "institution": inst, "email": email, "phone": phone, "bio": bio, "education": edu, "publications": pubs}
        pdf_bytes = create_academic_cv(data)
        st.download_button("📥 PDF İndir", pdf_bytes, "cv.pdf", "application/pdf")

# --- 5. AI AJANI ---
elif menu == "🕵️ AI Ajanı (Beta)":
    st.header("🕵️ Yapay Zeka Tespit Aracı")
    txt = st.text_area("Metni buraya yapıştırın (Maks 3000 karakter)", max_chars=3000)
    if st.button("Analiz Et"):
        with st.spinner("AI Taranıyor..."):
            res = check_ai_probability(txt)
        if res:
            st.metric(label=res['label'], value=f"%{int(res['score']*100)}", delta=res['message'])

# --- 6. YÖNETİCİ PANELİ ---
elif menu == "📊 Yönetici Paneli":
    st.header("📈 Yönetici & Ranking Paneli")
    k1, k2, k3 = st.columns(3)
    k1.metric("Aylık Yayın", "124", "+12%")
    k2.metric("Hedef Q1", "45")
    k3.metric("Tahmini Ranking", "78.4")
    
    df_chart = pd.DataFrame({'Fakülte': ['Tıp', 'Müh', 'Fen'], 'Yayın': [45, 30, 20]})
    st.plotly_chart(px.bar(df_chart, x='Fakülte', y='Yayın', title="Bölüm Performansı"))

# --- 7. GÜVENLİK ---
elif menu == "🛡️ Güvenlik Kontrolü":
    st.header("🛡️ Predatory Kontrol")
    j_name = st.text_input("Dergi Adı")
    if st.button("Sorgula"):
        if check_predatory(j_name): st.error("⚠️ RİSKLİ DERGİ!")
        else: st.success("✅ Temiz görünüyor.")





