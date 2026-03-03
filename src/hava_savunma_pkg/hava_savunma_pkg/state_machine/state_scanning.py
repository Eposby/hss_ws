#!/usr/bin/env python3
"""
SCANNING State - Balon Tarama/Tespit Modu
Kameradan görüntü alıp kırmızı ve mavi balonları tespit eder
"""

import cv2
import numpy as np


def detect_balloons(frame):
    """
    Görüntüden kırmızı ve mavi balonları tespit et.
    
    Args:
        frame: BGR formatında görüntü
        
    Returns:
        dict: {'red': [(x, y, w, h), ...], 'blue': [(x, y, w, h), ...]}
    """
    if frame is None:
        return {'red': [], 'blue': []}
    
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    results = {'red': [], 'blue': []}
    
    # KIRMIZI balon tespiti (HSV)
    # Kırmızı iki aralıkta (0-10 ve 160-180)
    red_lower1 = np.array([0, 100, 100])
    red_upper1 = np.array([10, 255, 255])
    red_lower2 = np.array([160, 100, 100])
    red_upper2 = np.array([180, 255, 255])
    
    red_mask1 = cv2.inRange(hsv, red_lower1, red_upper1)
    red_mask2 = cv2.inRange(hsv, red_lower2, red_upper2)
    red_mask = cv2.bitwise_or(red_mask1, red_mask2)
    
    # MAVİ balon tespiti (HSV)
    blue_lower = np.array([100, 100, 100])
    blue_upper = np.array([130, 255, 255])
    blue_mask = cv2.inRange(hsv, blue_lower, blue_upper)
    
    # Gürültü temizleme
    kernel = np.ones((5, 5), np.uint8)
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
    blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_OPEN, kernel)
    
    # Kırmızı balonları bul
    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 500:  # Minimum alan
            x, y, w, h = cv2.boundingRect(cnt)
            results['red'].append((x, y, w, h))
    
    # Mavi balonları bul
    contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 500:
            x, y, w, h = cv2.boundingRect(cnt)
            results['blue'].append((x, y, w, h))
    
    return results


def get_position_name(x, frame_width):
    """
    Balonun görüntüdeki konumunu belirle (sol, orta, sağ)
    """
    third = frame_width / 3
    if x < third:
        return "SOL"
    elif x < 2 * third:
        return "ORTA"
    else:
        return "SAĞ"


def execute(context):
    """
    SCANNING durumunda çalışır.
    Kameradan görüntü alıp balonları tespit eder.
    
    Args:
        context: Paylaşılan veriler
    
    Returns:
        Sonraki state adı veya None
    """
    frame = context.get('frame')
    
    if frame is None:
        print("[SCANNING] Kamera görüntüsü bekleniyor...")
        return None
    
    # Balonları tespit et
    balloons = detect_balloons(frame)
    context['balloons'] = balloons
    
    frame_height, frame_width = frame.shape[:2]
    
    # Sonuçları yazdır
    total = len(balloons['red']) + len(balloons['blue'])
    
    if total > 0:
        print(f"[SCANNING] {total} balon tespit edildi:")
        
        for x, y, w, h in balloons['red']:
            pos = get_position_name(x + w/2, frame_width)
            print(f"  🔴 KIRMIZI balon - Konum: {pos} (x={x}, y={y})")
        
        for x, y, w, h in balloons['blue']:
            pos = get_position_name(x + w/2, frame_width)
            print(f"  🔵 MAVİ balon - Konum: {pos} (x={x}, y={y})")
        
        return 'DETECTED'
    else:
        print("[SCANNING] Balon bulunamadı, taramaya devam...")
        return None


def draw_detections(frame, balloons):
    """
    Tespit edilen balonları görüntü üzerine çiz.
    """
    result = frame.copy()
    
    # Kırmızı balonları çiz
    for x, y, w, h in balloons.get('red', []):
        cv2.rectangle(result, (x, y), (x+w, y+h), (0, 0, 255), 2)
        cv2.putText(result, "KIRMIZI", (x, y-10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    
    # Mavi balonları çiz
    for x, y, w, h in balloons.get('blue', []):
        cv2.rectangle(result, (x, y), (x+w, y+h), (255, 0, 0), 2)
        cv2.putText(result, "MAVI", (x, y-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
    
    return result
