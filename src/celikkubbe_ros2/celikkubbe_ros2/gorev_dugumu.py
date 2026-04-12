import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, GoalResponse, CancelResponse
from rclpy.action.server import ServerGoalHandle
from std_msgs.msg import String, Int32, Bool
from celikkubbe_msgs.msg import TargetInfo, MotorFeedback
from celikkubbe_msgs.srv import SetPhase
from celikkubbe_msgs.action import EngageTarget
import threading
import time
import json

class GorevDugumu(Node):
    def __init__(self):
        super().__init__('gorev_dugumu')
        
        # State Machine States
        self.STATES = [
            "BEKLE", "ARAYUZ_HAZIR", "ASAMA_TESPIT", "HEDEF_TAKIP", 
            "HEDEF_NISAN", "HEDEF_BEKLEME_KISA", "TARAMA_MODU", "IMHA_ONAY", "ATESLE", 
            "IMHA_BASARILI", "IMHA_IPTAL", "ASAMA_BASARILI"
        ]
        self.current_state = "BEKLE"
        self.current_phase = 0
        
        # Phase specific variables
        self.active_target = None
        self.motor_feedback = MotorFeedback()
        self.is_e_stop_active = False
        self.is_manual_mode = False
        
        self.target_lost_time = None
        self.SHORT_LOST_TIMEOUT = self.declare_parameter('timeout.short_lost_s', 1.0).value
        self.LONG_LOST_TIMEOUT = self.declare_parameter('timeout.long_lost_s', 10.0).value
        self.last_known_target = None
        
        self.nofire_zones = []
        
        # Publishers
        self.dogrulanmis_pub = self.create_publisher(TargetInfo, '/gorev/dogrulanmis_hedef', 10)
        self.durum_pub = self.create_publisher(String, '/gorev/durum', 10)
        
        # Subscribers
        self.hedef_sub = self.create_subscription(TargetInfo, '/tespit/hedef_bilgisi', self.hedef_callback, 10)
        self.motor_fb_sub = self.create_subscription(MotorFeedback, '/donanim/motor_geri_bildirim', self.motor_fb_callback, 10)
        self.estop_sub = self.create_subscription(Bool, '/arayuz/acil_dur', self.estop_callback, 10)
        self.operator_sub = self.create_subscription(String, '/arayuz/operator_komutu', self.operator_callback, 10)
        self.nfz_sub = self.create_subscription(String, '/arayuz/yasak_bolge', self.nfz_callback, 10)
        
        # Service & Action Servers
        self.phase_srv = self.create_service(SetPhase, '/gorev/asama_sec', self.handle_set_phase)
        self.engage_action = ActionServer(
            self,
            EngageTarget,
            '/gorev/hedefe_angaje_ol',
            execute_callback=self.execute_engage_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback
        )
        
        self.action_lock = threading.Lock()
        
        self.get_logger().info("Görev Node başlatıldı.")
        self.change_state("ARAYUZ_HAZIR")

    def change_state(self, new_state):
        if new_state in self.STATES:
            self.current_state = new_state
            msg = String()
            msg.data = self.current_state
            self.durum_pub.publish(msg)
            self.get_logger().info(f"State değişti: {new_state}")

    def nfz_callback(self, msg: String):
        try:
            self.nofire_zones = json.loads(msg.data)
        except Exception as e:
            self.get_logger().error(f"NFZ Parse Error: {e}")

    def estop_callback(self, msg: Bool):
        if msg.data:
            self.is_e_stop_active = True
            self.get_logger().warn("E-STOP AKTİF! Motorlar kilitlendi.")
            # Publish empty target to stop motors (or specific stop message if defined)
            empty_target = TargetInfo()
            empty_target.is_tracked = False
            self.dogrulanmis_pub.publish(empty_target)
            self.change_state("IMHA_IPTAL")
        else:
            self.is_e_stop_active = False

    def handle_set_phase(self, request, response):
        if request.phase in [1, 2, 3]:
            self.current_phase = request.phase
            self.target_lost_time = None
            self.last_known_target = None
            self.change_state("ASAMA_TESPIT")
            response.success = True
            response.message = f"Aşama {self.current_phase} seçildi."
            self.get_logger().info(response.message)
        else:
            response.success = False
            response.message = "Geçersiz aşama seçimi!"
        return response

    def motor_fb_callback(self, msg: MotorFeedback):
        self.motor_fb_callback_data = msg
        self.motor_feedback = msg

    def hedef_callback(self, msg: TargetInfo):
        if self.is_e_stop_active:
            return
        
        # --- Hedef kaybı yönetimi (Bariyer Arkası) ---
        if not msg.is_tracked:
            if self.target_lost_time is None:
                self.target_lost_time = time.time()
                
            elapsed = time.time() - self.target_lost_time
            
            if self.current_state in ["HEDEF_TAKIP", "HEDEF_NISAN"]:
                if elapsed >= self.LONG_LOST_TIMEOUT:
                    self.change_state("TARAMA_MODU")
                    self.last_known_target = None
                    self.target_lost_time = None
                    self.get_logger().info("Hedef uzun süre kayıp, taramaya geçiliyor.")
                elif elapsed >= self.SHORT_LOST_TIMEOUT:
                    if self.current_state != "TARAMA_MODU":
                        self.change_state("TARAMA_MODU")
                        self.get_logger().info("Bariyer arkası bekleme uzadı, tarama aranıyor.")
                else:
                    if self.current_state != "HEDEF_BEKLEME_KISA":
                        self.change_state("HEDEF_BEKLEME_KISA")
                        self.get_logger().info("Hedef geçici kayıp, taret bekliyor.")
            elif self.current_state in ["HEDEF_BEKLEME_KISA", "TARAMA_MODU"]:
                if elapsed >= self.LONG_LOST_TIMEOUT:
                    self.change_state("ASAMA_TESPIT")
                    self.last_known_target = None
                    self.target_lost_time = None
            return
        
        # Hedef var → sayacı sıfırla
        self.target_lost_time = None
        
        # Bekleme'den dönüş → eski state'e devam
        if self.current_state in ["HEDEF_BEKLEME_KISA", "TARAMA_MODU"]:
            self.change_state("HEDEF_TAKIP")
            self.get_logger().info("Hedef tekrar görüldü, takibe devam.")
        
        # Aktif state kontrolü
        if self.current_state not in ["ASAMA_TESPIT", "HEDEF_TAKIP", "HEDEF_NISAN", "ATESLE"]:
            return
        
        # --- Manuel mod: sadece görüntüle, PID'e gönderme ---
        if self.is_manual_mode:
            # Manuel modda hedef bilgisi sadece GUI'de gösterilir
            # Doğrulanmış hedef yayınlanmaz (PID devre dışı)
            self.active_target = msg
            return
        
        # --- Balon kontrolü (Vurulacak mı?) ---
        if not msg.has_balloon:
            # Balon yok → bu hedef zaten imha edilmiş veya geçersiz
            durum_msg = String()
            durum_msg.data = "BALON_YOK_ATLANDI"
            self.durum_pub.publish(durum_msg)
            return

        # --- No-Fire Zone (Atışa Yasak Bölge) Kontrolü ---
        for zone in self.nofire_zones:
            if (zone.get("x_min", 0) <= msg.aim_x <= zone.get("x_max", 0)) and \
               (zone.get("y_min", 0) <= msg.aim_y <= zone.get("y_max", 0)):
                durum_msg = String()
                durum_msg.data = "NFZ_ICINDE_ATLANDI"
                self.durum_pub.publish(durum_msg)
                return
        
        # --- Aşama mantığı ---
        if self.current_phase == 3:
            if msg.is_friendly:
                # Dost unsur atlandı
                durum_msg = String()
                durum_msg.data = "DOST_ATLANDI"
                self.durum_pub.publish(durum_msg)
                return
            # Düşman hedef → doğrula ve ilet
            self.active_target = msg
            self.last_known_target = msg
            self.dogrulanmis_pub.publish(msg)
            if self.current_state == "ASAMA_TESPIT":
                self.change_state("HEDEF_TAKIP")
                    
        elif self.current_phase == 2:
            # Sürü modunda her şey düşman
            self.active_target = msg
            self.last_known_target = msg
            self.dogrulanmis_pub.publish(msg)
            if self.current_state == "ASAMA_TESPIT":
                self.change_state("HEDEF_TAKIP")
                    
        elif self.current_phase == 1:
            self.active_target = msg
            self.last_known_target = msg
            self.dogrulanmis_pub.publish(msg)
                
    def operator_callback(self, msg: String):
        # Mod değişikliği komutları
        if msg.data == "mod_manuel":
            self.is_manual_mode = True
            self.get_logger().info("Manuel mod aktif — PID bypass.")
            return
        elif msg.data == "mod_otonom":
            self.is_manual_mode = False
            self.get_logger().info("Otonom mod aktif — PID kontrol.")
            return
        elif msg.data == "home":
            self.get_logger().info("Home pozisyonuna dönüş komutu alındı.")
            # Home komutu donanım düğümüne iletilir
            return
        
        # Operatör ateş komutu (Aşama 1)
        if msg.data == "ates_istegi" and self.current_phase == 1 and self.current_state in ["HEDEF_TAKIP", "HEDEF_NISAN"]:
            self.change_state("IMHA_ONAY")

    # Action Server Callbacks
    def goal_callback(self, goal_request):
        self.get_logger().info('Hedef angajman isteği alındı.')
        if self.is_e_stop_active:
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def cancel_callback(self, goal_handle):
        self.get_logger().info('Angajman iptal edildi.')
        self.change_state("IMHA_IPTAL")
        return CancelResponse.ACCEPT

    def execute_engage_callback(self, goal_handle: ServerGoalHandle):
        self.get_logger().info('Angajman başlatılıyor...')
        target = goal_handle.request.target
        feedback_msg = EngageTarget.Feedback()
        result = EngageTarget.Result()
        
        self.change_state("HEDEF_NISAN")
        
        # Simüle edilmiş hedef takip ve ateşleme döngüsü (gerçekte ROS timer/rate kullanılır)
        for i in range(50): # 5 saniye max
            if goal_handle.is_cancel_requested or self.is_e_stop_active:
                goal_handle.canceled()
                result.success = False
                result.result_message = "İptal edildi veya E-Stop!"
                return result
                
            # Feedback yayınla
            feedback_msg.status = "aiming" if i < 20 else "locked"
            feedback_msg.error_x = float(target.error_x) # Gerçekte anlık güncellenmeli
            feedback_msg.error_y = float(target.error_y)
            feedback_msg.estimated_range = self.motor_feedback.estimated_range
            goal_handle.publish_feedback(feedback_msg)
            
            # Ateşleme kararı
            if i == 30 and feedback_msg.status == "locked":
                # Check range based on phase 3 specs
                if self.current_phase == 3:
                     # Menzi kontrolü simülasyonu
                     pass
                     
                self.change_state("ATESLE")
                # Wait for firing sequence
                time.sleep(1.0)
                self.change_state("IMHA_BASARILI")
                result.success = True
                result.result_message = "Hedef başarıyla imha edildi."
                goal_handle.succeed()
                self.change_state("ASAMA_TESPIT") # Bir sonraki hedefe geç
                return result
                
            time.sleep(0.1)
            
        goal_handle.abort()
        result.success = False
        result.result_message = "Zaman aşımı!"
        self.change_state("IMHA_IPTAL")
        return result

def main(args=None):
    rclpy.init(args=args)
    node = GorevDugumu()
    
    # Use MultiThreadedExecutor for action server 
    from rclpy.executors import MultiThreadedExecutor
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
