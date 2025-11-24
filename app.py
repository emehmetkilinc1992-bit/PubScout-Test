import streamlit as st
import pandas as pd
import base64
from logic import analyze_hybrid_search, check_predatory, check_ai_probability, create_academic_cv, convert_reference_style

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="PubScout | Hibrid Arama", page_icon="🎓", layout="wide")

# --- CSS (Minimalist & Clean) ---
st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    h1, h2, h3 { color: #0F2C59; }
    
    /* Arama Paneli Kutusu */
    .search-box {
        background-color: #F8F9FA;
        padding: 30px;
        border-radius: 15px;
        border: 1px solid #eee;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
    }
    
    /* Buton */
    .stButton>button {
        background: linear-gradient(90deg, #0F2C59 0%, #0056b3 100%);
        color: white;
        height: 50px;
        font-size: 18px;
        border-radius: 10px;
        border: none;
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #00DFA2 0%, #00bfa5 100%);
        color: #0F2C59;
    }
    </style>
""", unsafe_allow_html=True)

# --- MENÜ ---
with st.sidebar:
    st.title("🎓 PubScout")
    st.info("Mod: **Hybrid Search Engine**")
    menu = st.radio("Menü", ["🏠 Ana Sayfa", "🛠️ Araçlar", "📝 CV", "🕵️ AI Dedektör"])

# --- ANA SAYFA (HİBRİD ARAMA) ---
if menu == "🏠 Ana Sayfa":
    
    # Başlık
    st.markdown("<h1 style='text-align:center; margin-bottom:10px;'>PubScout AI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:gray;'>Özet (Abstract) ve Referanslarınızı (DOI) birlikte analiz ederek en doğru dergiyi bulur.</p>", unsafe_allow_html=True)
    st.write("###")

    # --- TEK ARAMA PANELİ ---
    st.markdown('<div class="search-box">', unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("1. Makale Özeti (Konu)")
        abstract_input = st.text_area("Özetinizi buraya yapıştırın", height=200, placeholder="Abstract...")
    
    with c2:
        st.subheader("2. Referanslar (Kültür)")
        doi_input = st.text_area("DOI Listesi (Opsiyonel ama önerilir)", height=200, placeholder="10.1007/xxxx, 10.1016/yyyy (Virgülle ayırın)...")
    
    st.write("###")
    analyze_btn = st.button("🚀 HİBRİD ANALİZİ BAŞLAT", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # --- ANALİZ SONUÇLARI ---
    if analyze_btn:
        if len(abstract_input) < 20 and "10." not in doi_input:
            st.error("Lütfen en az bir alanı (Özet veya DOI) geçerli şekilde doldurun.")
        else:
            with st.spinner('Yapay Zeka konu ve atıf ağlarını çapraz analiz ediyor...'):
                df_results = analyze_hybrid_search(abstract_input, doi_input)
            
            if df_results is not None and not df_results.empty:
                st.write("###")
                st.success(f"✅ Analiz Tamamlandı! {len(df_results)} dergi bulundu.")
                st.divider()

                # SONUÇ KARTLARI
                col1, col2, col3 = st.columns(3)
                
                # En iyi 3 sonucu göster
                for index, row in df_results.head(3).iterrows():
                    is_predatory = check_predatory(row['Dergi Adı'])
                    card_color = "#FF4B4B" if is_predatory else "#00CC96"
                    status_text = "⚠️ RİSKLİ" if is_predatory else "✅ GÜVENLİ"
                    
                    # Güçlü Eşleşme Rozeti
                    badge = ""
                    if "GÜÇLÜ" in row['Eşleşme Tipi']:
                        badge = "<div style='background:#FFD700; color:#000; padding:5px; border-radius:5px; font-size:11px; font-weight:bold; margin-bottom:5px; text-align:center;'>⭐ GÜÇLÜ EŞLEŞME (Konu + Atıf)</div>"
                    
                    google_link = f"https://www.google.com/search?q={row['Dergi Adı'].replace(' ', '+')}+author+guidelines"

                    with (col1 if index==0 else col2 if index==1 else col3):
                        st.markdown(f"""
                        <div style="background:white; border:1px solid #ddd; padding:20px; border-radius:15px; border-top:5px solid {card_color}; height:100%;">
                            {badge}
                            <h4 style="color:#0F2C59; height:50px; overflow:hidden;">{row['Dergi Adı']}</h4>
                            <p style="color:gray; font-size:12px;">{row['Yayınevi']}</p>
                            <div style="display:flex; justify-content:space-between; margin-top:10px;">
                                <span style="font-weight:bold; color:{card_color}">{status_text}</span>
                                <span style="background:#eee; padding:2px 8px; border-radius:4px;">{row['Q Değeri']}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.write("#")
                        l1, l2 = st.columns(2)
                        with l1:
                            if row['Link']: st.link_button("🌐 Site", row['Link'], use_container_width=True)
                            else: st.button("🚫", disabled=True, use_container_width=True)
                        with l2:
                            st.link_button("📝 Rehber", google_link, use_container_width=True)

                st.write("### 📊 Detaylı Sıralama")
                st.dataframe(df_results[['Dergi Adı', 'Yayınevi', 'Q Değeri', 'Eşleşme Tipi', 'Skor']], use_container_width=True)

            else:
                st.error("Üzgünüz, eşleşen dergi bulunamadı.")

# --- DİĞER SAYFALAR (Aynı kalıyor, yer tutucu) ---
elif menu == "🛠️ Araçlar":
    st.header("🛠️ Araçlar")
    # (Eski Utility Tools kodlarını buraya yapıştırabilirsin)
    
elif menu == "📝 CV":
    st.header("CV Oluşturucu")
    # (Eski CV kodları)

elif menu == "🕵️ AI Dedektör":
    st.header("AI Dedektör")
    # (Eski AI kodları)
