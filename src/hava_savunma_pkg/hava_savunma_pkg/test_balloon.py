#!/usr/bin/env python3
"""
Basit Test Script - ROS2 olmadan çalıştır
Webcam veya görüntü dosyası ile test
"""

import sys
import os

# Paket yolunu ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
from state_machine.machine import StateMachine
from state_machine import State
from state_machine import state_scanning


def test_with_webcam():
    """Webcam ile test"""
    print("=" * 50)
    print("BALON TESPİT SİSTEMİ - TEST")
    print("=" * 50)
    print("Kontroller:")
    print("  SPACE: Sistemi başlat/durdur")
    print("  Q: Çıkış")
    print("=" * 50)
    
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("HATA: Kamera açılamadı!")
        return
    
    sm = StateMachine(State.IDLE)
    running = False
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Frame'i state machine'e ver
        sm.set_frame(frame)
        
        # State machine güncelle
        if running:
            sm.update()
        
        # Tespit edilen balonları çiz
        balloons = sm.get_balloons()
        display = state_scanning.draw_detections(frame, balloons)
        
        # Durum bilgisi
        status = f"State: {sm.current_state.name}"
        red_count = len(balloons['red'])
        blue_count = len(balloons['blue'])
        info = f"Kirmizi: {red_count} | Mavi: {blue_count}"
        
        cv2.putText(display, status, (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(display, info, (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        cv2.imshow('Balon Tespit', display)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord(' '):
            running = not running
            if running:
                sm.start()
                print(">>> Sistem BAŞLATILDI")
            else:
                sm.stop()
                print(">>> Sistem DURDURULDU")
    
    cap.release()
    cv2.destroyAllWindows()


def test_with_image(image_path):
    """Görüntü dosyası ile test"""
    print(f"Test görüntüsü: {image_path}")
    
    frame = cv2.imread(image_path)
    if frame is None:
        print(f"HATA: Görüntü okunamadı: {image_path}")
        return
    
    sm = StateMachine(State.IDLE)
    sm.set_frame(frame)
    sm.start()
    
    # Birkaç güncelleme çalıştır
    for _ in range(3):
        sm.update()
    
    balloons = sm.get_balloons()
    display = state_scanning.draw_detections(frame, balloons)
    
    print(f"Sonuç: {len(balloons['red'])} kırmızı, {len(balloons['blue'])} mavi balon")
    
    cv2.imshow('Sonuç', display)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        test_with_image(sys.argv[1])
    else:
        test_with_webcam()
