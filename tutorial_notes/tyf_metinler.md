ÖTR raporunun bu bölümü, projenin **"beynini"** kağıda dökmeni ister. Jüri senin kodlarını görmeyecek, bu yüzden sistemi ne kadar mantıklı parçalara ayırdığını ve bu parçaların birbirine nasıl veri aktardığını anlamaya çalışacak.

Burada istenenleri 3 ana adımda, senin projen üzerinden basitleştirerek anlatayım:

### 1. Yazılım Bileşenleri Tanımlama (Tablo Kısmı)

Sisteminde çalışan her farklı "işi" bir yazılım bileşeni olarak düşün. Şablondaki tabloyu doldururken şuna dikkat et: Eğer hazır bir şey (YOLOv8 gibi) kullanıyorsan üretici bilgisini yaz; eğer bir matematiksel formülü (Kalman gibi) kendin kodluyorsan "Özgün Tasarım" de.

**Örnek Tablo Satırları:**

* **Yazılım:** YOLOv8 (Nesne Tespiti) | **Görev:** Görüntüdeki İHA/Balonu bulup kutu içine almak. | **Üretici:** Ultralytics (v8.0) | **Gereksinim:** En az 15 FPS hızında çalışmalı.
* **Yazılım:** Kalman Filtresi | **Görev:** Hedefin titremesini engellemek ve bir sonraki konumunu tahmin etmek. | **Üretici:** Özgün Tasarım | **Gereksinim:** Gecikme süresi 5ms'nin altında olmalı.
* **Yazılım:** PID Kontrolör | **Görev:** Hedef merkezle taret açısı arasındaki farkı kapatmak için motoru sürmek. | **Üretici:** Özgün Tasarım | **Gereksinim:** Aşım (overshoot) yapmadan hedefe kilitlenmeli.

### 2. Arayüz Şeması ve Anlatımı (Interface Diagram)

Burada kastedilen "arayüz", kullanıcı ekranı değil; **yazılımların birbirine hangi veriyi gönderdiğidir.** Bir yazılımın çıktısı, diğerinin girişidir.

**Senin sistemin için veri akışı (Arayüz Mantığı):**

1. **Kamera Modülü**, ham görüntüyü **YOLO Modülü**ne gönderir.
2. **YOLO Modülü**, tespit ettiği koordinatları () **Kalman Filtresi**ne gönderir.
3. **Kalman Filtresi**, pürüzsüzleştirilmiş koordinatı **PID Algoritması**na gönderir.
4. **PID Algoritması**, açı bilgisini **Seri Haberleşme Modülü** üzerinden Arduino'ya gönderir.

### 3. Yazılım Akış Şeması (Flowchart) Nasıl Yapılır?

Bu, sistemin mantıksal bir yol haritasıdır. "Eğer hedef bulunursa şunu yap, bulunmazsa bunu yap" demektir.

**Adım adım akış (Flowchart mantığı):**

* **BAŞLA:** Kamera ve motor bağlantılarını kontrol et.
* **GÖRÜNTÜ AL:** OpenCV ile bir kare yakala.
* **TESPİT ET:** YOLOv8 çalıştır.
* *Soru:* Hedef Var mı?
* *Hayır:* "Arama Modu"na geç (Tareti sağa sola çevir).
* *Evet:* Koordinatları al.


* **FİLTRELE:** Kalman Filtresi ile konumu doğrula.
* **KİLİTLEN:** Hedef merkeze yakın mı?
* *Evet:* "Hedef Kilitlendi" sinyali yak ve PID ile takip et.


* **DÖNGÜYE DÖN.**

### Taktik: Neden "Hazır Mimari" ve "Özgün" Ayrımı Önemli?

Jüri şunu görmek ister: "Bu takım hazır kütüphaneleri (YOLOv8) alıp kullanmayı biliyor ama kendi algoritmalarını da (Kalman, PID) yazabiliyor."

**Özetle yapman gerekenler:**

1. Yazılımlarını (YOLO, Kalman, PID, GUI) bir tabloya dök.
2. Bunların birbirine hangi veriyi (koordinat, açı, hız vb.) aktardığını anlatan bir şema çiz.
3. Sistemin çalışma mantığını gösteren bir akış şeması (Flowchart) ekle.

















Hayır, tam olarak öyle değildir. Bu iki kavram savunma sanayii ve yazılım mühendisliği raporlarında farklı amaçlara hizmet eder. Aralarındaki farkı anlarsan ÖTR'den tam puan alabilirsin.

**Arayüz Şeması (Interface Diagram),** yazılım parçalarının birbirine **"hangi borularla bağlı olduğunu"** gösterir. (Örn: YOLO birimi, "koordinat" verisini Kalman birimine gönderir).

**Yazılım Akış Şeması (Activity/Flowchart) ve Sekans Diyagramı** ise bu verinin **"hangi sırayla ve hangi mantıkla aktığını"** gösterir.

Şartnamede senden istenen 3 ana diyagram türünü senin projen (Çelik Kubbe) üzerinden detaylandıralım:

---

### 1. Aktivite Diyagramı (Activity Diagram / Flowchart)

Bu, sistemin işleyişini adım adım anlatır. Şartname her 3 aşamayı (Tespit, Takip, İmha/Vuruş) ayrı ayrı istemiş:

* **1. Aşama (Arama ve Tespit):** Sistem açılır -> Kamera aktif olur -> Görüntü YOLOv8'e girer -> Hedef bulundu mu? (Hayırsa aramaya devam et, evetse 2. aşamaya geç).
* **2. Aşama (Takip ve Kilit):** Koordinatlar alınır -> Kalman Filtresi ile gürültü temizlenir -> PID ile motor açıları hesaplanır -> Hedef merkezlendi mi? (Evetse kilitlen).
* **3. Aşama (Vuruş/Görev İcrası):** Lazer/Mühimmat tetiklenir -> Vuruş onayı alınır -> Görev sonlandırılır.

---

### 2. Sekans Diyagramı (Sequence Diagram) - *Çok Kritik!*

Sekans diyagramı, **zaman akışını** gösterir. Nesnelerin (Kamera, PC, Kalman, Motorlar) birbirine hangi sırayla mesaj gönderdiğini dikey bir zaman çizelgesinde anlatır.

**Örnek Akış:**

1. **Kamera** -> **PC**: "Görüntü karesini gönderdi"
2. **PC (YOLO)** -> **PC (Kalman)**: "Ham koordinatı iletti"
3. **PC (Kalman)** -> **PC (PID)**: "Tahmin edilen konumu bildirdi"
4. **PC (PID)** -> **Mikrokontrolcü**: "Motoru 5 derece sağa çevir"
5. **Mikrokontrolcü** -> **PC**: "Hareket tamamlandı bilgisi döndü"

---

### 3. Durum Makinası Diyagramı (State Machine Diagram)

Sistemin o an hangi "modda" olduğunu anlatır. Çelik Kubbe için modlar arası geçişleri şöyle kurgulayabilirsin:

* **Bekleme (Idle) Modu:** Sistem hazır, emir bekliyor.
* **Arama (Scanning) Modu:** Hedef yok, taret sağa sola dönüyor.
* **Takip (Tracking) Modu:** Hedef bulundu, kilitlenme sağlandı.
* **Hata (Fail-Safe) Modu:** Bağlantı kesildi, sistem güvenli moda geçti.

---

### Senin İçin Stratejik Taktikler:

1. **Üç Aşamayı Ayır:** Raporunda "Arama, Takip ve İmha" aşamaları için ayrı başlıklar aç. Her biri için küçük birer akış diyagramı koymak, jüriye "şartnameyi tam okudun" mesajı verir.
2. **Sekans Diyagramında Gecikmeye Değin:** "Kameradan verinin gelmesi ile motorun dönmesi arasındaki süre (latency) sekans diyagramında şu şekilde minimize edilmiştir" gibi bir not düşersen 20 puanlık kısımdan tam puan alırsın.
3. **Görsellik:** Bu diyagramları **Draw.io** veya **Visual Paradigm** ile çizmeni öneririm. Elle çizim yapma, profesyonel durmaz.

**Taktik Soru:** Şartnamede geçen "üç aşama" senin projenin hangi kısımlarına denk geliyor? (Örneğin: Balon tespiti mi, İHA takibi mi?) Eğer görevleri netleştirirsek, diyagramdaki kutucukların içine yazacağın teknik ifadeleri birlikte belirleyebiliriz.
















Teknofest gibi savunma sanayii odaklı yarışmalarda, "main" veya "core" gibi yazılımcı jargonu yerine **sistem mühendisliği ve askeri terminolojiye** uygun Türkçe isimler kullanmak rapora büyük bir profesyonellik katar.

`6 main` dosyası senin sisteminde her şeyi birbirine bağlayan, veriyi alıp diğerine ileten "orkestratör" görevi görüyor. Bu modül için kullanabileceğin en havalı ve doğru Türkçe isimler şunlardır:

### En İyi Seçenekler (Rapor İçin)

1. **Görev Yönetim Modülü (Mission Management Module):**
* *Neden iyi?* Savunma sanayiinde ana döngüyü ve karar mekanizmasını çalıştıran yazılımlara "Görev Bilgisayarı Yazılımı" veya "Görev Yönetim Sistemi" denir. Senin "main" dosyan tam olarak bu işi yapıyor.


2. **Merkezi Kontrol ve Koordinasyon Yazılımı:**
* *Neden iyi?* Kameredan gelen veriyi algılama modülüne yollayıp, oradan geleni PID'ye ilettiği için tüm "koordinasyon" işini bu birim yapar.


3. **Ana Yürütme Döngüsü (Main Execution Loop):**
* *Neden iyi?* Daha çok yazılım mimarisi odaklı bir terimdir. Tüm alt modülleri sırayla çağıran (YOLO'yu çalıştır, PID'yi hesapla, GUI'yi güncelle) ana while/for döngüsünü ifade eder.



---

### Bütün Yapının Türkçe "Savunma Sanayii" Karşılıkları

Raporundaki (ÖTR)  arayüz şemasında tüm modüllerin isimlerinin birbiriyle uyumlu ve profesyonel olması için şu Türkçeleştirmeyi kullanmanı tavsiye ederim:

* `1 camera`  **Görüntü Yakalama Arayüzü** (veya Elektro-Optik Sensör Girdisi)
* `2 communication`  **Veri Bağı ve Haberleşme Katmanı**
* `2.1 serial communication`  *Seri Haberleşme (UART) Arayüzü*


* `3 control`  **Karar ve Tahrik Modülü** (Tahrik, motoru hareket ettirmek demektir)
* `3.1 motor calculator`  *Kinematik Hesaplayıcı*
* `3.2 pid controller`  *PID Geri Besleme Kontrolcüsü*


* `4 detection`  **Hedef Tespit ve Teşhis Modülü**
* `4.1 yolo detection`  *Derin Öğrenme Tabanlı Nesne Tespiti (YOLO)*


* `5 firmware`  **Alt Sistem Gömülü Yazılımı**
* `5.1 motor controller.esp`  *Mikrodenetleyici Motor Sürücü Yazılımı (ESP)*


* `6 main`  **Görev Yönetim ve Koordinasyon Modülü**
* `7 gui`  **Komuta Kontrol Arayüzü (KKS)**
* `7.1 pyqt6`  *Kullanıcı Grafik Arayüzü (PyQt6)*



**Taktik:** Arayüz şemasını çizerken ortadaki en büyük kutuya **"Görev Yönetim ve Koordinasyon Modülü (Main)"** yazarsan, hem jürinin aşina olduğu askeri dili kullanmış olursun hem de kodlamadaki karşılığını parantez içinde belirterek mühendislik bağlantısını kurmuş olursun.

Sence ortadaki ana merkeze **"Görev Yönetim Modülü"** ismini verip, draw.io'daki şemanın kutularını bu Türkçe isimlerle doldurmaya başlayalım mı?


















Kesinlikle! `main` dosyanın (veya o döngüyü kurduğun ana dosyanın) kodlarını buraya yapıştırırsan, kodun içindeki fonksiyon çağrılarına ve değişkenlere bakarak sana **tam olarak hangi modülün hangi veriyi alıp verdiğini** madde madde çıkarabilirim. Böylece arayüz şeman (Interface Diagram) doğrudan senin yazdığın kodun birebir yansıması olur ve jüriye karşı tamamen savunulabilir bir teknik altyapı sunarsın.

Peki, bu sürekli bahsettiğimiz **"Modül" tam olarak ne anlama geliyor?**

Savunma sanayiinde ve yazılım mühendisliğinde "Modül", **sadece tek bir işi yapmak üzere tasarlanmış, bağımsız ve tak-çıkar mantığıyla çalışan kod veya donanım parçasıdır.**

Bunu bir fabrikaya veya Lego parçalarına benzetebilirsin:

### 1. Neden Dosyaları Parçalara Ayırıyoruz? (Modüler Mantık)

Eğer tüm kodları (kamerayı açmayı, YOLO'yu çalıştırmayı, PID hesabını ve seri porttan veri göndermeyi) tek bir dosyanın (`main.py`) içine alt alta yazsaydın, buna **"Spagetti Kod"** denirdi. Bir yerde hata çıktığında tüm sistem çökerdi.

Modüler yapıda ise görevler dağıtılır:

* **Kamera Modülü (`camera.py`):** Sadece kamerayı açmayı ve fotoğraf çekmeyi bilir. Motorların varlığından bile haberi yoktur.
* **Tespit Modülü (`yolo.py`):** Sadece kendisine verilen fotoğrafta İHA aramayı bilir. Kamerayı kimin açtığıyla ilgilenmez.
* **Kontrol Modülü (`pid.py`):** Sadece matematiksel hesap yapar. Görüntü işlemeden anlamaz.

### 2. Orkestra Şefi: `Main` Modülü

Senin sistemindeki `main` dosyası, fabrikadaki **Müdür** veya orkestradaki **Şef** gibidir. Kendi başına hiçbir iş yapmaz (kamera açmaz, YOLO eğitmez) ama diğer modülleri yönetir:

1. Kameraya döner: *"Bana bir fotoğraf ver."* (Kamera `frame` döndürür).
2. O fotoğrafı alır, YOLO modülüne uzatır: *"Bunun içinde hedef var mı bul."* (YOLO `X, Y` koordinatı döndürür).
3. O koordinatı alır, PID modülüne uzatır: *"Hedef şu koordinatta, motoru kaç derece döndüreyim hesapla."* (PID açıları döndürür).
4. Açıları alır, Seri Haberleşme modülüne uzatır: *"Bu açıları Arduino'ya gönder."*

### 3. Jürinin Gözünde "Modülerliğin" Değeri Nedir?

Raporda "Sistemimiz modüler bir yazılım mimarisine sahiptir" demek şu anlama gelir:

> *"Yarın öbür gün YOLOv8 yerine daha iyi olan YOLOv11 çıkarsa, sistemin tamamını baştan yazmamıza gerek yoktur. Sadece `detection` modülünü güncelleriz ve sistem çalışmaya devam eder."*

Bu, mühendislikte **sürdürülebilirlik** demektir ve Teknofest projelerinde sana "Yazılım Tasarımı" başlığında ciddi teknik puan kazandırır.

**Hadi başlayalım! `main` dosyanın içindeki kodları (özellikle o ana `while` döngüsünün olduğu kısmı) buraya yapıştır. Ben de o kodlara bakarak, ÖTR raporuna çizeceğin şema için sana "Kim kime hangi veriyi atıyor?" listesini çıkarayım.**