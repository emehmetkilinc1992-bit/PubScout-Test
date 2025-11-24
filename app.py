import streamlit as st
import pandas as pd
from logic import (
    get_journals_from_openalex, # Sadece bunu kullanıyoruz, hibrit yok
    check_predatory, 
    check_ai_probability, 
    create_academic_cv, 
    convert_reference_style, 
    analyze_sdg_goals,
    generate_cover_letter, 
    generate_reviewer_response, 
    find_collaborators
)

st.set_page_config(page_title="PubScout", page_icon="🎓", layout="wide")

# CSS
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

with st.sidebar:
    st.title("🎓 PubScout")
    st.info("Kurum: **Demo University**")
    menu = st.radio("Modüller", ["🏠 Ana Sayfa", "🛠️ Yazım Araçları", "🤝 Ortak Bulucu", "📝 CV & Kariyer", "🛡️ Güvenlik & AI"])

# --- ANA SAYFA (AYRI SEKMELİ ARAMA) ---
if menu == "🏠 Ana Sayfa":
    st.markdown("<h1 style='text-align:center;'>PubScout AI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:gray;'>Makale ve Referans Analiz Sistemi</p>", unsafe_allow_html=True)
    
    # SEKMELER (TABS) - KULLANICI İSTEĞİNE GÖRE AYRILDI
    tab_abstract, tab_doi = st.tabs(["📄 ÖZET (Abstract) İLE ARA", "🔗 REFERANS (DOI) İLE ARA"])
    
    # --- SEKME 1: ÖZET ARAMA ---
    with tab_abstract:
        st.markdown('<div class="search-area">', unsafe_allow_html=True)
        st.write("#### 1. Makalenizin Özetini Girin")
        abstract_input = st.text_area("Buraya yapıştırın (Türkçe veya İngilizce)", height=150, placeholder="Bu çalışma yapay zeka ve tıp alanında...")
        
        if st.button("🚀 ÖZETİ ANALİZ ET VE DERGİ BUL"):
            if len(abstract_input) < 10:
                st.warning("Lütfen daha uzun bir özet girin.")
            else:
                with st.spinner('Yapay Zeka konuyu analiz ediyor...'):
                    # Sadece Abstract Modu
                    df_results = get_journals_from_openalex(abstract_input, mode="abstract")
                    sdg_df = analyze_sdg_goals(abstract_input)
                
                if not sdg_df.empty:
                    st.info(f"🌍 **Sürdürülebilirlik Hedefi:** {sdg_df.iloc[0]['Hedef']}")
                
                if not df_results.empty:
                    st.success(f"✅ {len(df_results)} Dergi Bulundu")
                    st.dataframe(df_results, use_container_width=True)
                else:
                    st.error("Sonuç bulunamadı. Lütfen özeti kontrol edin.")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- SEKME 2: DOI ARAMA ---
    with tab_doi:
        st.markdown('<div class="search-area">', unsafe_allow_html=True)
        st.write("#### 2. Referanslarınızın DOI Numaralarını Girin")
        st.info("💡 İpucu: Kaynakçanızdaki 5-10 makalenin DOI numarasını buraya karışık şekilde yapıştırabilirsiniz.")
        
        doi_input = st.text_area("DOI Listesi (Örn: 10.1007/xxxx, https://doi.org/10.1016/yyyy)", height=150)
        
        if st.button("🔗 REFERANSLARI TARA VE DERGİ ÖNER"):
            if "10." not in doi_input:
                st.warning("Lütfen geçerli DOI numaraları girin (İçinde '10.' geçmelidir).")
            else:
                with st.spinner('Referans kültürü ve atıf ağları taranıyor...'):
                    # Sadece DOI Modu
                    df_doi = get_journals_from_openalex(doi_input, mode="doi")
                
                if not df_doi.empty:
                    # Frekans Analizi (Hangi dergi kaç kere geçti?)
                    counts = df_doi['Dergi Adı'].value_counts().reset_index()
                    counts.columns = ['Dergi Adı', 'Referans Sayısı']
                    
                    st.success(f"✅ Referanslarınızdan {len(counts)} farklı dergi tespit edildi.")
                    
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        st.write("🏆 **En Sık Atıf Yapılanlar**")
                        st.dataframe(counts.head(5), use_container_width=True)
                    with c2:
                        st.write("📊 **Detaylı Liste**")
                        st.dataframe(df_doi, use_container_width=True)
                else:
                    st.error("Girilen DOI numaralarından veri çekilemedi.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- DİĞER MODÜLLER (KISALTILDI) ---
elif menu == "🛠️ Yazım Araçları":
    st.header("✍️ Yazım Araçları")
    if st.button("Cover Letter Örneği"): st.code(generate_cover_letter({"title":"AI", "journal":"Nature", "topic":"ML", "author":"Dr. Ali", "institution":"ADU", "reason":"fit", "finding":"good"}))

elif menu == "🤝 Ortak Bulucu":
    st.header("🤝 Ortak Bulucu")
    t = st.text_input("Konu", "deep learning")
    if st.button("Bul"): st.dataframe(find_collaborators(t))

elif menu == "📝 CV & Kariyer":
    st.header("CV")
    if st.button("CV İndir"): st.download_button("İndir", create_academic_cv({"name":"Ali", "title":"Dr.", "institution":"Uni", "email":"a@b.com", "phone":"123", "bio":".", "education":".", "publications":"."}), "cv.pdf")

elif menu == "🛡️ Güvenlik & AI":
    st.header("Güvenlik")
    if st.button("Predatory Kontrol"): st.success("Temiz")
