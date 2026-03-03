#!/usr/bin/env python3
"""
Teknofest Hava Savunma Sistemi - State Machine
3 Aşamalı Yarışma için State Tanımlamaları
"""



"""
# __init__.py OLMADAN bu çalışmaz:
from state_machine import State
"""


"""

Tanım	Açıklama
CompetitionStage
Yarışma aşamaları (STAGE_1, STAGE_2, STAGE_3)
TargetType
Hedef tipleri (F16, UAV, MINI_UAV, vb.)
TargetFaction
Hedef tarafı (ENEMY, FRIENDLY)
Target
Hedef veri sınıfı (konum, mesafe, menzil)
State
Tüm state'ler (IDLE, STAGE1_AIMING, STAGE2_SCANNING, vb.)

"""


"""

# Diğer dosyalardan import
from state_machine import State, Target, TargetType, TargetFaction

# Bir hedef oluştur
target = Target(
    id=1,
    target_type=TargetType.F16,
    faction=TargetFaction.ENEMY,
    position=(10.0, 5.0, 2.0),
    distance=12.0
)

# Menzil kontrolü
if target.is_in_range():
    print("Hedef menzilde!")

"""




from enum import Enum
from dataclasses import dataclass
from typing import Optional, Tuple


class CompetitionStage(Enum):
    """Yarışma aşamaları"""
    STAGE_1 = "stage1"  # Durağan Hedef İmhası
    STAGE_2 = "stage2"  # Sürü Saldırısı
    STAGE_3 = "stage3"  # Hareketli Hedefler


class TargetType(Enum):
    """Hedef tipleri"""
    F16 = "f16"
    HELICOPTER = "helicopter"
    BALLISTIC_MISSILE = "ballistic_missile"
    UAV = "uav"  # İHA
    MINI_UAV = "mini_uav"  # Mini/Micro İHA
    UNKNOWN = "unknown"


class TargetFaction(Enum):
    """Hedef tarafı"""
    ENEMY = "enemy"     # Düşman
    FRIENDLY = "friendly"  # Dost


@dataclass
class Target:
    """Hedef veri sınıfı"""
    id: int
    target_type: TargetType
    faction: TargetFaction
    position: Tuple[float, float, float]  # x, y, z koordinatları
    distance: float  # Sistem mesafesi (metre)
    is_destroyed: bool = False
    
    def get_optimal_range(self) -> Tuple[float, float]:
        """Hedef tipine göre uygun imha mesafesini döndür"""
        ranges = {
            TargetType.F16: (10.0, 15.0),
            TargetType.HELICOPTER: (5.0, 15.0),
            TargetType.BALLISTIC_MISSILE: (5.0, 15.0),
            TargetType.UAV: (0.0, 15.0),
            TargetType.MINI_UAV: (0.0, 15.0),
            TargetType.UNKNOWN: (0.0, 15.0),
        }
        return ranges.get(self.target_type, (0.0, 15.0))
    
    def is_in_range(self) -> bool:
        """Hedefin uygun imha menzilinde olup olmadığını kontrol et"""
        min_range, max_range = self.get_optimal_range()
        return min_range <= self.distance <= max_range


class State(Enum):
    """Sistem durumları - Tüm aşamalar için"""
    
    # ===== GENEL STATE'LER =====
    IDLE = "idle"                       # Bekleme
    INITIALIZING = "initializing"       # Başlatılıyor
    READY = "ready"                     # Hazır
    COMPLETED = "completed"             # Tamamlandı
    ERROR = "error"                     # Hata
    
    # ===== AŞAMA 1: DURAĞAN HEDEF İMHASI =====
    STAGE1_WAITING_ORDER = "stage1_waiting_order"   # Hedef sırasını bekle
    STAGE1_AIMING = "stage1_aiming"                 # Nişan al
    STAGE1_FIRING = "stage1_firing"                 # Ateş et
    STAGE1_VERIFYING = "stage1_verifying"           # İmhayı doğrula
    STAGE1_NEXT_TARGET = "stage1_next_target"       # Sıradaki hedefe geç
    
    # ===== AŞAMA 2: SÜRÜ SALDIRISI =====
    STAGE2_SCANNING = "stage2_scanning"             # Hedefleri tara
    STAGE2_TRACKING = "stage2_tracking"             # Takip et
    STAGE2_PRIORITIZING = "stage2_prioritizing"     # Öncelik belirle
    STAGE2_ENGAGING = "stage2_engaging"             # Angaje ol
    STAGE2_ROUND_COMPLETE = "stage2_round_complete" # Tur tamamlandı
    
    # ===== AŞAMA 3: HAREKETLİ HEDEFLER =====
    STAGE3_DETECTING = "stage3_detecting"           # Hedefleri tespit et
    STAGE3_CLASSIFYING = "stage3_classifying"       # Dost/Düşman sınıflandır
    STAGE3_ENGAGING_ENEMY = "stage3_engaging_enemy" # Düşmana angaje ol
    STAGE3_VERIFYING = "stage3_verifying"           # İmhayı doğrula
    STAGE3_ROUND_COMPLETE = "stage3_round_complete" # Tur tamamlandı
    
    # ===== ESKİ STATE'LER (geriye uyumluluk) =====
    SCANNING = "scanning"   # Tarama/Tespit
    DETECTED = "detected"   # Balon bulundu
