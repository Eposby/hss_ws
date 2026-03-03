#!/usr/bin/env python3
"""
AŞAMA 3: FARKLI KATMANLARDAKİ HAREKETLİ HEDEFLERİN İMHASI

10 tur üzerinden gerçekleştirilir.
Her turda: 1 düşman hedef + 2 dost unsur yaklaşır.
Görev: Renk/şekil algılama ile düşmanı tespit edip, hedef tipine göre
uygun menzilde imha etmek.

Hedef Tipleri ve Menzilleri:
- F16: 10-15m
- Helikopter/Balistik Füze: 5-15m
- İHA/Mini-Micro İHA: 0-15m

Cezalar:
- Dost hedef vurma: 10 puan ceza (tur başına)
- 4 tur düşman vuramama: Aşamadan başarısız (0 puan)
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum


class TargetClass(Enum):
    """Hedef sınıfı (görsel özellikler)"""
    F16 = "f16"
    HELICOPTER = "helicopter"
    BALLISTIC_MISSILE = "ballistic"
    UAV = "uav"
    MINI_UAV = "mini_uav"


class Faction(Enum):
    """Hedef tarafı"""
    ENEMY = "enemy"
    FRIENDLY = "friendly"


# Hedef renk/şekil özellikleri (örnek)
TARGET_VISUAL_FEATURES = {
    TargetClass.F16: {"color": "gray", "shape": "jet"},
    TargetClass.HELICOPTER: {"color": "green", "shape": "rotor"},
    TargetClass.BALLISTIC_MISSILE: {"color": "white", "shape": "cylinder"},
    TargetClass.UAV: {"color": "black", "shape": "quad"},
    TargetClass.MINI_UAV: {"color": "red", "shape": "small_quad"},
}

# Hedef tiplerine göre uygun imha mesafeleri
OPTIMAL_RANGES = {
    TargetClass.F16: (10.0, 15.0),
    TargetClass.HELICOPTER: (5.0, 15.0),
    TargetClass.BALLISTIC_MISSILE: (5.0, 15.0),
    TargetClass.UAV: (0.0, 15.0),
    TargetClass.MINI_UAV: (0.0, 15.0),
}


@dataclass
class MovingTarget:
    """Hareketli hedef"""
    id: int
    target_class: TargetClass
    faction: Faction
    position: Tuple[float, float, float]  # x, y, z
    distance: float                        # Sisteme mesafe
    color: str                             # Renk
    shape: str                             # Şekil
    is_destroyed: bool = False
    is_identified: bool = False            # Tanımlandı mı (dost/düşman)
    
    def get_optimal_range(self) -> Tuple[float, float]:
        """Uygun imha menzilini döndür"""
        return OPTIMAL_RANGES.get(self.target_class, (0.0, 15.0))
    
    def is_in_optimal_range(self) -> bool:
        """Uygun menzilde mi kontrol et"""
        min_r, max_r = self.get_optimal_range()
        return min_r <= self.distance <= max_r


@dataclass
class Stage3Context:
    """Aşama 3 için context verileri"""
    current_round: int = 1                                    # Mevcut tur
    max_rounds: int = 10                                      # Maksimum tur (10)
    enemy_target: Optional[MovingTarget] = None               # Bu turdaki düşman
    friendly_targets: List[MovingTarget] = field(default_factory=list)  # Dost hedefler
    all_targets: List[MovingTarget] = field(default_factory=list)       # Tüm hedefler
    
    # İstatistikler
    enemies_destroyed: int = 0                                # Vurulan düşman sayısı
    friendlies_hit: int = 0                                   # Vurulan dost sayısı
    rounds_without_enemy_hit: int = 0                         # Düşman vurulamayan tur sayısı
    consecutive_misses: int = 0                               # Ardışık kaçırma (4'te fail)
    
    score: int = 0                                            # Toplam puan
    penalty: int = 0                                          # Ceza puanları
    is_failed: bool = False                                   # Aşama başarısız mı
    
    # Tanımlama
    identified_enemy: Optional[MovingTarget] = None           # Tanımlanan düşman


# ============================================================================
# STATE FUNCTIONS
# ============================================================================

def execute_detecting(context: Dict[str, Any]) -> Optional[str]:
    """
    STAGE3_DETECTING: Hedefleri tespit et
    
    Renk ve şekil algılama ile tüm hedefleri tespit eder.
    
    Returns:
        Sonraki state adı veya None
    """
    stage3_ctx = context.get('stage3', Stage3Context())
    
    # Başarısızlık kontrolü
    if stage3_ctx.is_failed:
        print("[AŞAMA 3] BAŞARISIZ - 4 tur düşman vurulamadı!")
        return 'ERROR'
    
    print(f"\n{'='*50}")
    print(f"[AŞAMA 3 - TESPİT] Tur {stage3_ctx.current_round}/{stage3_ctx.max_rounds}")
    print(f"{'='*50}")
    
    # Hedef tespiti (renk/şekil algılama)
    detected_targets = _detect_targets(context)
    
    if detected_targets:
        stage3_ctx.all_targets = detected_targets
        
        print(f"  {len(detected_targets)} hedef tespit edildi:")
        for target in detected_targets:
            print(f"    - Renk: {target.color}, Şekil: {target.shape}, Mesafe: {target.distance:.1f}m")
        
        context['stage3'] = stage3_ctx
        return 'STAGE3_CLASSIFYING'
    
    print("  Hedef bekleniyor...")
    return None


def execute_classifying(context: Dict[str, Any]) -> Optional[str]:
    """
    STAGE3_CLASSIFYING: Dost/Düşman sınıflandırması
    
    Tespit edilen hedefleri renk ve şekil özelliklerine göre sınıflandırır.
    
    Returns:
        Sonraki state adı veya None
    """
    stage3_ctx = context.get('stage3', Stage3Context())
    
    print("[AŞAMA 3 - SINIFLANDIRMA] Hedefler analiz ediliyor...")
    
    enemy = None
    friendlies = []
    
    for target in stage3_ctx.all_targets:
        # Sınıflandırma algoritması (renk/şekil bazlı)
        faction = _classify_target(target)
        target.faction = faction
        target.is_identified = True
        
        if faction == Faction.ENEMY:
            enemy = target
            print(f"  🔴 DÜŞMAN TESPİT: {target.target_class.value}")
            print(f"     Renk: {target.color}, Şekil: {target.shape}")
        else:
            friendlies.append(target)
            print(f"  🟢 DOST TESPİT: {target.target_class.value}")
    
    stage3_ctx.enemy_target = enemy
    stage3_ctx.friendly_targets = friendlies
    stage3_ctx.identified_enemy = enemy
    
    if enemy:
        min_r, max_r = enemy.get_optimal_range()
        print(f"\n  → Düşman için uygun imha mesafesi: {min_r}-{max_r}m")
        print(f"  → Mevcut mesafe: {enemy.distance:.1f}m")
        context['stage3'] = stage3_ctx
        return 'STAGE3_ENGAGING_ENEMY'
    else:
        print("  ⚠ Düşman hedef tespit edilemedi!")
        context['stage3'] = stage3_ctx
        return 'STAGE3_DETECTING'


def execute_engaging_enemy(context: Dict[str, Any]) -> Optional[str]:
    """
    STAGE3_ENGAGING_ENEMY: Düşmana angaje ol
    
    Tanımlanan düşman hedefe, hedef tipine uygun menzilde angaje olur.
    
    Returns:
        Sonraki state adı veya None
    """
    stage3_ctx = context.get('stage3', Stage3Context())
    
    enemy = stage3_ctx.identified_enemy
    
    if not enemy:
        print("[AŞAMA 3 - ANGAJE] HATA: Düşman hedef yok!")
        return 'STAGE3_DETECTING'
    
    print(f"[AŞAMA 3 - ANGAJE] {enemy.target_class.value} hedefine angaje!")
    
    # Menzil kontrolü
    if not enemy.is_in_optimal_range():
        min_r, max_r = enemy.get_optimal_range()
        print(f"  ⏳ Hedef menzil dışında ({enemy.distance:.1f}m)")
        print(f"     Beklenen menzil: {min_r}-{max_r}m")
        
        # Hedef pozisyonunu güncelle
        _update_target_position(enemy)
        
        if enemy.distance < 0:
            # Hedef geçti, kaçırıldı
            print(f"  ✗ HEDEF KAÇIRILDI!")
            return 'STAGE3_VERIFYING'
        
        return None  # Bekle
    
    print(f"  ✓ Hedef menzilde! Ateş açılıyor...")
    
    # Ateş et
    hit = _fire_at_target(context, enemy)
    
    context['stage3'] = stage3_ctx
    return 'STAGE3_VERIFYING'


def execute_verifying(context: Dict[str, Any]) -> Optional[str]:
    """
    STAGE3_VERIFYING: İmhayı doğrula
    
    Atışın sonucunu değerlendirir (dost mu düşman mı vuruldu).
    
    Returns:
        Sonraki state adı veya None
    """
    stage3_ctx = context.get('stage3', Stage3Context())
    
    print("[AŞAMA 3 - DOĞRULAMA] Atış sonucu kontrol ediliyor...")
    
    # Son atış sonucunu al
    hit_result = context.get('last_hit_result', None)
    hit_target = context.get('last_hit_target', None)
    
    enemy_hit_this_round = False
    friendly_hit_this_round = False
    
    if hit_result and hit_target:
        if hit_target.faction == Faction.ENEMY:
            enemy_hit_this_round = True
            stage3_ctx.enemies_destroyed += 1
            
            # Puanlama
            points = _calculate_stage3_points(hit_target)
            stage3_ctx.score += points
            
            print(f"  ✓ DÜŞMAN İMHA EDİLDİ!")
            print(f"  + {points} puan (Toplam: {stage3_ctx.score})")
            
            # Ardışık kaçırma sıfırla
            stage3_ctx.consecutive_misses = 0
            
        elif hit_target.faction == Faction.FRIENDLY:
            friendly_hit_this_round = True
            stage3_ctx.friendlies_hit += 1
            stage3_ctx.penalty += 10
            
            print(f"  ⚠ DOST UNSUR VURULDU!")
            print(f"  - 10 ceza puanı (Toplam ceza: {stage3_ctx.penalty})")
    
    # Düşman bu turda vurulmadı mı?
    if not enemy_hit_this_round:
        stage3_ctx.rounds_without_enemy_hit += 1
        stage3_ctx.consecutive_misses += 1
        
        print(f"  ✗ Bu turda düşman vurulamadı!")
        print(f"  Ardışık kaçırma: {stage3_ctx.consecutive_misses}/4")
        
        # 4 ardışık kaçırma = başarısız
        if stage3_ctx.consecutive_misses >= 4:
            stage3_ctx.is_failed = True
            stage3_ctx.score = 0
            print(f"\n  ❌ AŞAMA BAŞARISIZ! 4 tur ardışık düşman vurulamadı!")
    
    context['stage3'] = stage3_ctx
    return 'STAGE3_ROUND_COMPLETE'


def execute_round_complete(context: Dict[str, Any]) -> Optional[str]:
    """
    STAGE3_ROUND_COMPLETE: Tur tamamlandı
    
    Tur sonuçlarını değerlendirir ve bir sonraki tura geçer.
    
    Returns:
        Sonraki state adı veya None
    """
    stage3_ctx = context.get('stage3', Stage3Context())
    
    print(f"\n{'='*50}")
    print(f"[AŞAMA 3] TUR {stage3_ctx.current_round} TAMAMLANDI")
    print(f"  Düşman vurma: {stage3_ctx.enemies_destroyed}")
    print(f"  Dost vurma: {stage3_ctx.friendlies_hit}")
    print(f"  Skor: {stage3_ctx.score} | Ceza: {stage3_ctx.penalty}")
    print(f"  Net: {stage3_ctx.score - stage3_ctx.penalty}")
    print(f"{'='*50}\n")
    
     # Başarısız kontrolü
    if stage3_ctx.is_failed:
        print("[AŞAMA 3] BAŞARISIZ!")
        return 'ERROR'
    
    # Sonraki tur hazırlığı
    stage3_ctx.current_round += 1
    stage3_ctx.enemy_target = None
    stage3_ctx.friendly_targets = []
    stage3_ctx.all_targets = []
    stage3_ctx.identified_enemy = None
    
    if stage3_ctx.current_round > stage3_ctx.max_rounds:
        print("[AŞAMA 3] TÜM TURLAR TAMAMLANDI!")
        print(f"  Final Skor: {stage3_ctx.score}")
        print(f"  Toplam Ceza: {stage3_ctx.penalty}")
        print(f"  Net Skor: {stage3_ctx.score - stage3_ctx.penalty}")
        context['stage3'] = stage3_ctx
        return 'COMPLETED'
    
    context['stage3'] = stage3_ctx
    return 'STAGE3_DETECTING'


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _detect_targets(context: Dict[str, Any]) -> List[MovingTarget]:
    """
    Hedefleri tespit et (renk/şekil algılama).
    
    Gerçek implementasyonda kamera + görüntü işleme kullanılacak.
    """
    # TODO: Gerçek hedef tespiti
    # - Kamera görüntüsü al
    # - Renk filtresi uygula
    # - Şekil tespiti (contour analizi)
    # - Hedef sınıflandırma
    return []


def _classify_target(target: MovingTarget) -> Faction:
    """
    Hedefi dost/düşman olarak sınıflandır.
    
    Renk ve şekil özelliklerine göre karar verir.
    """
    # TODO: Gerçek sınıflandırma algoritması
    # Örnek: Kırmızı = düşman, Yeşil/Mavi = dost
    
    enemy_colors = ["red", "orange", "gray"]
    friendly_colors = ["green", "blue", "white"]
    
    if target.color.lower() in enemy_colors:
        return Faction.ENEMY
    elif target.color.lower() in friendly_colors:
        return Faction.FRIENDLY
    else:
        # Varsayılan: Bilinmeyen = dikkatli ol
        return Faction.FRIENDLY


def _update_target_position(target: MovingTarget) -> None:
    """
    Hedef pozisyonunu güncelle (hareket simülasyonu).
    """
    # Hedef yaklaşıyor
    target.distance -= 0.5  # Her döngüde 0.5m yaklaşma


def _fire_at_target(context: Dict[str, Any], target: MovingTarget) -> bool:
    """
    Hedefe ateş et.
    
    Returns:
        True: İsabet, False: Iskalama
    """
    # TODO: Gerçek ateşleme implementasyonu
    
    # Simülasyon için isabet varsay
    target.is_destroyed = True
    context['last_hit_result'] = True
    context['last_hit_target'] = target
    
    return True


def _calculate_stage3_points(target: MovingTarget) -> int:
    """
    Aşama 3 için puan hesapla.
    
    Hedef tipine ve menzile göre puanlama.
    """
    base_points = {
        TargetClass.F16: 30,
        TargetClass.HELICOPTER: 25,
        TargetClass.BALLISTIC_MISSILE: 25,
        TargetClass.UAV: 20,
        TargetClass.MINI_UAV: 15,
    }
    
    points = base_points.get(target.target_class, 10)
    
    # Optimal menzil bonusu
    if target.is_in_optimal_range():
        points += 5
    
    return points


# ============================================================================
# STATE DISPATCHER
# ============================================================================

def execute(context: Dict[str, Any]) -> Optional[str]:
    """
    Aşama 3 state dispatcher.
    
    Mevcut state'e göre uygun fonksiyonu çağırır.
    """
    from . import State
    
    current_state = context.get('current_state', State.IDLE)
    
    state_handlers = {
        State.STAGE3_DETECTING: execute_detecting,
        State.STAGE3_CLASSIFYING: execute_classifying,
        State.STAGE3_ENGAGING_ENEMY: execute_engaging_enemy,
        State.STAGE3_VERIFYING: execute_verifying,
        State.STAGE3_ROUND_COMPLETE: execute_round_complete,
    }
    
    handler = state_handlers.get(current_state)
    if handler:
        return handler(context)
    
    return None


def get_stage3_results(context: Dict[str, Any]) -> Dict[str, Any]:
    """Aşama 3 sonuçlarını döndür"""
    stage3_ctx = context.get('stage3', Stage3Context())
    return {
        'score': stage3_ctx.score,
        'penalty': stage3_ctx.penalty,
        'net_score': stage3_ctx.score - stage3_ctx.penalty,
        'enemies_destroyed': stage3_ctx.enemies_destroyed,
        'friendlies_hit': stage3_ctx.friendlies_hit,
        'rounds_completed': stage3_ctx.current_round - 1,
        'is_failed': stage3_ctx.is_failed,
    }
