"""
Serial Haberleşme Modülü
Arduino/ESP32 ile USB Serial iletişim
"""

import json
import time
import threading
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from queue import Queue, Empty


@dataclass
class MotorCommand:
    """
    Motor komut yapısı
    Hibrit Sistem:
    - Pan: Step sayısı (int)
    - Tilt: Encoder count (int)
    """
    pan_steps: int = 0
    tilt_counts: int = 0
    pan_speed: float = 0.0   # Opsiyonel: Hız bilgisi
    tilt_speed: float = 0.0  # Opsiyonel: Hız bilgisi


class SerialCommunicator:
    """
    Serial Haberleşme Sınıfı
    JSON tabanlı protokol ile Arduino/ESP32 iletişimi
    """
    
    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        baudrate: int = 115200,
        timeout: float = 0.1,
        auto_reconnect: bool = True
    ):
        """
        Args:
            port: Serial port ("/dev/ttyUSB0", "/dev/ttyACM0", "COM3" vb.)
            baudrate: Baud rate
            timeout: Okuma timeout (saniye)
            auto_reconnect: Bağlantı kopunca otomatik yeniden bağlan
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.auto_reconnect = auto_reconnect
        
        self.serial = None
        self.connected = False
        
        # Threading
        self.read_thread = None
        # Bu değişken, okuma döngüsünün (loop) çalışıp çalışmayacağını kontrol eder.
        # start_reading içinde True yapılır, disconnect içinde False yapılır.   
        self.running = False
        # Gelen verilerin geçici olarak tutulduğu yer (kuyruk)
        self.receive_queue = Queue()
        
        # Callbacks
        """
        
        Callable, Python'da "Bu bir fonksiyondur, bunu çağırabilirsin" anlamına gelir.
        Callable[[GirdiTipi], ÇıktıTipi]
        [GirdiTipi]: Fonksiyona ne göndereceğiz? (Örn: Dict yani sözlük)
        ÇıktıTipi: Fonksiyon bize ne geri döndürecek? (Örn: None yani hiçbir şey)
        """

        # Bu değişkenler, dışarıdan bağlanacak fonksiyonlar için "giriş kapıları"dır.
        # şu an boşlar (None). main.py bunları dolduracak.
        self.on_receive: Optional[Callable[[Dict], None]] = None
        self.on_connect: Optional[Callable[[], None]] = None
        self.on_disconnect: Optional[Callable[[], None]] = None
        
        # Son alınan durum
        self.last_status = {}
        
    def connect(self) -> bool:
        """Serial porta bağlan"""
        try:
            import serial
            
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            
            # Arduino'nun başlaması için bekle
            time.sleep(2)
            
            # Buffer'ı temizle
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            
            self.connected = True
            print(f"[SERIAL] Bağlandı: {self.port} @ {self.baudrate} baud")
            
            if self.on_connect:
                self.on_connect()
            
            return True
            
        except ImportError:
            print("[HATA] pyserial kütüphanesi bulunamadı!")
            print("Kurulum: pip install pyserial")
            return False
        except Exception as e:
            print(f"[HATA] Serial bağlantı hatası: {e}")
            return False

    # Bu fonksiyon, dışarıdan "Benimle ilgilen" diye çağrılacak.
    def set_callbacks(self, on_receive=None, on_connect=None, on_disconnect=None):
        """Callback fonksiyonları ayarla"""
        self.on_receive = on_receive
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
    



    def disconnect(self):
        """Bağlantıyı kapat"""
        self.running = False
        
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=1.0)
        
        if self.serial and self.serial.is_open:
            self.serial.close()
            
        self.connected = False
        print("[SERIAL] Bağlantı kapatıldı")
        
        if self.on_disconnect:
            self.on_disconnect()
    



    def start_reading(self):
        """Arka planda okuma başlat
        
        
        """
        if not self.connected:
            print("[HATA] Önce bağlanın!")
            return
        
        self.running = True
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()
        print("[SERIAL] Okuma thread'i başlatıldı")
    



    def _read_loop(self):
        """Arka plan okuma döngüsü"""
        while self.running and self.connected:
            try:
                if self.serial and self.serial.in_waiting > 0:
                    line = self.serial.readline().decode('utf-8').strip()
                    
                    if line:
                        # GÜÇLENDİRİLMİŞ (ROBUST) OKUMA MANTIĞI:
                        # 1. Satırdaki ilk '{' işaretini bul (JSON başlangıcı)
                        # 2. Satırdaki son '}' işaretini bul (JSON bitişi)
                        # 3. Aradaki kısmı cımbızla çek al
                        
                        start_idx = line.find('{')
                        end_idx = line.rfind('}')
                        
                        # Eğer hem { hem de } varsa ve sıra doğruysa ({ önce gelmeli)
                        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                            # Sadece JSON kısmını al (substring)
                            json_str = line[start_idx : end_idx + 1]
                            
                            try:
                                data = json.loads(json_str)
                                self.last_status = data
                                self.receive_queue.put(data)
                                
                                if self.on_receive:
                                    self.on_receive(data)
                            except json.JSONDecodeError:
                                pass # Bozuk JSON ise yoksay
                        else:
                            # Debug mesajlarını yazdır (opsiyonel)
                            # print(f"[ARDUINO] {line}")
                            pass
                            
            except Exception as e:
                print(f"[SERIAL] Okuma hatası: {e}")
                if self.auto_reconnect:
                    self._try_reconnect()
                else:
                    break
                    
            time.sleep(0.001)
    



    def _try_reconnect(self):
        """Yeniden bağlanmayı dene
                for i in range(5):
            # 1. Tur: i = 0 olur.
            # 2. Tur: i = 1 olur.
            # 3. Tur: i = 2 olur.
            # 4. Tur: i = 3 olur.
            # 5. Tur: i = 4 olur.
            
            if self.connect():
                return  # Bağlanınca döngüden ve fonksiyondan kaçar!
            
            time.sleep(1) # Başarısız olursak 1 saniye bekle
        
        
        """
        print("[SERIAL] Yeniden bağlanılıyor...")
        self.connected = False
        time.sleep(1)
        
        for i in range(5):
            if self.connect():
                return
            time.sleep(1)
        
        print("[SERIAL] Yeniden bağlanma başarısız!")
    


    def send_command(self, command: MotorCommand) -> bool:
        """
        Motor komutu gönder
        
        Args:
            command: MotorCommand nesnesi
            
        Returns:
            Başarılı mı
        """
        if not self.connected:
            return False
        
        # RELATIVE hareket gönderiyoruz (mevcut konuma göre değişim)
        # Arduino tarafı bu değerleri mevcut konumuna ekleyecek
        data = {
            "cmd": "MOVE",
            "P": int(command.pan_steps),    # Pan: Adım
            "T": int(command.tilt_counts)   # Tilt: Count
        }
        
        # Opsiyonel: Hız bilgisi de gönderilebilir
        if command.pan_speed > 0 or command.tilt_speed > 0:
            data["SP"] = int(command.pan_speed)
            data["ST"] = int(command.tilt_speed)
        
        return self._send_json(data)
    


    def send_home(self) -> bool:
        """Home pozisyonuna git"""
        return self._send_json({"cmd": "HOME"})
    


    def send_stop(self) -> bool:
        """Motorları durdur"""
        return self._send_json({"cmd": "STOP"})
    

    # bu kısımileride sensör eklenirse genişletilecek   a 
    def send_calibrate(self) -> bool:
        """Kalibrasyon komutu gönder
        
        Arduino'ya CALIBRATE komutu gönderir. Şu an HOME ile aynı işi yapar
        (tüm pozisyonları sıfırlar). İleride limit switch veya sensör eklenirse
        motorlar önce fiziksel referans noktasına gidip sonra sıfırlanabilir.
        
        Kullanım: main.py içinde 'c' tuşuna basınca çağrılır.
        Arduino karşılığı: motor_controller.ino → processJSON() → "CALIBRATE"
        """
        return self._send_json({"cmd": "CALIBRATE"})
    
    def is_connected(self) -> bool:
        """Bağlantı durumunu döndür"""
        return self.connected
    


    def send_status_request(self) -> bool:
        """Durum bilgisi iste"""
        return self._send_json({"cmd": "STATUS"})
    



    def _send_json(self, data: Dict[str, Any]) -> bool:
        """JSON verisi gönder"""
        if not self.connected or not self.serial:
            return False
        
        try:
            message = json.dumps(data) + "\n"
            self.serial.write(message.encode('utf-8'))
            self.serial.flush()
            return True
        except Exception as e:
            print(f"[SERIAL] Gönderme hatası: {e}")
            return False
    


    def list_ports(self) -> list:
        """Mevcut serial portları listele"""
        try:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            return [{"device": p.device, "description": p.description} for p in ports]
        except:
            return []
    

    # Nesne yok edildiğinde bağlantıyı kapat bu güvenlik için gereklidir
    # Python otomatik olarak __del__ fonksiyonunu çağırır
    def __del__(self):
        self.disconnect()



# Test kodu
if __name__ == "__main__":
    print("Serial Communicator (Hibrit) test başlıyor...")
    print("=" * 60)
    
    comm = SerialCommunicator()
    
    print("\nÖrnek Komut (Simülasyon):")
    # Pan: 50 adım sağa, Tilt: 200 count yukarı
    cmd = MotorCommand(pan_steps=50, tilt_counts=200, pan_speed=500, tilt_speed=2000)
    
    print(f"Komut: Pan={cmd.pan_steps} step, Tilt={cmd.tilt_counts} count")
    
    # JSON yapısını göster
    data = {
        "cmd": "MOVE",
        "P": int(cmd.pan_steps),
        "T": int(cmd.tilt_counts),
        "SP": int(cmd.pan_speed),
        "ST": int(cmd.tilt_speed)
    }
    print(f"JSON: {json.dumps(data)}")
    
    print("\n" + "=" * 60)





# Callbacks
#=======================================================================================

# Satır Satır Analiz
# self.on_receive: Optional[Callable[[Dict], None]]
# Anlamı: "Bana bir fonksiyon ver. Bu fonksiyon içine bir Sözlük (Dict) alabilsin, ama geriye bir şey döndürmesin (None). Eğer fonksiyon vermezsen sorun değil (Optional)."
# Kullanımı: Arduino'dan veri gelince bu fonksiyonu çağırırız ve gelen veriyi (Sözlük olarak) ona veririz.
# self.on_connect: Optional[Callable[[], None]]
# Anlamı: "Bana bir fonksiyon ver. Bu fonksiyon hiçbir şey almasın ([]), geriye de bir şey döndürmesin."
# Kullanımı: Bağlantı kurulduğunda sadece haber vermek için çağırılır.
# 📝 Basit Analoji: "Kartvizit Bırakmak"
# Bu değişkenler aslında birer kartvizit kutusu gibidir.

# self.on_receive = benim_fonksiyonum: "Bak, eğer bir kargo (veri) gelirse, benim bu numaramı (fonksiyonumu) ara ve kargoyu bana ver."
# self.on_receive(): "Alo, kargo geldi!" (Fonksiyonu çağırmak).
# Eğer kartvizit kutusu boşsa (None), kimseyi aramayız.







# on_connect Kullanımı: 
# connect()
#  fonksiyonunun içinde (başarılı bağlantı kurulduktan sonra):


# self.connected = True
# print(f"[SERIAL] Bağlandı: {self.port} @ {self.baudrate} baud")

# if self.on_connect:  # <-- Bakıyoruz, kartvizit var mı?
#     self.on_connect() # <-- Varsa arıyoruz: "Bağlandık!"





# on_disconnect Kullanımı: 
# disconnect()
#  fonksiyonunun en sonunda:


# self.connected = False
# print("[SERIAL] Bağlantı kapatıldı")

# if self.on_disconnect: # <-- Kartvizit var mı?
#     self.on_disconnect() # <-- Varsa arıyoruz: "Kopardık!"




# on_receive Kullanımı: 
# _read_loop()
#  (arka plandaki okuma) içinde:



# data = json.loads(line)
# self.receive_queue.put(data)

# if self.on_receive: # <-- Kartvizit var mı?
#     self.on_receive(data) # <-- Varsa arıyoruz: "Bak yeni bir şey geldi, al bu 'data' senin."





# Peki bunları kim tanımlıyor?
# Genellikle 
# main.py
#  gibi ana program dosyası. Ana program şunu der:



# # main.py örneği
# def veri_geldi(data):
#     print("Arduino bir şey dedi:", data)

# serial = SerialCommunicator()
# serial.on_receive = veri_geldi  # Kartviziti veriyoruz
# serial.connect()

#=======================================================================================





# disconnect
#=======================================================================================

# Bağlantıyı Güvenli Kapatma (
# disconnect
# ) Fonksiyonu

# Bu fonksiyonun amacı, seri portu "kaba kuvvetle" kapatmak yerine, çalışan işlemleri, okuma döngülerini ve donanım bağlantısını sırayla ve güvenli bir şekilde sonlandırmaktır.

# 🛑 Adım Adım Açıklama
# self.running = False:
# Arka planda çalışan okuma thread'ine (iş parçacığına) "Artık durmalısın" mesajı verir. Okuma döngüsü (while self.running:) bu değişkeni sürekli kontrol eder.


# self.running = False
# Anlamı: "Arkadaşına, 'Artık telefonu dinlemeyi bırak' diyorsun."
# Arkada sürekli çalışan bir "dinleyici" (thread) var. Bu komutla ona durmasını söylüyoruz.





# if self.read_thread and self.read_thread.is_alive():
# Okuma işi yapan bir thread var mı ve hala yaşıyor mu?



# if self.read_thread and self.read_thread.is_alive():
# Anlamı: "Arkadaşım hala hatta mı, yoksa zaten kapatmış mı diye bakıyorsun."
# Eğer dinleyici zaten yoksa veya durmuşsa bir şey yapmaya gerek yok.





# self.read_thread.join(timeout=1.0):
# En Kritik Kısım: Ana programa "Okuma thread'i işini bitirene kadar bekle" der. Eğer beklemeden kapatırsak, thread hala okumaya çalışırken port kapanır ve program çöker. timeout=1.0 ise "En fazla 1 saniye bekle, bitmezse zorla devam et" demektir.


# self.read_thread.join(timeout=1.0)
# Anlamı: "Arkadaşının 'Tamam, kapattım' demesini en fazla 1 saniye bekliyorsun."
# Telefonu yüzüne kapatmıyorsun. Onun son sözünü söylemesini bekliyorsun ki işler karışmasın. Ama 1 saniyeden fazla da beklemiyorsun.





# if self.serial and self.serial.is_open:
# USB portu gerçekten açık mı?


# if self.serial and self.serial.is_open:
# Anlamı: "Telefon hattı gerçekten açık mı diye kontrol ediyorsun."
# Hat zaten kesikse kapatmaya çalışmak hata verir. Sadece açık olan hattı kapatabilirsin.






# self.serial.close():
# İşletim sistemine portu serbest bıraktırır. Bunu yapmazsak, programı kapatıp tekrar açtığınızda "Port meşgul" hatası alırsınız.


# self.serial.close()
# Anlamı: "Telefonu fiziksel olarak yerine koyuyorsun (Hattı kesiyorsun)."
# Artık USB kablosu üzerinden veri akışı tamamen durur. Başka bir program (örneğin Arduino IDE) artık bu portu kullanabilir.



# self.connected = False
# Anlamı: "Kendi not defterine 'Şu an kimseyle konuşmuyorum' yazıyorsun."
# Programın geri kalanı senin bağlı olmadığını anlasın diye bu bayrağı indiriyorsun.





# if self.on_disconnect:
# Eğer birisi "Bağlantı koparsa bana haber ver" dediyse (callback fonksiyonu), ona haber verir. (Örneğin arayüzde "Bağlı Değil" yazmak için).

# if self.on_disconnect: self.on_disconnect()
# Anlamı: "Eğer birisi sana 'Telefonu kapatınca bana haber ver' dediyse, onu arayıp 'Kapattım' diyorsun."
# Örneğin ekranda "Bağlantı Kesildi" yazısı çıkmasını sağlayan fonksiyondur.




#=======================================================================================






# Threading Kullanımı
#=======================================================================================

# Bu satır, Python'a "Ana programım çalışırken, arkada gizlice başka bir iş daha yapayım" demenin yoludur.

# self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
#  Benzetme: "Restoran ve Garsonlar"
# Ana Program (Main Thread): Restoranın müdürüdür. Müşterilerle ilgilenir, hesapları tutar, ana işi yönetir. (Bizim için kameradan görüntü alan, karar veren kısım).
# read_thread (Okuma İş Parçacığı): Mutfakta sürekli soğan doğrayan yardımcı elemandır.



# Parametreler Ne Anlama Geliyor?
# target=self._read_loop:
# Anlamı: "Yardımcı elemana ne iş vereyim?"
# Cevap: Lütfen git 
# _read_loop
#  fonksiyonunu sürekli çalıştır. (Sürekli Arduino'dan veri gelmiş mi diye bak).



#  daemon=True:
# Anlamı: "Bu eleman Ölümlü (Daemon) olsun mu?"
# Evet (True) derseniz: Restoran kapanınca (Ana program kapatılınca), bu eleman işini hemen bırakıp dükkanı terk eder.
# Hayır (False) derseniz: Ana program kapansa bile, bu eleman "Benim işim bitmedi!" deyip programın kapanmasını engeller. Sonsuza kadar çalışmaya devam eder (Zombie Process).
# Neden True yaptık? Programı kapattığımızda arka planda gizlice çalışan ve bilgisayarı yoran işlemler kalmasın diye.
#=======================================================================================







# read loop fonksiyonu
#=======================================================================================

# while self.running and self.connected:
# Anlamı: "Patron bana dur diyene kadar (running) ve telefon hattı açık olduğu sürece (connected) çalışmaya devam et."
# Bu sonsuz bir döngüdür.



# if self.serial and self.serial.in_waiting > 0:
# Anlamı: "Posta kutusunda bekleyen mektup var mı?"
# in_waiting: Okunmayı bekleyen byte sayısı. Eğer 0 ise boşuna okumaya çalışma.



# line = self.serial.readline().decode('utf-8').strip()
# Anlamı:
# readline(): Bir satır oku (Enter tuşuna kadar olan kısmı al).
# decode('utf-8'): Gelen 0 ve 1'leri okunabilir harflere çevir (Byte -> String).
# strip(): Satır sonundaki boşlukları ve \n (yeni satır) karakterini temizle.




# if line.startswith('{'):
# Anlamı: "Gelen mesaj { ile başlıyor mu?"
# Arduino JSON formatında veri gönderdiği için (örn: {"status":"OK"}), sadece süslü parantez ile başlayanları ciddiye alıyoruz. Diğerleri (örneğin Arduino açılırken gelen Booting... yazısı) bizi ilgilendirmiyor.





# data = json.loads(line)
# Anlamı: "Bu yazıyı Python Sözlüğü'ne (Dictionary) çevir."
# '{"a": 1}' (String) --> {'a': 1} (Dict) olur.



# self.last_status = data
# Anlamı: "Son duyduğum haberi tahtaya yaz." (Programın diğer kısımları istediği an son durumu görebilsin diye).




# self.receive_queue.put(data)
# Anlamı: "Bu haberi 'Gelen Evraklar' sepetine koy."
# Kuyruk (Queue) yapısı sayesinde veriler sırayla işlenir, kaybolmaz.






# if self.on_receive: self.on_receive(data)
# Anlamı: "Eğer patron 'bana haber ver' dediyse, onu hemen ara." (Callback fonksiyonu).




# except json.JSONDecodeError:
# Anlamı: "Eğer mektup bozuk geldiyse (yarım yamalak JSON), panik yapma. Çöpe at ve devam et (pass)."
# except Exception as e:
# Anlamı: "Eğer başka büyük bir hata olursa (örn: kablo çıktı), hatayı ekrana yaz."





# if self.auto_reconnect: self._try_reconnect()
# Anlamı: "Hata büyükse ve 'Otomatik Bağlan' açıksa, hemen yeniden bağlanmayı dene."



# time.sleep(0.001)
# Anlamı: "Çok minik bir mola ver (1 milisaniye)."
# Bu, işlemciyi (CPU) %100 kullanıp bilgisayarı kilitlememek içindir. Nefes alma payıdır.
#=======================================================================================
