import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, GoalResponse, CancelResponse
from rclpy.action.server import ServerGoalHandle
from std_msgs.msg import String, Int32, Bool
from celikubbe_msgs.msg import TargetInfo, MotorFeedback
from celikubbe_msgs.srv import SetPhase
from celikubbe_msgs.action import EngageTarget
import threading
import time

class GorevDugumu(Node):
    def __init__(self):
        super().__init__('gorev_dugumu')
        
        # State Machine States
        self.STATES = [
            "BEKLE", "ARAYUZ_HAZIR", "ASAMA_TESPIT", "HEDEF_TAKIP", 
            "HEDEF_NISAN", "IMHA_ONAY", "ATESLE", "IMHA_BASARILI", "IMHA_IPTAL", "ASAMA_BASARILI"
        ]
        self.current_state = "BEKLE"
        self.current_phase = 0
        self.score = 0
        
        # Phase specific variables
        self.active_target = None
        self.motor_feedback = MotorFeedback()
        self.is_e_stop_active = False
        
        # Publishers
        self.dogrulanmis_pub = self.create_publisher(TargetInfo, '/gorev/dogrulanmis_hedef', 10)
        self.durum_pub = self.create_publisher(String, '/gorev/durum', 10)
        self.puan_pub = self.create_publisher(Int32, '/gorev/puan', 10)
        
        # Subscribers
        self.hedef_sub = self.create_subscription(TargetInfo, '/tespit/hedef_bilgisi', self.hedef_callback, 10)
        self.motor_fb_sub = self.create_subscription(MotorFeedback, '/donanim/motor_geri_bildirim', self.motor_fb_callback, 10)
        self.estop_sub = self.create_subscription(Bool, '/arayuz/acil_dur', self.estop_callback, 10)
        self.operator_sub = self.create_subscription(String, '/arayuz/operator_komutu', self.operator_callback, 10)
        
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
            
    def update_score(self, points):
        self.score += points
        msg = Int32()
        msg.data = self.score
        self.puan_pub.publish(msg)

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
            self.score = 0
            self.update_score(0)
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
        # Aşama mantığına göre hedef filtreleme ve doğrulama
        if self.is_e_stop_active or self.current_state not in ["ASAMA_TESPIT", "HEDEF_TAKIP", "HEDEF_NISAN", "ATESLE"]:
            return
            
        if self.current_phase == 3:
            if msg.is_tracked and not msg.is_friendly:
                self.active_target = msg
                self.dogrulanmis_pub.publish(self.active_target)
                if self.current_state == "ASAMA_TESPIT":
                    self.change_state("HEDEF_TAKIP")
            elif msg.is_tracked and msg.is_friendly:
                # Dost atlandı
                durum_msg = String()
                durum_msg.data = "DOST_ATLANDI"
                self.durum_pub.publish(durum_msg)
                
        elif self.current_phase == 2:
            # Sürü modunda her şey düşman (örnek)
            if msg.is_tracked:
                self.active_target = msg
                self.dogrulanmis_pub.publish(self.active_target)
                if self.current_state == "ASAMA_TESPIT":
                    self.change_state("HEDEF_TAKIP")
                    
        elif self.current_phase == 1:
            if msg.is_tracked:
                self.active_target = msg
                self.dogrulanmis_pub.publish(self.active_target)
                
    def operator_callback(self, msg: String):
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
                
                # Puan simülasyonu
                points = 10
                if target.target_type == "f16": points = 30
                elif target.target_type == "helikopter" or target.target_type == "balistik_fuze": points = 15
                
                self.update_score(points)
                result.success = True
                result.points_earned = points
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
