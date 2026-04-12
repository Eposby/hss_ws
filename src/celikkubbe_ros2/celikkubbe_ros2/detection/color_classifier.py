import cv2
import numpy as np

class VehicleColorClassifier:
    """
    Araç gövde rengini HSV analizi ile belirler.
    Balon bölgesi çıkarılarak sadece araç gövdesi analiz edilir.
    """
    
    # Önceden belirlenen HSV renk eşikleri (Yarışma kurallarına göre güncellenecektir)
    COLOR_RANGES = {
        "kirmizi": [(0, 70, 50, 10, 255, 255), (170, 70, 50, 180, 255, 255)],
        "mavi": [(100, 70, 50, 130, 255, 255)],
        "yesil": [(35, 70, 50, 85, 255, 255)],
        "sari": [(20, 100, 100, 35, 255, 255)],
        "beyaz": [(0, 0, 180, 180, 30, 255)],
        "siyah": [(0, 0, 0, 180, 255, 50)],
    }
    
    def __init__(self, friendly_colors=None, enemy_colors=None):
        self.friendly_colors = friendly_colors or ["mavi", "yesil"]
        self.enemy_colors = enemy_colors or ["kirmizi"]

    def classify(self, frame, vehicle_bbox, balloon_bbox=None):
        """
        Gövdenin ağırlıklı rengini döndür.
        Returns:
            (renk_adi, is_friendly)
        """
        x1, y1, x2, y2 = vehicle_bbox
        
        # Araç bbox sınırlarını garantile
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)
        
        if x2 <= x1 or y2 <= y1:
            return ("bilinmiyor", False)
            
        roi = frame[y1:y2, x1:x2]
        hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        # Eğer balon bbox biliniyorsa o kısmı maskele ki analizden çıksın
        mask = np.ones(roi.shape[:2], dtype=np.uint8) * 255
        if balloon_bbox:
            bx1, by1, bx2, by2 = balloon_bbox
            # Balon koordinatlarını ROI koordinat sistemine çevir
            bx1, by1 = max(0, bx1 - x1), max(0, by1 - y1)
            bx2, by2 = min(roi.shape[1], bx2 - x1), min(roi.shape[0], by2 - y1)
            if bx2 > bx1 and by2 > by1:
                cv2.rectangle(mask, (bx1, by1), (bx2, by2), 0, -1)
                
        # Her renk için maske piksel sayısını hesapla
        color_counts = {}
        for color, ranges in self.COLOR_RANGES.items():
            color_mask = np.zeros(roi.shape[:2], dtype=np.uint8)
            for (lh, ls, lv, hh, hs, hv) in ranges:
                lower = np.array([lh, ls, lv])
                upper = np.array([hh, hs, hv])
                c_mask = cv2.inRange(hsv_roi, lower, upper)
                color_mask = cv2.bitwise_or(color_mask, c_mask)
            
            # Balonu dahil etme
            color_mask = cv2.bitwise_and(color_mask, color_mask, mask=mask)
            color_counts[color] = cv2.countNonZero(color_mask)
            
        # En dominant rengi bul
        dominant_color = max(color_counts, key=color_counts.get)
        
        # Önemsiz miktardaysa bilinmiyor de
        total_pixels = roi.shape[0] * roi.shape[1]
        if color_counts[dominant_color] / max(1, total_pixels) < 0.05:
            return ("bilinmiyor", False)
            
        is_friendly = dominant_color in self.friendly_colors
        return (dominant_color, is_friendly)
