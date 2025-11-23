import streamlit as st
import pandas as pd
import plotly.express as px
from logic import get_journals_from_openalex, check_predatory, check_ai_probability

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="PubScout | Akademik Asistan",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS İLE ÖZELLEŞTİRME (KURUMSAL TASARIM) ---
st.markdown("""
    <style>
    .main { background-color: #F8F9FA; }
    h1 { color: #0F2C59; }
    h2, h3 { color: #0F2C59; }
    .stButton>button {
        background-color: #0F2C59;
        color: white;
        border-radius: 8px;
    }
    .stButton>button:hover {
        background-color: #00DFA2;
        color: #0F2C59;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR (YAN MENÜ) ---
with st.sidebar:
    st.title("🎓 PubScout")
    st.caption("AI Powered Academic Assistant")
    st.markdown("---")
    st.info("🏛️ **Demo University**\n*(Premium License)*")
    
    menu = st.radio(
        "Modüller", 
        [
            "🏠 Ana Sayfa", 
            "🔍 Dergi Bulucu (Core)", 
            "🕵️ AI Ajanı (Beta)", 
            "📊 Yönetici Paneli",
            "🛡️ Güvenlik Kontrolü"
        ]
    )
    
    st.markdown("---")
    st.write("© 2025 PubScout Inc.")

# --- 1. ANA SAYFA ---
if menu == "🏠 Ana Sayfa":
    # Hero Section
    st.markdown("""
    <div style="background-color:#0F2C59; padding:40px; border-radius:15px; text-align:center; color:white;">
        <h1>🚀 Makaleniz İçin En Doğru Evi Bulun</h1>
        <p style="font-size:18px;">Bürokrasiyle değil, bilimle uğraşın. Yapay zeka destekli yayın asistanınız.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("###") # Boşluk
    
    col1, col2, col3 = st.columns(3)
    col1.metric("İndeksli Dergi", "85,000+", "Global")
    col2.metric("Analiz Edilen Makale", "1,204", "+12 bu hafta")
    col3.metric("Engellenen Hata", "450+", "Risk Önleme")
    
    st.image("https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&q=80", caption="Akademik Başarı İçin Teknoloji", use_container_width=True)

# --- 2. DERGİ BULUCU (CORE) ---
elif menu == "🔍 Dergi Bulucu (Core)":
    st.header("🎯 Akıllı Dergi Eşleştirme")
    st.write("Makalenizin özetini (Abstract) yapıştırın, sistem OpenAlex veritabanını tarasın.")
    
    abstract_input = st.text_area("Makale Özeti (Abstract)", height=150, placeholder="Abstract metnini buraya yapıştırın...")
    
    if st.button("Dergileri Analiz Et ve Bul"):
        if len(abstract_input) < 20:
            st.warning("Lütfen daha uzun bir özet girin.")
        else:
            with st.spinner('OpenAlex veritabanı taranıyor, atıf kültürleri analiz ediliyor...'):
                df_results = get_journals_from_openalex(abstract_input)
                
            if df_results is not None and not df_results.empty:
                journal_counts = df_results['Dergi Adı'].value_counts().reset_index()
                journal_counts.columns = ['Dergi Adı', 'Eşleşme Skoru']
                
                st.success(f"Analiz Tamamlandı! {len(journal_counts)} potansiyel dergi bulundu.")
                
                # Kartlar
                col1, col2, col3 = st.columns(3)
                top_journals = journal_counts.head(3)
                
                for index, row in top_journals.iterrows():
                    is_predatory = check_predatory(row['Dergi Adı'])
                    
                    # Veritabanından o derginin detayını bul
                    detail = df_results[df_results['Dergi Adı'] == row['Dergi Adı']].iloc[0]
                    
                    card_color = "#FF4B4B" if is_predatory else "#00CC96"
                    status_text = "⚠️ RİSKLİ / PREDATORY" if is_predatory else "✅ GÜVENLİ"
                    
                    with (col1 if index==0 else col2 if index==1 else col3):
                        st.markdown(f"""
                        <div style="border:1px solid #ddd; padding:15px; border-radius:10px; border-top: 5px solid {card_color}; background:white;">
                            <h4>{row['Dergi Adı']}</h4>
                            <p style="font-size:12px; color:gray;">{detail['Yayınevi']}</p>
                            <p><strong>{status_text}</strong></p>
                            <p>Tahmini Etki: <strong>{detail['Tahmini Q Değeri']}</strong></p>
                        </div>
                        """, unsafe_allow_html=True)
                
                st.write("### 📊 Detaylı Liste")
                st.dataframe(df_results, use_container_width=True)
            else:
                st.error("Eşleşen veri bulunamadı.")

# --- 3. AI AJANI (YENİ ÖZELLİK) ---
elif menu == "🕵️ AI Ajanı (Beta)":
    st.header("🕵️ Yapay Zeka Tespit Aracı (Pre-Check)")
    st.info("Bu modül, makalenizin 'Yapay Zeka' olarak algılanma riskini ölçer.")
    
    ai_text = st.text_area("Metni Yapıştırın (Maks. 3000 Karakter)", height=200, max_chars=3000)
    
    if st.button("AI Taraması Yap"):
        if not ai_text:
            st.error("Metin girilmedi.")
        else:
            with st.spinner("Yapay zeka sinir ağları analiz ediyor..."):
                res = check_ai_probability(ai_text)
            
            if res and isinstance(res, dict):
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.markdown(f"""
                    <div style="text-align:center; padding:20px; border-radius:10px; border: 2px solid {res['color']}; background-color: white;">
                        <h2 style="color:{res['color']}">{res['label']}</h2>
                        <h1 style="font-size: 50px;">%{int(res['score']*100)}</h1>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    st.subheader("Analiz Raporu")
                    st.write(res['message'])
                    st.progress(res['score'], text="Algoritma Güven Seviyesi")
                    if res['label'] == "Yapay Zeka (AI)":
                        st.warning("Öneri: Metni kendi cümlelerinizle yeniden yazın (Paraphrasing).")
            else:
                st.error("Bir hata oluştu: " + str(res))

# --- 4. YÖNETİCİ PANELİ (KÖRFEZ İÇİN) ---
elif menu == "📊 Yönetici Paneli":
    st.header("📈 Kurumsal Performans & Ranking")
    st.info("Bu panel Rektörlük ve Kütüphane Daire Başkanlığı yetkisindedir.")
    
    # Metrikler
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Aylık Yayın", "124", "+12%")
    k2.metric("Hedeflenen Q1", "45", "Yüksek Etki")
    k3.metric("Engellenen Risk", "8", "-8 Hata")
    k4.metric("Tahmini Ranking", "78.4", "+0.5")
    
    st.divider()
    
    # Grafikler
    data_dept = pd.DataFrame({
        'Fakülte': ['Tıp', 'Mühendislik', 'Fen Ed.', 'Eğitim', 'İlahiyat'],
        'Yayın': [45, 30, 25, 15, 10],
        'Etki (IF)': [5.2, 4.1, 2.8, 1.5, 0.9]
    })
    
    c1, c2 = st.columns(2)
    with c1:
        fig1 = px.bar(data_dept, x='Fakülte', y='Yayın', color='Etki (IF)', title="Fakülte Performansı", color_continuous_scale='Bluered')
        st.plotly_chart(fig1, use_container_width=True)
    with c2:
        fig2 = px.pie(values=[35, 45, 20], names=['Q1', 'Q2', 'Q3'], title="Kalite Dağılımı")
        st.plotly_chart(fig2, use_container_width=True)

# --- 5. GÜVENLİK ---
elif menu == "🛡️ Güvenlik Kontrolü":
    st.header("🛡️ Predatory (Yağmacı) Dergi Kontrolü")
    search_journal = st.text_input("Dergi Adı Giriniz:")
    if st.button("Sorgula"):
        if check_predatory(search_journal):
            st.error(f"❌ DİKKAT! '{search_journal}' şüpheli listede görünüyor!")
        else:
            st.success(f"✅ '{search_journal}' temiz görünüyor (Yine de detaylı inceleyiniz).")