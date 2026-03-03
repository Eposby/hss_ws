#!/usr/bin/env python3
"""
IDLE State - Bekleme Modu
"""


def execute(context):
    """
    IDLE durumunda çalışır.
    
    Args:
        context: Paylaşılan veriler (kamera, tespit sonuçları vb.)
    
    Returns:
        Sonraki state adı veya None (aynı state'te kal)
    """
    print("[IDLE] Sistem bekleme modunda...")
    
    # Eğer başlatma komutu geldiyse SCANNING'e geç
    if context.get('start_command', False):
        context['start_command'] = False
        return 'SCANNING'
    
    return None  # IDLE'da kal
