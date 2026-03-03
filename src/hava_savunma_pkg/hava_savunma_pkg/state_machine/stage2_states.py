#!/usr/bin/env python3
"""
AŞAMA 2: SÜRÜ SALDIRISI VE İMHASI

Sürü saldırısı 3 farklı koldan hedeflerin önceden tanımlı bir yol üzerinde
sistemlerine yaklaşacak şekilde gerçekleşecektir. Yarışmacı sistemlerin bu
hedefleri belirli bir mesafeden önce imha etmeleri gerekmektedir.

Hedef Türleri: Balistik Füze, İHA, Mini/Micro İHA

Tur Mantığı:
- Hedefler A noktasından B noktasına hareket eder (1 tam tur)
- Her tur başında tüm hedefler parkurda olur
- Tur tamamlandığında imha edilen hedef yerine yenisi konulur
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum


class Lane(Enum):
    """Saldırı kolları"""
    LEFT = "left"      # Sol kol
    CENTER = "center"  # Orta kol
    RIGHT = "right"    # Sağ kol


@dataclass
class SwarmTarget:
    """Sürü hedefi"""
    id: int
    target_type: str  # "ballistic_missile", "uav", "mini_uav"
    lane: Lane        # Hangi koldan geliyor
    position: Tuple[float, float, float]  # x, y, z
    distance: float   # Sisteme mesafe
    speed: float      # Hız (m/s)
    is_destroyed: bool = False
    is_passed: bool = False  # Kritik mesafeyi geçti mi


@dataclass
class Stage2Context:
    """Aşama 2 için context verileri"""
    current_round: int = 1                                    # Mevcut tur
    max_rounds: int = 5                                       # Maksimum tur sayısı
    targets: List[SwarmTarget] = field(default_factory=list)  # Aktif hedefler
    destroyed_this_round: int = 0                             # Bu turda imha edilen
    total_destroyed: int = 0                                  # Toplam imha edilen
    missed_targets: int = 0                                   # Kaçırılan hedefler
    score: int = 0                                            # Toplam puan
    critical_distance: float = 5.0                            # Kritik mesafe (m)
    priority_target: Optional[SwarmTarget] = None             # Öncelikli hedef
    is_round_active: bool = False                             # Tur aktif mi


# ============================================================================
# STATE FUNCTIONS
# ============================================================================

def execute_scanning(context: Dict[str, Any]) -> Optional[str]:
    """
    STAGE2_SCANNING: 3 koldan yaklaşan hedefleri tara
    
    Tüm kolları tarar ve yaklaşan hedefleri tespit eder.
    
    Returns:
        Sonraki state adı veya None
    """
    stage2_ctx = context.get('stage2', Stage2Context())
    
    print(f"[AŞAMA 2 - TARAMA] Tur {stage2_ctx.current_round}/{stage2_ctx.max_rounds}")
    print("  Hedefler taranıyor...")
    
    # Hedef tespiti (gerçek implementasyonda kamera + görüntü işleme)
    detected_targets = _scan_for_targets(context)
    
    if detected_targets:
        stage2_ctx.targets = detected_targets
        stage2_ctx.is_round_active = True
        
        print(f"  {len(detected_targets)} hedef tespit edildi:")
        for target in detected_targets:
            print(f"    - [{target.lane.value}] {target.target_type} @ {target.distance:.1f}m")
        
        context['stage2'] = stage2_ctx
        return 'STAGE2_TRACKING'
    
    # Hedef yok, taramaya devam
    return None


def execute_tracking(context: Dict[str, Any]) -> Optional[str]:
    """
    STAGE2_TRACKING: Hedefleri takip et
    
    Tespit edilen hedeflerin pozisyonlarını günceller.
    
    Returns:
        Sonraki state adı veya None
    """
    stage2_ctx = context.get('stage2', Stage2Context())
    
    print("[AŞAMA 2 - TAKİP] Hedefler takip ediliyor...")
    
    # Hedef pozisyonlarını güncelle
    _update_target_positions(context)
    
    # Kritik mesafeyi geçen hedef var mı kontrol et
    for target in stage2_ctx.targets:
        if not target.is_destroyed and target.distance < stage2_ctx.critical_distance:
            if not target.is_passed:
                target.is_passed = True
                stage2_ctx.missed_targets += 1
                print(f"  ⚠ HEDEF KAÇIRILDI: {target.target_type} kritik mesafeyi geçti!")
    
    # Aktif hedef kaldı mı?
    active_targets = [t for t in stage2_ctx.targets if not t.is_destroyed and not t.is_passed]
    
    if not active_targets:
        print("  Tüm hedefler işlendi, tur tamamlanıyor...")
        context['stage2'] = stage2_ctx
        return 'STAGE2_ROUND_COMPLETE'
    
    context['stage2'] = stage2_ctx
    return 'STAGE2_PRIORITIZING'


def execute_prioritizing(context: Dict[str, Any]) -> Optional[str]:
    """
    STAGE2_PRIORITIZING: Öncelikli hedefi belirle
    
    En yakın veya en tehlikeli hedefi seçer.
    
    Returns:
        Sonraki state adı veya None
    """
    stage2_ctx = context.get('stage2', Stage2Context())
    
    print("[AŞAMA 2 - ÖNCELİK] Hedef önceliklendiriliyor...")
    
    # Aktif hedefleri filtrele
    active_targets = [t for t in stage2_ctx.targets if not t.is_destroyed and not t.is_passed]
    
    if not active_targets:
        return 'STAGE2_ROUND_COMPLETE'
    
    # Önceliklendirme algoritması
    priority_target = _calculate_priority(active_targets)
    stage2_ctx.priority_target = priority_target
    
    print(f"  → Öncelikli hedef: {priority_target.target_type}")
    print(f"    Kol: {priority_target.lane.value}")
    print(f"    Mesafe: {priority_target.distance:.1f}m")
    
    context['stage2'] = stage2_ctx
    return 'STAGE2_ENGAGING'


def execute_engaging(context: Dict[str, Any]) -> Optional[str]:
    """
    STAGE2_ENGAGING: Hedefe angaje ol
    
    Seçilen öncelikli hedefe angaje olur ve ateş eder.
    
    Returns:
        Sonraki state adı veya None
    """
    stage2_ctx = context.get('stage2', Stage2Context())
    
    if not stage2_ctx.priority_target:
        return 'STAGE2_SCANNING'
    
    target = stage2_ctx.priority_target
    
    print(f"[AŞAMA 2 - ANGAJE] {target.target_type} hedefine angaje!")
    
    # Nişan al ve ateş et
    if _engage_target(context, target):
        target.is_destroyed = True
        stage2_ctx.destroyed_this_round += 1
        stage2_ctx.total_destroyed += 1
        
        # Puanlama
        points = _calculate_swarm_points(target)
        stage2_ctx.score += points
        
        print(f"  ✓ HEDEF İMHA EDİLDİ!")
        print(f"  + {points} puan (Toplam: {stage2_ctx.score})")
    else:
        print(f"  ✗ Iskalandı, hedef takibe devam...")
    
    stage2_ctx.priority_target = None
    context['stage2'] = stage2_ctx
    
    # Daha fazla aktif hedef var mı?
    active_targets = [t for t in stage2_ctx.targets if not t.is_destroyed and not t.is_passed]
    
    if active_targets:
        return 'STAGE2_TRACKING'
    else:
        return 'STAGE2_ROUND_COMPLETE'


def execute_round_complete(context: Dict[str, Any]) -> Optional[str]:
    """
    STAGE2_ROUND_COMPLETE: Tur tamamlandı
    
    Tur sonuçlarını değerlendirir ve bir sonraki tura geçer.
    
    Returns:
        Sonraki state adı veya None
    """
    stage2_ctx = context.get('stage2', Stage2Context())
    
    print(f"\n{'='*50}")
    print(f"[AŞAMA 2] TUR {stage2_ctx.current_round} TAMAMLANDI")
    print(f"  İmha: {stage2_ctx.destroyed_this_round}")
    print(f"  Kaçırılan: {len([t for t in stage2_ctx.targets if t.is_passed])}")
    print(f"  Tur Skoru: {stage2_ctx.score}")
    print(f"{'='*50}\n")
    
    # Sonraki tur hazırlığı
    stage2_ctx.current_round += 1
    stage2_ctx.destroyed_this_round = 0
    stage2_ctx.targets = []
    stage2_ctx.is_round_active = False
    
    if stage2_ctx.current_round > stage2_ctx.max_rounds:
        print("[AŞAMA 2] TÜM TURLAR TAMAMLANDI!")
        print(f"  Final Skor: {stage2_ctx.score}")
        print(f"  Toplam İmha: {stage2_ctx.total_destroyed}")
        context['stage2'] = stage2_ctx
        return 'COMPLETED'
    
    context['stage2'] = stage2_ctx
    return 'STAGE2_SCANNING'


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _scan_for_targets(context: Dict[str, Any]) -> List[SwarmTarget]:
    """
    Hedefleri tara ve tespit et.
    
    Gerçek implementasyonda kamera görüntü işleme kullanılacak.
    """
    # TODO: Gerçek hedef tespiti
    # - 3 kamera ile 3 kol tarama
    # - Görüntü işleme ile hedef tespiti
    # - Hedef türü sınıflandırma
    
    # Simülasyon için boş liste
    return []


def _update_target_positions(context: Dict[str, Any]) -> None:
    """
    Hedef pozisyonlarını güncelle.
    
    Hedeflerin hareketini takip eder, mesafeleri günceller.
    """
    stage2_ctx = context.get('stage2', Stage2Context())
    
    for target in stage2_ctx.targets:
        if not target.is_destroyed and not target.is_passed:
            # Hedef yaklaşıyor (simülasyon)
            target.distance -= target.speed * 0.1  # 100ms için


def _calculate_priority(targets: List[SwarmTarget]) -> SwarmTarget:
    """
    Hedef önceliklendirme algoritması.
    
    Öncelik kriterleri:
    1. En yakın hedef (mesafe)
    2. Hedef tipi tehlike seviyesi
    3. Hız
    """
    # Basit algoritma: En yakın hedef
    return min(targets, key=lambda t: t.distance)


def _engage_target(context: Dict[str, Any], target: SwarmTarget) -> bool:
    """
    Hedefe angaje ol ve ateş et.
    
    Returns:
        True: İsabet, False: Iskalama
    """
    # TODO: Gerçek angaje implementasyonu
    # - Hedef takibi
    # - Nişan alma
    # - Ateşleme
    # - İsabet kontrolü
    return True


def _calculate_swarm_points(target: SwarmTarget) -> int:
    """
    Sürü hedefi için puan hesapla.
    
    Hedef tipine ve imha mesafesine göre puan.
    """
    base_points = {
        "ballistic_missile": 25,
        "uav": 20,
        "mini_uav": 15,
    }
    
    points = base_points.get(target.target_type, 10)
    
    # Mesafe bonusu
    if target.distance > 10:
        points += 5  # Uzaktan imha bonusu
    
    return points


# ============================================================================
# STATE DISPATCHER
# ============================================================================

def execute(context: Dict[str, Any]) -> Optional[str]:
    """
    Aşama 2 state dispatcher.
    
    Mevcut state'e göre uygun fonksiyonu çağırır.
    """
    from . import State
    
    current_state = context.get('current_state', State.IDLE)
    
    state_handlers = {
        State.STAGE2_SCANNING: execute_scanning,
        State.STAGE2_TRACKING: execute_tracking,
        State.STAGE2_PRIORITIZING: execute_prioritizing,
        State.STAGE2_ENGAGING: execute_engaging,
        State.STAGE2_ROUND_COMPLETE: execute_round_complete,
    }
    
    handler = state_handlers.get(current_state)
    if handler:
        return handler(context)
    
    return None


def get_stage2_results(context: Dict[str, Any]) -> Dict[str, Any]:
    """Aşama 2 sonuçlarını döndür"""
    stage2_ctx = context.get('stage2', Stage2Context())
    return {
        'score': stage2_ctx.score,
        'total_destroyed': stage2_ctx.total_destroyed,
        'missed_targets': stage2_ctx.missed_targets,
        'rounds_completed': stage2_ctx.current_round - 1,
    }
