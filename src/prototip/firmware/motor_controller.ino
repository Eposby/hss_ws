/*
 * Pan-Tilt Hibrit Motor Kontrolcüsü
 * Pan: Step Motor (NEMA 17 + A4988/DRV8825)
 A4988 ve DRV8825, NEMA step motorları güvenli ve hassas şekilde sürmek için kullanılan step motor sürücüleridir.
 * Tilt: DC Motor + Enkoder (JGY-370 + L298N)
 * 
 * Veri Formatı: JSON
 * {"cmd": "MOVE", "P": 100, "T": 500}
 * P: Pan Steps
 * T: Tilt Encoder Counts
 */

#include <AccelStepper.h>
// Bu kütüphane, step motorları (bizim sistemde Pan motoru) profesyonelce kontrol etmek için kullanılır.

// Hızlanma ve Yavaşlama (Acceleration): Motorun aniden durup kalkmasını engeller. Yumuşak kalkış ve duruş sağlar (arabaların gaz ve fren pedalı gibi). Bu sayede motor sarsılmaz ve adım kaçırmaz.
// Aynı Anda Çok İş Yapabilme: Arduino'nun "delay()" komutuyla beklemesini gerektirmez. Bu sayede step motor dönerken Arduino aynı anda seri portu dinleyebilir veya sensör okuyabilir.
// Kodunuzdaki Yeri: AccelStepper panStepper(...) satırında pan motorunu bununla tanımlıyoruz.
#include <ArduinoJson.h>
// Bu kütüphane, Arduino'nun JSON verilerini anlamasını ve oluşturmasını sağlar.

// Veri Alma: Bilgisayardan gelen {"cmd": "MOVE", "P": 100} gibi metinleri parçalar ve içindeki komutları ("MOVE"), sayıları (100) ayıklar.
// Veri Gönderme: Arduino'nun durumunu (pozisyon, hız vb.) bilgisayara geri gönderirken {"status": "OK"} gibi düzgün, standart bir formatta paketler.
// Neden Gerekli? Elle metin parçalamak (string parsing) çok zordur ve hataya açıktır. Bu kütüphane bu işi hatasız yapar.





// ==========================================
// 1. TILT Motoru (JGY-370 DC Motor + Encoder)
// Bu motoru L298N Sürücü ile kullanacağız.

// A) Sürücü (L298N) <-> Arduino Bağlantısı:

// ENA: -> Pin 9 (PWM hız kontrolü için jumper'ı çıkarın!)
// IN1: -> Pin 7
// IN2: -> Pin 8
// GND: -> Arduino GND (Burası çok önemli, toprakları birleştirin)
// B) Motor Kabloları (JGY-370) <-> Arduino Bağlantısı: Motorun arkasında 6 tane kablo vardır:

// Motor + (Kırmızı): -> L298N OUT1
// Motor - (Beyaz): -> L298N OUT2
// Sensor GND (Siyah): -> Arduino GND
// Sensor VCC (Mavi): -> Arduino 5V
// Encoder A (Sarı): -> Pin 2 (Kesme pini)
// Encoder B (Yeşil): -> Pin 3 (Kesme pini)
//----------------------------------------------------------------

// 2. PAN Motoru (NEMA 17 Step Motor)
// Bu motoru A4988 veya DRV8825 Sürücü ile kullanacağız.

// A) Sürücü (A4988) <-> Arduino Bağlantısı:

// STEP: -> Pin 4
// DIR: -> Pin 5
// EN (Enable): -> Pin 6 (A4988'de EN pini boş bırakılırsa motor çalışır ama kodda kontrol etmek iyidir)
// RESET ve SLEEP: -> Birbirine bağlayın (Kısa devre yapın)
// VDD: -> Arduino 5V
// GND: -> Arduino GND
// B) Motor Kabloları (NEMA 17) <-> Sürücü Bağlantısı:

// Motorun 4 kablosunu (1A, 1B, 2A, 2B) sırasıyla sürücünün çıkışlarına bağlayın. Eğer motor ters dönerse soketi ters çevirmeniz yeterlidir.

// ==========================================

// --- TILT MOTOR (DC + Encoder) ---
// Encoder pinleri Interrupt (2 ve 3) olmak ZORUNDA
#define TILT_ENC_A 2      // Interrupt 0
#define TILT_ENC_B 3      // Interrupt 1
#define TILT_PWM 9        // L298N ENA (Hız)
#define TILT_IN1 7        // L298N IN1
#define TILT_IN2 8        // L298N IN2

// --- PAN MOTOR (Step) ---
#define PAN_STEP_PIN 4    // bu pin A4988'in STEP pinine bağlanır
#define PAN_DIR_PIN 5     // bu pin A4988'in DIR pinine bağlanır
#define PAN_ENABLE_PIN 6  // bu pin A4988'in EN pinine bağlanır




// ==========================================
// AYARLAR
// ==========================================



// Pan Step Ayarları
#define MAX_SPEED_PAN 2000.0
#define MAX_ACCEL_PAN 1000.0

// Tilt PID Ayarları (JGY-370 için ayarlanmalı)
double Kp = 2.0;    // Oransal
double Ki = 0.0;    // İntegral
double Kd = 0.1;    // Türev

// Encoder Değişkenleri
//Özetle: "Bu sayı çok büyüyebilir (long) ve her an, habersizce değişebilir (volatile), o yüzden her seferinde gidip hafızadan en güncel halini oku."
volatile long tiltPosition = 0;
volatile long lastTiltPosition = 0;

// PID Değişkenleri
long targetTiltCount = 0;
double error, lastError, integral;
unsigned long lastPidTime = 0;




// Pan Stepper Nesnesi
// ==========================================
// AccelStepper::DRIVER: Kütüphaneye "Benim arada bir Sürücüm (A4988) var" diyoruz.
// Eğer sürücü kullanmasaydık (direkt motor kablolarını Arduino'ya bağlasaydık) buraya FULL4WIRE yazardık. Ama biz STEP ve DIR pinlerini kullanan akıllı bir sürücü kullanıyoruz.
// PAN_STEP_PIN: Sürücünün "Step" (Adım at) bacağına bağlı pin.
// PAN_DIR_PIN: Sürücünün "Dir" (Yön değiştir) bacağına bağlı pin.
// Bu sayede kodun ilerleyen kısımlarında sadece panStepper.moveTo(100) dememiz yetiyor; Arduino hangi pini yakıp söndüreceğini kendi biliyor.
// ==========================================
AccelStepper panStepper(AccelStepper::DRIVER, PAN_STEP_PIN, PAN_DIR_PIN);
// ==========================================
// STEP ve DIR Arasındaki Fark Nedir?

// Bu iki pin, step motoru kontrol etmek için kullanılan en temel komutlardır.

// STEP Pini (Adım At):
// Bu pine her 1 saniyelik elektrik verip kestiğinizde (Puls gönderdiğinizde), motor tek bir adım (1.8 derece) döner ve durur.
// Saniyede 10 kere gönderirseniz yavaş döner.
// Saniyede 1000 kere gönderirseniz çok hızlı döner.
// Görevi: Motorun Hızını ve Dönme Miktarını belirler.
// DIR Pini (Yön Değiştir):
// Bu pine sürekli elektrik (HIGH) verirseniz, motor Saat Yönünde döner.
// Bu pinden elektriği keserseniz (LOW) yaparsanız, motor Saat Yönünün Tersi yönünde döner.
// Görevi: Motorun Sağa mı Sola mı döneceğini belirler.
// Örnek Senaryo: Arduino, motora "Sağa dön" demek isterse:

// DIR pinini HIGH yapar.
// STEP pinine tık-tık-tık diye sinyal gönderir.
// ==========================================





// JSON İletişim
// // ==========================================
// JSON İletişim Değişkenleri
// Bu kısım, bilgisayardan gelen karmaşık cümleleri (JSON) anlamak için hazırladığımız not defteridir.

// StaticJsonDocument<200> doc;
// Anlamı: "Bana hafızada 200 byte'lık bir alan ayır. Gelen JSON'ı burada parçalayacağım."
// Arduino'nun hafızası (RAM) çok az olduğu için bu boyutu önceden belirlemek zorundayız.
// String inputString = "";
// Anlamı: "Bilgisayardan harf harf gelen verileri birleştirip burada cümle haline getireceğim."
// Seri porttan veriler tek tek gelir ('M', 'O', 'V', 'E'...). Bunları yan yana ekleyip anlamlı bir kelime yaparız.
// boolean stringComplete = false;
// Anlamı: "Cümle bitti mi bayrağı."
// Bilgisayar cümlenin sonuna "Enter" (\n) bastığında bu bayrağı kaldırırız (True yaparız). Ana döngü (
// loop
// ) bu bayrağı görünce "Hah, mesaj gelmiş, hadi okuyalım" der.
// ==========================================
StaticJsonDocument<200> doc;
String inputString = "";
boolean stringComplete = false;

// Zamanlama
unsigned long lastStatusTime = 0;
const int STATUS_INTERVAL = 100; // ms


void setup() {
  // Serial Başlat
  Serial.begin(115200);
  inputString.reserve(200);

  // ==========================================
// inputString.reserve(200); Satırının Anlamı

// Bu satır, Arduino'ya "Bana hafızada önceden 200 harflik bir yer ayırt, son anda sıkışmayayım" demektir.

// 🏨 Otel Rezervasyonu Gibi Düşün
// Rezervasyonsuz (Kötü Yöntem):
// Bir harf gelir: "Bir oda ver!" (Arduino hafızayı böler).
// İkinci harf gelir: "Bir oda daha ver!" (Hafızayı yine böler).
// Bu durum Hafıza Dağınıklığına (Fragmentation) yol açar ve bir süre sonra Arduino kilitlenip donabilir.
// reserve(200) (İyi Yöntem):
// Arduino baştan 200 kişilik koca bir salonu kapatır.
// Harfler geldikçe "Buyrun salon sizin" der.
// Ekstra işlem yapmaz, hafıza tertemiz kalır ve çok hızlı çalışır.
// Bu, özellikle String kullanırken Arduino'nun çökmemesi için hayati bir önlemdir.
// ==========================================

// INPUT_PULLUP: Arduino'nun pinlerini dinleyici moda alır. Özellikle PULLUP, kablo kopsa bile pinin boşlukta sallanıp rastgele sinyal üretmesini engeller (içeriden 5V'a bağlar).
// OUTPUT: Pinleri emir verici (elektrik gönderici) moda alır. Motoru sürmek için gereklidir.
  // --- TILT MOTOR KURULUMU ---
  pinMode(TILT_ENC_A, INPUT_PULLUP);
  pinMode(TILT_ENC_B, INPUT_PULLUP);
  pinMode(TILT_PWM, OUTPUT);
  pinMode(TILT_IN1, OUTPUT);
  pinMode(TILT_IN2, OUTPUT);
  
//   // Interrupt Tanımla
//   Anlamı: "Şu andan itibaren A veya B pininde en ufak bir kıpırdanma (CHANGE) olursa, ne yapıyorsan bırak ve hemen 
// readEncoder
//  fonksiyonuna koş!"
// Bu sayede motor çok hızlı dönse bile Arduino hiçbir adımı kaçırmaz. (Normal bir döngüde kontrol etseydik, başka iş yaparken motor dönüp geçmiş olabilirdi).
  attachInterrupt(digitalPinToInterrupt(TILT_ENC_A), readEncoder, CHANGE);
  attachInterrupt(digitalPinToInterrupt(TILT_ENC_B), readEncoder, CHANGE);

  // --- PAN MOTOR KURULUMU ---
  // digitalWrite(PAN_ENABLE_PIN, LOW); // Kontağı çevir (Motoru kilitle/hazırla)
  // panStepper.setMaxSpeed(MAX_SPEED_PAN); // Hız limitini koy
  // panStepper.setCurrentPosition(0);      // "Burası senin EVİN (0)" de.
  // Step motorların nerede olduğunu bilmesi için bir referansa ihtiyacı vardır. Açılışta bulunduğu yeri "0" kabul ediyoruz.    

  pinMode(PAN_ENABLE_PIN, OUTPUT);
  digitalWrite(PAN_ENABLE_PIN, LOW); // Aktif (LOW)
  
  panStepper.setMaxSpeed(MAX_SPEED_PAN);
  panStepper.setAcceleration(MAX_ACCEL_PAN);
  panStepper.setCurrentPosition(0);

  // Başlangıç Mesajı
  Serial.println(F("{\"status\":\"READY\",\"msg\":\"Hybrid Controller Started\"}"));
}




// ==========================================

// otor Kurulum Bölümü (
// setup
// ) Açıklaması

// Bu kısımda motorları "savaşa hazırlıyoruz".

// 1. Tilt Motoru (DC) Kurulumu
// pinMode(TILT_ENC_A, INPUT_PULLUP);
// Ne Yapar: Pin 2'yi "Giriş" yapar ve içindeki 20k ohm direnci açar.
// Neden: Enkoderden gelen sinyali okumak için. PULLUP sayesinde kablo kopsa bile pin kararsız kalmaz, HIGH okunur.



// pinMode(TILT_PWM, OUTPUT);
// Ne Yapar: Pin 9'u "Çıkış" yapar.
// Neden: Motor sürücüye (L298N) hız sinyali (PWM) göndermek için.



// attachInterrupt(digitalPinToInterrupt(TILT_ENC_A), readEncoder, CHANGE);
// Ne Yapar (Çok Önemli!): "Pin 2'de en ufak bir değişiklik (CHANGE) olursa, elindeki işi bırak ve hemen 
// readEncoder
//  fonksiyonuna koş!"
// Neden: Arduino başka işlerle uğraşırken enkoder çok hızlı dönerse adımları kaçırmamak için. Bu bir "Alarm Sistemi"dir.



// 2. Pan Motoru (Step) Kurulumu
// digitalWrite(PAN_ENABLE_PIN, LOW);
// Ne Yapar: Enable pinine 0 volt verir.
// Neden: A4988 sürücüsü ters mantıkla çalışır. LOW yapınca uyanır, HIGH yapınca uyur (Motor kilitlenmez, elle döner). Biz motorun kilitlenip hazır olmasını istiyoruz.



// panStepper.setMaxSpeed(MAX_SPEED_PAN);
// Ne Yapar: Hız limitini 2000 adım/saniye olarak ayarlar.
// Neden: Motorun kapasitesinden fazla hız istemeyelim diye (yoksa motor ıslık sesi çıkarır ama dönmez).



// panStepper.setCurrentPosition(0);
// Ne Yapar: "Şu an durduğun yer senin Evin (0 noktası)" der.
// Neden: Tüm hareketler bu noktaya göre hesaplanacaktır.



// Örnek: Enkoder Pini. Enkoder dönerken Arduino'ya "Ben döndüm!" diye sinyal gönderir. Arduino bunu duymak için kulağını açar (INPUT).




// 2. Interrupt (Kesme) Nedir? 🚨
// Bunu "Kapı Zili" olarak düşün.

// Interrupt Olmasaydı: Sen kulaklıkla müzik dinliyorsun (Arduino başka iş yapıyor). Kapı çalıyor ama duymuyorsun. Kargo geliyor, gidiyor, haberin yok (Enkoder adım kaçırıyor). Bunu engellemek için sürekli kapıya gidip bakman lazım: "Gelen var mı? Yok. Gelen var mı? Yok." (Bu çok yorucu ve yavaştır).
// Interrupt Varsa: Kapı ziline basıldığı an, ne yapıyorsan yap (müzik dinle, uyu), zank diye durursun ve hemen kapıya koşarsın. Kargoyu alırsın, sonra kaldığın yerden devam edersin. Enkoder pini de böyledir. Motor döndüğü an Arduino her şeyi bırakır, "Bir adım döndük!" diye not alır ve işine döner.





// 3. 
// panStepper
// Nesnesi Nedir? 🤖
// Bu, Step Motorunuzun Özel Şoförüdür.

// Eğer AccelStepper kütüphanesi olmasaydı, motoru döndürmek için şöyle kod yazmanız gerekirdi:

    // Pini aç.
// Bunu bekle.
// Pini kapat.
// Bunu bekle.
// Hızlanmak için bekleme süresini azalt... (Çok zor!)
// panStepper
// nesnesi tüm bu zor işleri sizin yerinize yapar. Siz sadece arka koltuktan:

// "Hızlan!" (setAcceleration)
// "100. metreye git!" (moveTo) dersiniz, şoför (
// panStepper
// ) motoru sarsmadan, hızlanarak ve yavaşlayarak oraya götürür.
// ==========================================


void loop() {
  // 1. Pan Motoru Çalıştır (Sürekli çağrılmalı!)
  panStepper.run();

  // 2. Tilt PID Kontrolü
  computePID();

  // 3. Serial Komut İşleme
  if (stringComplete) {
    processJSON();
    inputString = "";
    stringComplete = false;
  }
}


// ==========================================
// Bu blok, Arduino'nun "Ana Döngüsüdür" (
// loop
//  fonksiyonu). Buradaki kodlar saniyede binlerce kez durmadan, sonsuza kadar döner.

// Üç kritik parçayı (Pan, Tilt, İletişim) aynı anda idare etmek için çok önemli bir sıralama vardır:


// 1. panStepper.run() (Pan Şoförü)
// Öncelik: Çok Yüksek
// Step motorun her bir adımını atmak için bu komutun sürekli çağrılması gerekir.
// Neden önemli? Eğer delay() gibi bir komutla bu satırı geciktirirseniz, pan hareketi kekeler, takılır. Burası asla bekletilmemelidir.
// 2. 
// computePID()
//  (Tilt Beyni)
// Bu fonksiyon her seferinde çağrılır ama içinde kendi saati vardır (kodun aşağısında göreceksiniz: if (now - lastPidTime >= 10)).
// Anlamı: "Her turda kontrol et, ama sadece milisaniyede bir (10ms) hesaplama yap."
// Sürekli hesap yapmak işlemciyi boşa yorar, 10ms (saniyede 100 kere) kontrol etmek PID için yeterlidir.
// 3. Komut İşleme (Posta Servisi)
// if (stringComplete): "Yeni bir emir geldi mi?" diye bakar. (Bu bayrağı 
// serialEvent
//  veya interrupt kaldırır).
// Varsa, 
// processJSON()
//  ile emri uygular ve bayrağı indirir.
// Özet: Bu döngü bir orkestra şefi gibidir.

// "Pan, sen bir adım at."
// "Tilt, senin hesap vaktin geldi mi? Hayır. Tamam geç."
// "PC'den emir var mı? Yok. Tamam başa dön."
// "Pan, sen bir adım daha at..."
// Bu sayede tek bir beyin (Arduino), üç işi aynı anda yapıyormuş gibi görünür.





// Pan (Step Motor):
// Step motorlar doğası gereği zaten çok hassastır. "100 adım at" derseniz, tam 100 adım atar ve orada zımba gibi durur. Hata yapmaz, kaymaz.
// Bu yüzden PID'ye (Düzeltme Çabasına) ihtiyacı yoktur. Sadece "Git" demek yeterlidir. (AccelStepper kütüphanesi hızlanma/yavaşlamayı halleder).
// Tilt (DC Motor):
// DC motorlar "aptaldır". Elektrik verirseniz döner, keserseniz durur (ama hemen değil, kayarak durur).
// "30 dereceye git" diyemezsiniz. "Elektrik ver... ver... şimdi kes... eyvah biraz geç kestim, geri gel" demeniz gerekir.
// İşte bu "Neredeyim? Hedefe ne kadar kaldı? Ne kadar elektrik vermeliyim?" hesabını sürekli yapan şeye PID denir.

// ==========================================



// ==========================================
// PID KONTROL DÖNGÜSÜ (TILT İÇİN)


// 1. error = targetTiltCount - currentPos;
// Anlamı: "Neredeyim, nereye gitmeliyim?"

// targetTiltCount: Gitmem gereken ev (100. km)
// currentPos: Şu an 80. km'deyim.
// error
// : 100 - 80 = 20. (Daha 20 km yolum var).
// 2. output = (Kp * error) + (Ki * integral) + (Kd * derivative);
// İşte sihir burada! Üç farklı danışman motora ne yapacağını söylüyor:

// P (Şimdiki Zaman - Aceleci):
// Kp * error
// "Hata 20 km mi? O zaman gaza bas!"
// Hata büyükse çok gaz verir, küçükse az gaz verir. Ama tek başına yeterli değildir, hedefe yaklaşınca çok yavaşlar.
// I (Geçmiş Zaman - İnatçı):
// Ki * integral
// "Yarım saattir 2 km kala durduk, gitmiyoruz! Bas gaza!"
// integral değişkeni, geçmişteki hataları toplar. Eğer uzun süre hedefe varamazsanız bu sayı büyür ve motoru zorla iter.
// D (Gelecek Zaman - Tedbirli):
// Kd * derivative
// "Hızla yaklaşıyoruz, çarpacağız! frene bas!"
// derivative (türev), hatanın ne kadar hızlı değiştiğine bakar. Hızla yaklaşıyorsanız bu sayı negatiftir ve outputu azaltır (fren yapar).
// Sonuç (output)
// Bu üç danışmanın toplam sesi motorun voltajı olur:

// P: "Bas!"
// I: "Daha çok bas!"
// D: "Yavaşla!"
// Sonuç: Motor, hedefe tam zamanında ve sarsıntısız bir şekilde varır.
// Eğer bu hesap olmasaydı, motor ya hedefe varamazdı ya da hedefi hızla geçip (overshoot) geri dönmeye çalışırdı (titrerdı).
// ==========================================
void computePID() {
  unsigned long now = millis();
  if (now - lastPidTime >= 10) { // 10ms'de bir çalış (100Hz)
    lastPidTime = now;

    // Hata hesabı (interrupt güvenliği için atomik okuma)
    noInterrupts();
    long currentPos = tiltPosition;
    interrupts();
    error = targetTiltCount - currentPos;
    
    // İntegral (Anti-windup korumalı)
    integral += error;
    if (integral > 1000) integral = 1000;
    if (integral < -1000) integral = -1000;
    
    // Türev
    double derivative = error - lastError;
    
    // PID Çıkışı
    double output = (Kp * error) + (Ki * integral) + (Kd * derivative);
    
    // Motoru Sür
    driveDC(output);
    
    lastError = error;
  }
}

// ==========================================
// DC MOTOR SÜRÜCÜ (L298N)
// ==========================================
void driveDC(double pwm) {
  // PWM sınırla (-255 ile 255 arası)
  // Arduino'nun analogWrite komutu en fazla 255 (tam gaz) kabul eder.
  // PID bazen gaza gelip 500 diyebilir. Bu kod, "Sakin ol şampiyon, en fazla 255 basabiliriz" der ve sınırlar.
  if (pwm > 255) pwm = 255;
  if (pwm < -255) pwm = -255;

  // Deadzone (Çok küçük güçte hareket etmez, sesi kesmek için)
  if (abs(pwm) < 20) {
    pwm = 0;
  }
  // pwm pozitifse (+), motoru ileri döndürür.
  // pwm negatifse (-), motoru geri döndürür.
  // 0 ise motoru serbest bırakır (fren yapmaz, akışına bırakır).

  if (pwm > 0) {
    digitalWrite(TILT_IN1, HIGH);
    digitalWrite(TILT_IN2, LOW);
  } else if (pwm < 0) {
    digitalWrite(TILT_IN1, LOW);
    digitalWrite(TILT_IN2, HIGH);
  } else {
    digitalWrite(TILT_IN1, LOW);
    digitalWrite(TILT_IN2, LOW);
  }
  
  analogWrite(TILT_PWM, abs(pwm));
}

// Son olarak hesaplanan şiddeti (abs(pwm) yani mutlak değer, çünkü hız negatif olamaz, yön negatif olur) motora gönderir.
// abs(-150) = 150. Yani "Geri vitese tak, 150 şiddetinde gaza bas."

// ==========================================
// SERIAL EVENT & JSON PARSING
// ==========================================
void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    inputString += inChar;
    if (inChar == '\n') {
      stringComplete = true;
    }
  }
}

void processJSON() {
  DeserializationError error = deserializeJson(doc, inputString);

  if (error) {
    // JSON hatası varsa yoksay veya bildir
    return;
  }

  const char* cmd = doc["cmd"];

  if (strcmp(cmd, "MOVE") == 0) {
    // Relative hareket: Mevcut konuma ekle
    long p_steps = doc["P"];  // Pan Step
    long t_counts = doc["T"]; // Tilt Count
    
    // Pan: AccelStepper zaten relative 'move' veya absolute 'moveTo' destekler
    // MotorCalculator'dan 'delta' geliyorsa move(), 'target' geliyorsa moveTo()
    // Bizim yapımızda 'MotorCommand' içinde hedef pozisyon değil, değişim (delta) olması daha güvenli
    // Ancak main.py'de target gönderiyor olabiliriz.
    // Şimdilik RELATIVE (değişim) kabul edelim:
    
    panStepper.move(p_steps); 
    targetTiltCount += t_counts;

    sendAck();
  }
  else if (strcmp(cmd, "HOME") == 0) {
    panStepper.setCurrentPosition(0);
    targetTiltCount = 0;
    noInterrupts();       // Interrupt durdur (race condition koruması)
    tiltPosition = 0;     // Güvenli yaz
    interrupts();         // Interrupt tekrar aç
    integral = 0;         // PID integralini de sıfırla
    lastError = 0;
    sendAck();
  }
  else if (strcmp(cmd, "STOP") == 0) {
    panStepper.stop();    // Pan motorunu durdur
    noInterrupts();
    targetTiltCount = tiltPosition;  // Mevcut konumu hedef yap → tilt motoru durur
    interrupts();
    integral = 0;
    lastError = 0;
    sendAck();
  }
  else if (strcmp(cmd, "CALIBRATE") == 0) {
    // Kalibrasyon: Şu an HOME ile aynı işi yapıyor (pozisyonları sıfırla).
    // İleride limit switch veya sensör eklenirse, motorlar önce referans noktasına
    // gidip sonra sıfırlanabilir.
    panStepper.setCurrentPosition(0);
    targetTiltCount = 0;
    noInterrupts();
    tiltPosition = 0;
    interrupts();
    integral = 0;
    lastError = 0;
    sendAck();
  }
  else if (strcmp(cmd, "STATUS") == 0) {
    sendStatus();
  }
}


// ==========================================


// processJSON()
//  Fonksiyonu: Beyin Kısmı 🧠

// Bu fonksiyonun görevi, gelen mektubu açıp içindeki emri yerine getirmektir.

// Satır satır analiz:

// DeserializationError error = deserializeJson(doc, inputString);
// Anlamı: "Gelen yazıyı (inputString), hafızadaki not defterine (doc) aktar."
// JSON formatını çözmeye çalışır.
// if (error) { return; }
// Anlamı: "Eğer yazı bozuksa (JSON değilse), hiç uğraşma, çık."
// const char* cmd = doc["cmd"];
// Anlamı: "Mesajın içindeki cmd (komut) başlığını oku."
// Örn: {"cmd": "MOVE"} geldiyse, cmd değişkeni "MOVE" olur.



// Komutları Ayıklama (if-else Zinciri)
// if (strcmp(cmd, "MOVE") == 0)
// Anlamı: "Gelen emir MOVE (Hareket Et) mi?"
// strcmp (String Compare): İki kelimeyi karşılaştırır. Eşitse 0 döner.
// long p_steps = doc["P"];
// "P başlığındaki sayıyı al." (Pan adımı)
// long t_counts = doc["T"];
// "T başlığındaki sayıyı al." (Tilt adımı)
// panStepper.move(p_steps);
// Çok Önemli: 
// move()
//  komutu Relative (Göreceli) hareket yapar.
// "Bulunduğun yerden p_steps kadar ileri git."
// targetTiltCount += t_counts;
// Anlamı: "Tilt hedefimi, gelen sayı kadar artır/azalt."
// (PID döngüsü bu yeni hedefi görünce motoru oraya götürecektir).
// sendAck();
// "Emir anlaşıldı tamam!" mesajı gönder.
// else if (strcmp(cmd, "HOME") == 0)
// Anlamı: "Gelen emir HOME (Eve Dön / Sıfırla) mı?"
// panStepper.setCurrentPosition(0); -> "Pan motoru, şu anki yerini 0 kabul et."
// targetTiltCount = 0; tiltPosition = 0; -> "Tilt motoru, sen de sıfırlan."
// else if (strcmp(cmd, "STATUS") == 0)
// Anlamı: "Gelen emir STATUS (Durum Raporu) mu?"
// sendStatus();
//  -> "Şu an nerede olduğunu yaz."
// ==========================================




void sendAck() {
  Serial.print(F("{\"status\":\"OK\",\"P\":"));
  Serial.print(panStepper.currentPosition());
  Serial.print(F(",\"T\":"));
  Serial.print(tiltPosition);
  Serial.println(F("}"));
}

void sendStatus() {
  // JSON oluşturup gönder
  doc.clear();
  doc["status"] = "STATUS";
  doc["P_act"] = panStepper.currentPosition();
  doc["T_act"] = tiltPosition;
  doc["T_set"] = targetTiltCount;
  serializeJson(doc, Serial);
  Serial.println();
}

// ==========================================
// ENCODER INTERRUPT
// ==========================================
void readEncoder() {
  // Quadrature enkoder: A ve B pinlerinin durumunu karşılaştırarak yön belirle
  int a = digitalRead(TILT_ENC_A);
  int b = digitalRead(TILT_ENC_B);
  if (a == b) {
    tiltPosition++;   // İleri yön
  } else {
    tiltPosition--;   // Geri yön
  }
}
