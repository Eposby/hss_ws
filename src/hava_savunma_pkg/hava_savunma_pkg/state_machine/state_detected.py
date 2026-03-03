#!/usr/bin/env python3
"""
DETECTED State - Balon Tespit Edildi
"""


def execute(context):
    """
    DETECTED durumunda çalışır.
    Tespit edilen balonlarla ilgili işlem yapılır.
    
    Args:
        context: Paylaşılan veriler
    
    Returns:
        Sonraki state adı veya None
    """
    balloons = context.get('balloons', {'red': [], 'blue': []})
    
    red_count = len(balloons['red'])
    blue_count = len(balloons['blue'])
    
    print(f"[DETECTED] Toplam: {red_count} kırmızı, {blue_count} mavi balon")
    
    # Burada hedef seçimi, ateşleme vb. yapılabilir
    # Şimdilik tekrar taramaya dön
    
    if context.get('continue_scanning', True):
        return 'SCANNING'
    
    return 'IDLE'
