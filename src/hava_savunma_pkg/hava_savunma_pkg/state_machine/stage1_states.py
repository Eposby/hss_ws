#!/usr/bin/env python3
"""
AŞAMA 1: FARKLI MENZİLLERDE DURAN HEDEF İMHASI

Hedefler sistemden yaklaşık 5-10-15 metre uzaklıkta yer alacaktır.
Hedefler durağan olacaktır. 5 farklı hedefin imha sırası yarışma öncesinde
hazırlık aşaması tamamlanınca yarışmacı takıma bir zarf ile verilecektir.

Ceza: Yanlış sıradaki bir hedefin imha edilmesi = 5 ceza puanı
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class Stage1Context:
    """Aşama 1 için context verileri"""
    target_order: List[int] = field(default_factory=list)    # Zarf ile verilen sıra [1, 3, 2, 5, 4]
    current_target_index: int = 0                             # Şu anki hedef indeksi
    destroyed_targets: List[int] = field(default_factory=list)  # İmha edilen hedefler
    target_positions: Dict[int, tuple] = field(default_factory=dict)  # Hedef ID -> (x, y, z)
    target_distances: Dict[int, float] = field(default_factory=dict)  # Hedef ID -> mesafe (5, 10, 15m)
    score: int = 0                                            # Toplam puan
    penalty: int = 0                                          # Ceza puanları
    is_target_locked: bool = False                            # Hedef kilitli mi
    last_shot_hit: bool = False                               # Son atış isabet etti mi


# ============================================================================
# STATE FUNCTIONS
# ============================================================================

def execute_waiting_order(context: Dict[str, Any]) -> Optional[str]:
    """
    STAGE1_WAITING_ORDER: Hedef sırasını bekle
    
    Zarf açılana kadar bekler. Hedef sırası context'e girildiğinde
    bir sonraki state'e geçer.
    
    Returns:
        Sonraki state adı veya None
    """
    stage1_ctx = context.get('stage1', Stage1Context())
    
    print("[AŞAMA 1 - BEKLEME] Hedef sırası bekleniyor...")
    
    # Hedef sırası verildi mi kontrol et
    if stage1_ctx.target_order and len(stage1_ctx.target_order) > 0:
        print(f"[AŞAMA 1] Hedef sırası alındı: {stage1_ctx.target_order}")
        context['stage1'] = stage1_ctx
        return 'STAGE1_AIMING'
    
    return None  # Bekle


def execute_aiming(context: Dict[str, Any]) -> Optional[str]:
    """
    STAGE1_AIMING: Sıradaki hedefe nişan al
    
    Hedef sırasına göre bir sonraki hedefe yönelir ve kilitlenir.
    
    Returns:
        Sonraki state adı veya None
    """
    stage1_ctx = context.get('stage1', Stage1Context())
    
    # Tüm hedefler imha edildi mi?
    if stage1_ctx.current_target_index >= len(stage1_ctx.target_order):
        print("[AŞAMA 1] Tüm hedefler imha edildi!")
        return 'COMPLETED'
    
    current_target_id = stage1_ctx.target_order[stage1_ctx.current_target_index]
    target_distance = stage1_ctx.target_distances.get(current_target_id, 10)
    
    print(f"[AŞAMA 1 - NİŞAN] Hedef #{current_target_id} | Mesafe: {target_distance}m")
    print(f"  Sıra: {stage1_ctx.current_target_index + 1}/{len(stage1_ctx.target_order)}")
    
    # Nişan alma işlemi (burada gerçek servo/gimbal kontrolü olacak)
    # Simülasyon için doğrudan kilitleme
    if _aim_at_target(context, current_target_id):
        stage1_ctx.is_target_locked = True
        context['stage1'] = stage1_ctx
        print(f"  ✓ Hedef #{current_target_id} KİLİTLENDİ")
        return 'STAGE1_FIRING'
    
    # Hedef henüz kilitlenmedi
    return None


def execute_firing(context: Dict[str, Any]) -> Optional[str]:
    """
    STAGE1_FIRING: Ateş et
    
    Kilitli hedefe ateş eder.
    
    Returns:
        Sonraki state adı veya None
    """
    stage1_ctx = context.get('stage1', Stage1Context())
    
    if not stage1_ctx.is_target_locked:
        print("[AŞAMA 1 - ATEŞ] HATA: Hedef kilitli değil!")
        return 'STAGE1_AIMING'
    
    current_target_id = stage1_ctx.target_order[stage1_ctx.current_target_index]
    
    print(f"[AŞAMA 1 - ATEŞ] Hedef #{current_target_id} için ATEŞ!")
    
    # Ateş etme işlemi (burada gerçek ateşleme kontrolü olacak)
    _fire_weapon(context)
    
    context['stage1'] = stage1_ctx
    return 'STAGE1_VERIFYING'


def execute_verifying(context: Dict[str, Any]) -> Optional[str]:
    """
    STAGE1_VERIFYING: İmhayı doğrula
    
    Hedefin imha edilip edilmediğini kontrol eder.
    Puanlama yapar.
    
    Returns:
        Sonraki state adı veya None
    """
    stage1_ctx = context.get('stage1', Stage1Context())
    
    current_target_id = stage1_ctx.target_order[stage1_ctx.current_target_index]
    target_distance = stage1_ctx.target_distances.get(current_target_id, 10)
    
    print(f"[AŞAMA 1 - DOĞRULAMA] Hedef #{current_target_id} kontrol ediliyor...")
    
    # İmha kontrolü (burada gerçek görüntü işleme olacak)
    is_destroyed = _verify_target_destroyed(context, current_target_id)
    
    if is_destroyed:
        stage1_ctx.destroyed_targets.append(current_target_id)
        stage1_ctx.last_shot_hit = True
        
        # Puanlama - mesafeye göre
        points = _calculate_points(target_distance)
        stage1_ctx.score += points
        
        print(f"  ✓ Hedef #{current_target_id} İMHA EDİLDİ!")
        print(f"  + {points} puan (Toplam: {stage1_ctx.score})")
        
        # Yanlış sıra kontrolü
        if _check_wrong_order(stage1_ctx, current_target_id):
            stage1_ctx.penalty += 5
            print(f"  ⚠ YANLIŞ SIRA! -5 ceza puanı (Toplam ceza: {stage1_ctx.penalty})")
    else:
        stage1_ctx.last_shot_hit = False
        print(f"  ✗ Hedef #{current_target_id} imha edilemedi!")
    
    stage1_ctx.is_target_locked = False
    context['stage1'] = stage1_ctx
    return 'STAGE1_NEXT_TARGET'


def execute_next_target(context: Dict[str, Any]) -> Optional[str]:
    """
    STAGE1_NEXT_TARGET: Sıradaki hedefe geç
    
    Bir sonraki hedefe geçiş yapar veya aşamayı tamamlar.
    
    Returns:
        Sonraki state adı veya None
    """
    stage1_ctx = context.get('stage1', Stage1Context())
    
    stage1_ctx.current_target_index += 1
    
    if stage1_ctx.current_target_index >= len(stage1_ctx.target_order):
        print("[AŞAMA 1] TÜM HEDEFLER TAMAMLANDI!")
        print(f"  Final Skor: {stage1_ctx.score}")
        print(f"  Ceza: {stage1_ctx.penalty}")
        print(f"  Net Skor: {stage1_ctx.score - stage1_ctx.penalty}")
        context['stage1'] = stage1_ctx
        return 'COMPLETED'
    
    remaining = len(stage1_ctx.target_order) - stage1_ctx.current_target_index
    print(f"[AŞAMA 1] Sıradaki hedefe geçiliyor... (Kalan: {remaining})")
    
    context['stage1'] = stage1_ctx
    return 'STAGE1_AIMING'


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _aim_at_target(context: Dict[str, Any], target_id: int) -> bool:
    """
    Hedefe nişan al.
    
    Bu fonksiyon gerçek implementasyonda servo/gimbal kontrolü yapacak.
    Şimdilik simülasyon için True döndürür.
    """
    # TODO: Gerçek nişan alma implementasyonu
    # - Kamera ile hedef tespiti
    # - Servo/gimbal açı hesaplama
    # - Mekanizma kontrolü
    return True


def _fire_weapon(context: Dict[str, Any]) -> None:
    """
    Silahı ateşle.
    
    Bu fonksiyon gerçek implementasyonda ateşleme mekanizmasını tetikleyecek.
    """
    # TODO: Gerçek ateşleme implementasyonu
    # - Tetik mekanizması kontrolü
    # - Geri tepme kompanzasyonu
    pass


def _verify_target_destroyed(context: Dict[str, Any], target_id: int) -> bool:
    """
    Hedefin imha edilip edilmediğini doğrula.
    
    Bu fonksiyon gerçek implementasyonda görüntü işleme ile kontrol yapacak.
    Şimdilik simülasyon için True döndürür.
    """
    # TODO: Gerçek doğrulama implementasyonu
    # - Kamera görüntüsü analizi
    # - Hedef hala görünür mü kontrolü
    return True


def _calculate_points(distance: float) -> int:
    """
    Mesafeye göre puan hesapla.
    
    Yarışma kurallarına göre puan tablosu uygulanacak.
    """
    # Örnek puanlama (gerçek yarışma kurallarına göre güncellenmeli)
    if distance >= 15:
        return 30  # Uzak mesafe - yüksek puan
    elif distance >= 10:
        return 20  # Orta mesafe
    else:
        return 10  # Yakın mesafe
    

def _check_wrong_order(stage1_ctx: Stage1Context, target_id: int) -> bool:
    """
    Yanlış sırada ateş edilip edilmediğini kontrol et.
    
    Zarf ile verilen sıra dışında bir hedef vurulduysa True döner.
    """
    expected_order = stage1_ctx.target_order
    destroyed = stage1_ctx.destroyed_targets
    
    # Son vurulan hedefin sırası doğru mu?
    if len(destroyed) > 0:
        expected_index = len(destroyed) - 1
        if expected_index < len(expected_order):
            expected_target = expected_order[expected_index]
            if target_id != expected_target:
                return True
    
    return False


# ============================================================================
# STATE DISPATCHER
# ============================================================================

def execute(context: Dict[str, Any]) -> Optional[str]:
    """
    Aşama 1 state dispatcher.
    
    Mevcut state'e göre uygun fonksiyonu çağırır.
    """
    from . import State
    
    current_state = context.get('current_state', State.IDLE)
    
    state_handlers = {
        State.STAGE1_WAITING_ORDER: execute_waiting_order,
        State.STAGE1_AIMING: execute_aiming,
        State.STAGE1_FIRING: execute_firing,
        State.STAGE1_VERIFYING: execute_verifying,
        State.STAGE1_NEXT_TARGET: execute_next_target,
    }
    
    handler = state_handlers.get(current_state)
    if handler:
        return handler(context)
    
    return None


def get_stage1_results(context: Dict[str, Any]) -> Dict[str, Any]:
    """Aşama 1 sonuçlarını döndür"""
    stage1_ctx = context.get('stage1', Stage1Context())
    return {
        'score': stage1_ctx.score,
        'penalty': stage1_ctx.penalty,
        'net_score': stage1_ctx.score - stage1_ctx.penalty,
        'destroyed_targets': stage1_ctx.destroyed_targets,
        'total_targets': len(stage1_ctx.target_order),
    }
