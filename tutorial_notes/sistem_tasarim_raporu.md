# Hava Savunma Sistemi (HSS) Yazılım ve Tasarım Raporu

## 1. Sistemde Yer Alacak Yazılım Bileşenleri

Sistem kurgusunda yer alan temel yazılım, algoritma ve framework bileşenleri aşağıda tanımlanmıştır. 
Kontrol gerekiyo!!!!

### 1.1 Yazılım ve Algoritma Bilgi Tablosu


|BİLEŞENLER|ÜRETİCİ|VERSİYON|ÖZELLİKLERİ|
| :--- | :--- | :--- | :--- |
| **YOLOv8** | Ultralytics | 8.4.21 | Hava hedeflerinin gerçek zamanlı tespiti, sınıflandırılması ve koordinatlarının ROS 2 kanallarına aktarılması.|
| **OpenCV** | OpenCV | 4.11 |Görüntü işleme, bağımsız kamera akışı alma ve sensor_msgs/Image formatında ROS 2 veri yoluna iletme.|
| **PyQt6** | Riverbank Computing | 6.8.1 | Kullanıcı arayüzü sunma ve ROS 2 veri yoluna abone olarak sistem logları ile anlık kamera görüntülerini eşzamanlı gösterme.|
| **micro-ROS** | eProsima | Humble(2.x) | STM32 mikrodenetleyicisini doğrudan ROS 2 veri yoluna bir düğüm olarak bağlamak ve motor komutlarına donanım seviyesinde abone olmak.|
| **AccelStepper** | Mike McCauley | 1.66 | Step motorların STM32 üzerinden ivmeli,yumuşak ve hassas sürüşünü sağlamak.|
| **Çift Eksenli (DualAxis) PID Algoritması** |Özgün Tasarım |- | Görüntü işleme merkezinden alınan piksel hatasını sıfıra indirmek için motor güç çıkışını yani hata payını hesaplamak. |
| **Motor Açı-Piksel Dönüşüm Algoritması** | Özgün Tasarım | -|Kameranın görüş açısı ile pikselleri fiziksel dereceye dönüştürüp, hedefin yönelimini motor adım değerlerine dönüştürmek.|
| **ROS 2 (Robot Operating System)** |Open Robotics|Humble 22.04LTS|Düğümler arası asenkron yayıncı/abone haberleşmesini sağlamak ve alt sistemleri izole ederek hata toleransını artırmak.|




### 1.2 Yazılımların Birbirleriyle Arayüzleri ve İletişim Şeması

- **Görev Yönetim ve Koordinasyon Arayüzü (Mission Control Node)** Sistemin ana karar mekanizması ve orkestratörü olarak çalışan bu merkezi ROS 2 düğümü, alt sistemlerden gelen verileri doğrudan donanıma aktarmak yerine stratejik görev planlamasını ve durum makinası (State Machine) geçişlerini yönetir. Şartnamede belirtilen "yanlış sıradaki hedefin imha edilmesi durumunda 5 ceza puanı" kuralını bertaraf etmek amacıyla gelişmiş bir Hedef Filtreleme ve Doğrulama (Target Discrimination) algoritması koşturur; Tespit Arayüzünden (YOLO) /detection/target_info başlığıyla alınan tüm potansiyel hedef verilerini, operatörün KKS üzerinden girdiği indeks sırasıyla eşleştirerek sadece doğru hedefin koordinatlarını Kontrol Arayüzüne (PID) iletir ve hatalı kilitlenme riskini sıfıra indirir. Buna ek olarak, hedefin anlık olarak görüş alanından çıkması durumunda "Kestirim (Coasting)" modunu tetiklemek gibi otonom senaryoları yönetirken, KKS üzerinden yayınlanan Acil Durdurma (E-Stop) komutlarına sürekli abone olarak, sistemin içinde bulunduğu durum (otonom veya manuel) fark etmeksizin tüm motor tahrik komutlarını anında kesen ve taret donanımını "Güvenli Mod"a (Safe State) alan kesintisiz bir emniyet (fail-safe / interrupt) altyapısı sunar.

- **Görüntü Yakalama Arayüzü (Camera Node)** Bağımsız çalışan kamera düğümü, donanımdan sürekli olarak aldığı ham görüntü karelerini işleyerek /camera/image_raw başlığı altında ağa yayınlar (Publish).

- **Hedef Tespit ve Teşhis Arayüzü (YOLOv8 Node)** Tespit düğümü görüntü başlığına abone olur (Subscribe). Görüntü üzerindeki hava hedeflerini (İHA, Balon vb.) tespit eder ve hedefin merkez koordinatları ile bounding box (sınır kutusu) verilerini /detection/target_info başlığında paylaşır.

- **Hata Hesaplama PID Kontrolcüsü ve Kinematik Hesaplayıcı (PID & Motor Calc Node)** Bu arayüz, tespit edilen hedefin piksel verilerini alarak ekran merkezine göre konum hatasını (X ve Y ekseninde) hesaplar. DualAxis PID Kontrolcüsü ile işlenen bu hata payı, Motor Dönüşüm Hesaplayıcısı tarafından fiziksel yönelim ve adım (step) değerlerine formüle edilir. Elde edilen kesin hareket komutları /control/motor_setpoint başlığına aktarılır.

- **Seri Haberleşme Arayüzü (micro-ROS & ESP32)** Ana kontrolcü (PC) ile ESP32 (motor sürücü anakart) arasındaki haberleşme için en güncel yöntem olan micro-ROS (UART/Seri üzerinden) tercih edilmiştir. ESP32, ağda doğrudan bir ROS 2 düğümü gibi davranarak motor komutlarına abone olur. Ekstra bir metin ayrıştırma (JSON parsing) işlemine gerek kalmadan alınan bu komutlar, donanım seviyesinde AccelStepper kütüphanesi ile işlenerek taretin pürüzsüz ve ivmeli hareketini sağlar.

- **Komuta Kontrol Arayüzü (GUI Node - PyQt6)** PyQt6 tabanlı komuta kontrol arayüzü, sistemdeki ilgili topic'leri dinleyerek operatöre canlı video akışını, hedef kilitlenme durumunu ve motorların anlık açısal verilerini (telemetri) eşzamanlı olarak sunar.


```mermaid
graph TD
    A[Görüntü Kaynağı - OpenCV/PiCamera] -->|Frame/Görüntü Matrisi| B[YOLOv8 Modeli - Ultralytics]
    B -->|Hedef Sınıfı & Bounding Box| C[Ana Karar ve Takip Döngüsü - main.py]
    C -->|Pixel Hatası (Error X, Y)| D[MotorCalculator & PID Controller]
    D -->|Motor Komutu - Pan Step / Tilt PWM| E[SerialCommunicator - PySerial]
    E -->|JSON String UART Sinyali| F[Motor Controller - Arduino]
    F -->|Step/Dir Sinyalleri| G[A4988 Sürücü & NEMA 17 Pan]
    F -->|PWM/Yön Sinyalleri| H[L298N Sürücü & JGY-370 Tilt]
    C <-->|Kamera Akışı, Log, Onay Sinyalleri| I[Çelik Kubbe Arayüzü - PyQt6]
```

### 1.3 Yazılımların Temel Gereksinimleri
* **Asenkron Çalışma:** Arayüzün (GUI) donmaması için kamera yakalama ve nesne tespiti arka planda `QThread` (TrackerWorker) üzerinde yapılmalıdır.
* **Gecikmesiz İletişim (Low-Latency):** USB veya network stream üzerinden alınan görüntü ile motor komutunun gitmesi arasında minimum (gerçek zamanlıya yakın) gecikme olmalıdır. `VideoCapture` tamponu (buffer) en aza (1 frame) indirilmelidir.
* **Aşırı Yük Koruması (Anti-Windup):** Nesne algılanamadığında PID hatasının birikmemesi için integratör limite sahip olmalıdır. PID kontrolcüsünde ölü bölge (deadband) özelliği kullanılarak motorların titremesi engellenmelidir.
* **Güvenlik Mimarisi (Safe Shutdown):** İletişim koptuğunda veya uygulama kapatıldığında, motorların serbest bırakılması (STOP komutu) güvence altına alınmalıdır.

---



A. Veri (Haberleşme) Hatları:

PC (veya Jetson/Raspberry) ile mikrokontrolcü arasındaki UART/USB hattı ve mikrokontrolcüden motor sürücülerine (PUL/DIR pinleri) giden hatlar kesinlikle LIYCY (Ekranlı/Zırhlı) Kablo olmalıdır.

Kablonun dışındaki o hasır metal kılıfı (shield), sistemin sadece tek bir noktasından toprağa (GND) bağlamalısın ki motorların yaydığı manyetik gürültü verini bozmasın.




B. Güç ve Motor Hatları:

Motorlara giden faz kablolarını (A+, A-, B+, B-) kendi içinde birbiri üzerine sarmalısın (Twisted). Bu, manyetik alanı sönümler.
A+ kablosundan ne kadar akım ileri gidiyorsa, A- kablosundan tam olarak aynı miktarda akım geri döner. Yönleri zıt olduğu için ürettikleri manyetik alanların da yönleri zıttır.
Eğer sen A+ ve A- kablolarını alıp bir saç örgüsü gibi sıkıca birbiri etrafında burarsan (bükersen), bu iki zıt manyetik alanı fiziksel olarak tam üst üste bindirmiş olursun. Pozitif manyetik alan ile negatif manyetik alan birbirine çarpar ve dışarıya sızmadan kendi içlerinde birbirlerini sıfırlarlar (sönümlerler).



Hareketli eksenlerde (özellikle Tilt ekseninde yukarı aşağı hareket ederken) standart PVC kablolar zamanla içten kırılır. Bunun yerine AWG 20 veya AWG 22 Silikon Kablo kullanmalısın. Silikon kablolar çok esnektir ve milyonlarca kez bükülmeye dayanır.




C. Konnektör Seçimi (Kesinlikle Jumper Kullanma!):

TEKNOFEST alanında titreşimden dolayı dişi-erkek jumper kabloları yerinden çıkar.

Devre kartında (PCB) JST-XH (klipsli) konnektörler kullan.

Dış kutu bağlantılarında (örneğin taretten ana kontrol kutusuna giden kablolar için) GX16 Havacılık Konnektörleri (Aviation Plug) kullan. Bunlar vidalıdır, asla yerinden oynamaz.



D. Kayar Bilezik (Slip Ring) Kullanımı:

Taretin (Pan ekseni) 360 derece dönecekse, kabloların dolanıp kopmaması ortasından kablo geçen bir döner mafsal olan Slip Ring kullanman mühendislik açısından neredeyse zorunludur.





ros2 dds ile haberleşiyor
sensör kullanılacaksa spı 


1. Donanım Olarak RS-422 Nasıl Bağlanır?
ROS 2 (micro-ROS) verisinin kesintisiz ve eşzamanlı akması için "Tam Çift Yönlü" (Full-Duplex) haberleşmen gerekir. RS-422 tam olarak bunu sağlar. Sistemi kurmak için araya iki küçük dönüştürücü modül ekleyeceksin:

PC (Yer İstasyonu) Tarafı: Bir adet USB to RS-422 Dönüştürücü bilgisayarına takılır. (Üzerinde T+, T-, R+, R- klemensleri/vidaları bulunur).

STM32 (Taret) Tarafı: Bir adet UART TTL to RS-422 Modülü (Genelde MAX490 çipli modüllerdir). STM32'nin TX ve RX pinleri bu modüle girer.

Aradaki Uzun Kablo: Sıradan bir kablo yerine, bir CAT6 (Ethernet) kablosu kullanırsın. CAT6'nın içindeki o sarmal (twisted) yapılar diferansiyel sinyali korumak için yaratılmıştır. PC tarafındaki T+ taret tarafındaki R+'ya, T- ise R-'ye bağlanır.



3. Alt Sistem $\leftrightarrow$ Motor Sürücüleri (STM32 $\leftrightarrow$ TB6600): Step/DirKullanılacak Protokol: Pulse/Direction (Adım/Yön) Sinyallemesi.Neden? Bu tam anlamıyla veri tabanlı bir protokol (I2C gibi) değil, donanımsal bir tetiklemedir. STM32, donanımsal Timer'larını kullanarak mikrosaniye hassasiyetinde PUL (Adım at) ve DIR (Sağa/Sola dön) pinlerine kare dalga (PWM benzeri) gönderir.Kritik Detay: STM32 3.3V mantığıyla çalışır, ancak endüstriyel motor sürücüleri (TB6600 gibi) optokuplörlerini tetiklemek için 5V ister. Araya küçük bir Logic Level Converter (Seviye Dönüştürücü) koyman sistemin hızını ve güvenilirliğini artırır.







---------------------------------------------------------------------------------------

!!!! kart ismini değiştir


Yazılım altyapımız, ROS 2 Humble mimarisi ile düğümler halinde çalışacak şekilde tasarladık. Arayüz şemasında görüldüğü üzere Görüntü Yakalama Arayüzü, ham kamera verisini veri yoluna aktarırken, Hedef Tespit ve Teşhis Modülü, bu veriyi YOLOv8 ile işleyerek hedefin koordinatlarını çıkarır. Görev Yönetim ve Koordinasyon Modülü, durum makinası alogritması ile angajman kurallarını uygular. Hedefin piksel hatası Hata Hesaplama PID Kontrolcüsü ve Kinematik Hesaplayıcı, ile adım komutlarına dönüştürülür. Seri Haberleşme Arayüzü ise STM32 üzerinde micro-ROS ile çalışarak bu komutları motor sürücülerine aktarır. Tüm süreç, PyQt6 tabanlı Komuta Kontrol Arayüzünden anlık izlenip kontrol edilebilir.

Ön tasarım aşamasında sistemin temel performans ve güvenlik gereksinimleri planladık. Dinamik takip yapabilmek için YOLOv8 modelinin en az 30 FPS hızında ve %70 güven eşiğiyle çalışması hedeflenmektedir. Görüntünün işlenip motorlara komut olarak iletilmesi arasındaki uçtan uca haberleşme gecikmesi 10 milisaniyenin altında tutmayı hedefliyoruz. Güvenlik önlemi olarak, arayüzden verilen acil durdurma komutunun donanımı en geç 10 ms içinde tamamen durdurmasını planladık. Ayrıca bağımsız ROS 2 düğüm yapısı sayesinde, olası bir arayüz veya tespit modülü çökmesi durumunda donanım kontrolünün kilitlenmemesi temel mimari kararımızdır.


endüstriyel m12 lens
"ELP Marka, AR0144 Sensörlü, Renkli (RGB) Global Shutter, M12 Lensli USB Kamera Modülü"
https://turkish.alibaba.com/product-detail/ELP-High-Speed-60fps-1280-720-1600331369701.html




















Otonom taret sistemlerinin "gözü" olan kamera seçimi, yazılımın ve donanımın kaderini belirler. Dizüstü bilgisayarda YOLOv8 koşturulacak ve 15 metreye kadar olan hedefler vurulacak bir mimari için piyasadaki 4 ana kamera alternatifini, savunma sanayii standartlarına göre tüm donanım özellikleri, avantaj ve dezavantajlarıyla aşağıda listeledim.

Raporunun "Görsel Algılama Donanımı" bölümüne doğrudan koyabileceğin teknik bir analizdir:

---

### 1. Endüstriyel Makine Görüşü (Machine Vision) Kamerası [Şampiyon Seçenek]

*Bu, senin sistemin için en pragmatik, hedefe en uygun ve endüstri standardı olan seçenektir.*

* **Örnek Modeller:** ELP USB Global Shutter Kamera, Kayeton AR0144 veya OV9281 Sensörlü Metal Kasalı Modüller.
* **Donanım Özellikleri:**
* **Sensör Tipi:** Gerçek **Global Shutter** (Küresel Deklanşör).
* **Lens:** Değiştirilebilir **M12 Mount** (Vidalı lens).
* **Çerçeve Hızı (FPS):** Düşük çözünürlüklerde (Örn: 640x480) saniyede 120 FPS'e kadar çıkabilir.
* **Bağlantı:** Tak-çalıştır USB 2.0 / 3.0 (UVC Destekli).



**Avantajları:**

* **Sıfır Bulanıklık (Motion Blur):** Global Shutter sayesinde taret saniyede 100 derece hızla dönse bile her kare dondurulmuş gibi net çıkar. YOLO asla hedefi kaybetmez.
* **Optik Özelleştirme:** Üzerine 8mm veya 12mm'lik dar açılı bir lens takarak kamerayı adeta bir "keskin nişancı dürbününe" çevirebilirsin. 15 metredeki ufak bir hedef bile ekranda devasa görünür.
* **Mekanik Uyumluluk:** Metal kasalı versiyonları namluya sıfırlamak (boresight) ve sabitlemek için harika vida deliklerine sahiptir. Çok hafiftir, taretin dengesini bozmaz.

**Dezavantajları:**

* **Derinlik (Z Ekseni) Yoktur:** Sadece 2 boyutlu (X,Y) görüntü verir. Hedefin tam uzaklığını bulmak için bounding box (sınır kutusu) piksel boyutundan matematiksel bir kestirim yapman veya sisteme ekstra bir Lazer Mesafe Ölçer (Lidar/ToF) eklemen gerekir.
* **Manuel Odaklama:** Lensi elinle çevirerek (15 metreye göre) odağı bir kere sabitleyip (tercihen Loctite veya bant ile) bırakman gerekir.

---

### 2. RGB-D (Stereo Derinlik) Kameraları [Gelişmiş Seçenek]

*Sisteme "3 Boyutlu" görme yeteneği katan, genellikle otonom araçlarda ve gelişmiş dronelarda kullanılan sistemlerdir.*

* **Örnek Modeller:** Intel RealSense D435i, D455 veya Stereolabs ZED 2i.
* **Donanım Özellikleri:**
* **Sensör Tipi:** Çift kızılötesi (IR) sensör, IR projektör ve standart RGB kamera.
* **Ekstra Donanım:** İçinde genellikle donanımsal **IMU (Jiroskop ve İvmeölçer)** bulunur.
* **Menzil:** Modele göre 10-20 metreye kadar derinlik haritası çıkarabilir.



**Avantajları:**

* **Gerçek Mesafe Ölçümü:** Hedefin tam olarak kaç metre (Örn: 12.4 metre) uzakta olduğunu piksel piksel verir. Şartnamedeki 5-10-15 metre farkını anında donanımsal olarak algılarsın.
* **Dahili IMU:** Taretin anlık titreşimini veya yönelimini doğrudan kameranın içindeki jiroskoptan okuyarak PID algoritmana geri besleme (feedback) yapabilirsin.

**Dezavantajları:**

* **Lens Değişmez (Çok Geniş Açı):** En büyük handikabı budur. Bu kameraların görüş açıları genelde 90 derece civarıdır. 15 metredeki bir İHA veya balon, ekranda o kadar küçülür ki YOLO'nun onu tespit etmesi (güven skoru) çok düşer.
* **Yüksek Veri Yükü ve USB Hassasiyeti:** Derinlik haritası ve RGB'yi aynı anda aktarmak için kusursuz bir **USB 3.0 / 3.2** (Type-C) bağlantısı ister. Kablo uzarsa veya araya dönüştürücü girerse bağlantı anında kopar. Oldukça ağırdır.

---

### 3. Edge AI (Yapay Zeka) Akıllı Kameralar [Otonom Seçenek]

*Görüntü işlemeyi laptopa bırakmadan, kameranın kendi içindeki işlemcide yapan yeni nesil teknolojidir.*

* **Örnek Modeller:** Luxonis OAK-D, OAK-D Pro veya OAK-D Lite.
* **Donanım Özellikleri:**
* **İşlemci:** Dahili Intel Movidius VPU (Görsel İşlem Birimi).
* **Sensör:** 4K RGB kamera + Çift Stereo kamera.



**Avantajları:**

* **Sıfır İşlemci Yükü:** YOLOv8 ağırlıklarını (weights) doğrudan kameranın içine yüklersin. Yerdeki laptopun ekran kartı veya işlemcisi hiç yorulmaz. Kamera bilgisayara sadece hedefin "X, Y, Z koordinatlarını" text verisi olarak gönderir.
* **Kablolama Kolaylığı:** Veri boyutu sadece birkaç kilobayt olduğu için uzun veya düşük kaliteli USB kablolarında bile sistem tıkanmaz.

**Dezavantajları:**

* **Lens Kısıtlaması:** RealSense ile aynı kaderi paylaşır. Dar açılı lens takılamaz, 15 metrelik uzun menzil tespitleri için uygunsuzdur.
* **Yazılım Ekosistemi:** ROS 2 (DepthAI ROS) kurulumu ve YOLO modelini kameranın içine derlemek (OpenVINO formatına çevirmek) oldukça zahmetli bir süreçtir.

---

### 4. Standart Web Kameraları [Uzak Durulması Gereken Seçenek]

*Sadece neyin "yapılmaması" gerektiğini rapora yazmak için bilinmesi gereken sınıftır.*

* **Örnek Modeller:** Logitech C920, C922, Brio 4K.
* **Donanım Özellikleri:** Rolling Shutter sensör, otomatik odaklamalı (Autofocus) plastik/cam lens.

**Dezavantajları:**

* **Rolling Shutter Etkisi:** Taret hedefe kilitlenmek için sağa sola döndüğünde ekrandaki görüntü sağa-sola yatar. Algoritmalar çöker.
* **Kontrolsüz Otomatik Odaklama (Autofocus):** 15 metredeki hedefi ararken, araya giren bir kuş veya sinek yüzünden kamera aniden yakına odaklanır, hedef tamamen bulanıklaşıp ekrandan kaybolur.

---

### Karar Matrisi Özeti

| Kamera Tipi | 15m Optik Başarı (Dar FOV) | Hareket Başarısı | Mesafe (Derinlik) | Maliyet | Sistemin İçin Uygunluk |
| --- | --- | --- | --- | --- | --- |
| **Endüstriyel M12** | **Mükemmel** (Değişen Lens) | **Mükemmel** (Global) | Yazılımsal Kestirim | Uygun | ⭐⭐⭐⭐⭐ (En İyisi) |
| **RGB-D (RealSense)** | Zayıf (Geniş FOV) | İyi (Modele Göre) | **Mükemmel** (Donanım) | Pahalı | ⭐⭐⭐ |
| **OAK-D (Edge AI)** | Zayıf (Geniş FOV) | İyi | **Mükemmel** | Orta-Pahalı | ⭐⭐⭐ |

Yerde güçlü bir laptop kullanarak YOLOv8 çalıştıracağın ve asıl hedefin 15 metre gibi uzak mesafelerde netlik sağlamak olduğu için **Alternatif 1 (Endüstriyel Global Shutter + M12 Dar Açılı Lens)** mimarin için tartışmasız en doğru mühendislik seçimidir.

Şartnamedeki 15 metrelik hedefi ekranda devasa görebilmek için hangi milimetrik değerde (6mm, 8mm veya 12mm) M12 lense ihtiyacın olduğunu matematiksel bir Formül (FOV Hesabı) ile kesinleştirelim mi?







Harika bir detaya takıldın! Bu markalar ve kodlar ilk bakışta sadece rastgele harfler gibi görünür ama aslında donanımın "Zekası" (Sensör) ile "Kıyafeti" (Marka) arasındaki o ince çizgiyi belirlerler.

Jüriye "Biz ELP kamera kullandık" demek yerine, "Sistemimizde ON Semiconductor üretimi AR0144 sensörlü bir endüstriyel modül kullandık" dersen anında profesyonel bir intiba bırakırsın.

Bu karmaşayı senin için iki ana başlıkta (Markalar ve Sensörler) tamamen çözüyorum:

### 1. Marka Farkı: ELP vs. Kayeton

ELP ve Kayeton aslında kameranın "kendi beynini" (sensörünü) üreten firmalar değildir. Bu firmalar **Modül Üreticisi (Toplayıcı)** firmalardır.

* Gidip OmniVision veya ON Semi gibi silikon devlerinden o küçücük sensörü alırlar.
* Kendi tasarladıkları bir elektronik karta (PCB) lehimlerler.
* Üzerine USB haberleşme çipini ve M12 Lens yuvasını ekleyip metal bir kutuya koyarlar.

**Farkları Nedir?**

* **ELP:** Bu piyasanın tartışmasız lideri ve en bilinenidir. Sürücüleri (UVC) Windows ve Linux'ta (ROS 2 ortamında) kusursuz çalışır. Malzeme kalitesi ve metal kasası çok sağlamdır. Türkiye'de (Robotistan vb. yerlerde) veya AliExpress'te kolayca bulunur.
* **Kayeton:** ELP'nin en büyük rakibidir. Birebir aynı kaliteyi sunar, sadece kasalarının şekli veya vida deliklerinin yerleri farklı olabilir. Hangisini ucuz veya stokta bulursan onu alabilirsin, yazılımsal olarak bilgisayar ikisini de aynı şekilde tanır.

---

### 2. Asıl Kritik Fark: AR0144 vs. OV9281 (Sensör Savaşı)

İşte projenin kaderini belirleyecek asıl donanım seçimi burasıdır. Bu kodlar, o metal kasanın içindeki silikon çipin (gözün) ta kendisidir. İkisi de 1 Megapixel (1280x800) çözünürlüğünde ve **Global Shutter** (sıfır bulanıklık) özelliklidir ama aralarında devasa bir fark vardır:

#### OV9281 (OmniVision Üretimi) - Hız Canavarı ama Tehlikeli

* **Hız:** İnanılmaz hızlıdır. Saniyede 120 FPS, hatta çözünürlüğü düşürürsen 210 FPS'e kadar görüntü basabilir.
* **⚠️ En Büyük Tehlike (Renk Tuzağı):** Piyasada satılan OV9281 modüllerinin %90'ı **Monochrome (Siyah-Beyaz)** sensördür! Sadece ışık şiddetini okur, renk verisi yoktur.
* **Taret İçin Anlamı:** Eğer senin YOLOv8 modelin standart veri setleriyle (COCO) eğitildiyse, renkleri göremeyen siyah-beyaz bir kamerada kafası çok karışır ve hedefi bulamayabilir. Ayrıca TEKNOFEST'te hedeflerin renkli olması (kırmızı balon vb.) ayırt edici bir özelliktir. Renksiz görüntü sana yarışmayı kaybettirebilir. (Not: Renkli OV9782 versiyonları da vardır ama bulması zordur).

#### AR0144 (ON Semiconductor Üretimi) - Renk ve Dinamik Aralık Şampiyonu

* **Renk Doğruluğu:** **RGB (Renkli)** sensördür. YOLOv8 bu sensörden gelen görüntülere bayılır, hedefleri şak diye tanır.
* **Dinamik Aralık (WDR - Geniş Dinamik Aralık):** Taret gökyüzüne doğru bakarken arkadan güneş vurduğunda (Ters ışık), OV9281 kör olabilir. Ancak AR0144 ters ışıkta bile hedefi karanlıkta bırakmaz, gölgeleri aydınlatır. Güneşli bir Teknofest gününde hayat kurtarır.
* **Hız:** 1280x800 çözünürlükte saniyede **60 FPS** verir. Bir taret sistemi ve PID döngüsü için 60 FPS fazlasıyla yeterli ve mükemmel bir hızdır.

---

### Senin Sistemin İçin Kesin Karar

Yerdeki güçlü laptopunda YOLOv8 çalıştıracağın ve 15 metredeki hedefleri "renkleri ve şekilleriyle" net tespit etmen gerektiği için:

**Sipariş etmen / Rapora yazman gereken donanım:**

> **"ELP Marka, AR0144 Sensörlü, Renkli (RGB) Global Shutter, M12 Lensli USB Kamera Modülü"**

Bu seçimle hem "Siyah-Beyaz görüntü" tuzağından kurtulmuş olursun hem de güneşe karşı namluyu kaldırdığında hedefin silüet olarak kararmasını (WDR sayesinde) engellersin.

Kameranın kalbini (AR0144) kesin olarak belirledik. Şimdi bu kameranın ucuna takacağın ve 15 metre ilerideki ufacık hedefi senin ekranına kocaman getirecek o sihirli cam parçasını, yani **M12 Lensin odak uzaklığını (Kaç mm olmalı?)** ufak bir matematik hesabı ile netleştirelim mi?