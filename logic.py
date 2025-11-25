# --- MEVCUT KODLARIN ALTINA EKLE ---

# --- YENİ: 8. KURUMSAL ANALİZ (ÜNİVERSİTE YAYINLARI) 🏛️ ---
def analyze_university_pubs(uni_name):
    """
    Üniversite isminden kurum ID'sini bulur ve son yayınlarını çeker.
    Ardından dergi kalitesine (Tahmini Q) göre sınıflandırır.
    """
    base_url = "https://api.openalex.org"
    headers = {'User-Agent': 'mailto:admin@pubscout.com'}
    
    # 1. ADIM: Üniversite ID'sini Bul
    try:
        # Kurum araması yap
        inst_params = {"search": uni_name}
        r_inst = requests.get(f"{base_url}/institutions", params=inst_params, headers=headers)
        inst_data = r_inst.json().get('results', [])
        
        if not inst_data:
            return None, "Kurum bulunamadı."
            
        # En iyi eşleşen kurumu al
        best_match = inst_data[0]
        inst_id = best_match['id'] # Örn: https://openalex.org/I20463608 (Gazi Üniv)
        inst_display_name = best_match['display_name']
        
        # 2. ADIM: Bu Kurumun Son Yayınlarını Çek
        work_params = {
            "filter": f"institutions.id:{inst_id},type:article", # Sadece o kurum ve makaleler
            "sort": "publication_date:desc", # En yeniden eskiye
            "per-page": 100 # Son 100 makale (Demo için yeterli)
        }
        
        r_works = requests.get(f"{base_url}/works", params=work_params, headers=headers)
        works_data = r_works.json().get('results', [])
        
        pub_list = []
        
        # 3. ADIM: Yayınları Analiz Et ve Q Değeri Ata
        for work in works_data:
            if not work.get('primary_location') or not work['primary_location'].get('source'):
                continue
                
            source = work['primary_location']['source']
            journal_name = source.get('display_name', 'Bilinmiyor')
            
            # Derginin Atıf Gücü (Cited by count, o derginin popülerliği)
            # OpenAlex'te 'cited_by_count' makalenin atıfıdır.
            # Derginin kalitesini anlamak için makalenin atıfını ve derginin genel seviyesini kullanırız.
            
            # Basit Q Değeri Simülasyonu (Gerçek veriler ücretlidir)
            # Derginin genel atıf sayısına (works_count vb.) bakarak tahmin ediyoruz.
            
            impact_proxy = source.get('cited_by_count', 0) # Derginin toplam atıfı
            paper_citation = work.get('cited_by_count', 0) # Makalenin kendi atıfı
            
            # Tahmini Sınıflandırma
            if impact_proxy > 50000: q_val = "Q1 (Çok Yüksek)"
            elif impact_proxy > 10000: q_val = "Q2 (Yüksek)"
            elif impact_proxy > 2000: q_val = "Q3 (Orta)"
            else: q_val = "Q4 (Düşük/Yerel)"
            
            pub_list.append({
                "Makale Başlığı": work['title'],
                "Dergi": journal_name,
                "Yayın Yılı": work.get('publication_year'),
                "Makale Atıfı": paper_citation,
                "Kalite Sınıfı": q_val
            })
            
        return pd.DataFrame(pub_list), inst_display_name

    except Exception as e:
        return None, str(e)
