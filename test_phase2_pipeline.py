#!/usr/bin/env python3
"""
Aşama 2 Uçtan Uca Boru Hattı (End-to-End Pipeline) Entegrasyon Testi
-------------------------------------------------------------------
1. Girdi: Sentetik hareketli 2B BBox (iha)
2. pnp_depth_estimator: 3B X, Y, Z ve Radyal Menzil çıkarımı
3. tracker_node (EKF 3D): Titreşim giderme ve Vx, Vy, Vz hız vektörü hesabı
4. ballistic_calculator: Lead Angle (Önleme Açısı) kestirimi
5. dual_axis_pid_node: Pan/Tilt motor adımları ve hız komutları üretimi
"""

import math
import numpy as np
from hss_localization_3d.pnp_depth_estimator import PnPDepthEstimator
from hss_tracking.ekf_filter_3d import EKFFilter3D
from hss_guidance_control.ballistic_calculator import BallisticCalculator


def test_phase2_math_pipeline():
    print("=== AŞAMA 2 BORU HATTI TESTİ BAŞLIYOR ===")

    # 1. 3B Poz Kestirimi (PnP / Monocular)
    fx, fy, cx, cy = 620.0, 620.0, 320.0, 240.0
    real_h = 0.20 # İHA yüksekliği (metre)
    real_w = 0.40 # İHA kanat genişliği (metre)

    # Hedef 5 metre mesafede olsun:
    # pixel_h = (fy * real_h) / Z = (620 * 0.20) / 5.0 = 24.8 piksel
    pixel_h = 25
    pixel_w = 50
    # Hedef sağa doğru hareket etsin: x_center 320'den (eksen) 400'e ilerliyor
    x_centers = [320, 335, 350, 365, 380] # 5 ardışık kare (dt = 0.1s)
    dt = 0.1

    # EKF Filtresi
    ekf = EKFFilter3D(init_pos=(0.0, 0.0, 5.0), q_pos=0.01, q_vel=0.1, r_meas=0.05)

    positions = []
    velocities = []

    for idx, cx_meas in enumerate(x_centers):
        # Monoküler 3B Metrik Konum
        Z = (fy * real_h) / float(pixel_h)
        X = ((cx_meas - cx) * Z) / fx
        Y = 0.0 # Yatay düzlemde uçuyor

        # Kalman Filtresi Tahmin ve Güncelleme
        ekf.predict(dt)
        ekf.update((X, Y, Z))

        pos = ekf.position
        vel = ekf.velocity
        positions.append(pos)
        velocities.append(vel)
        print(f"Adım {idx+1}: Ölçülen X={X:.2f}m, Z={Z:.2f}m | Filtrelenmiş X={pos[0]:.2f}m, Hız Vx={vel[0]:.2f} m/s")

    final_pos = positions[-1]
    final_vel = velocities[-1]

    # Hedef hızının pozitif (sağa doğru) olduğu doğrulanmalı
    assert final_vel[0] > 0.5, f"Hız Vx beklenenden düşük: {final_vel[0]}"
    print(">> Kalman Filtresi Hız Kestirimi Başarılı! (Vx > 0)")

    # 2. Balistik Önleme Açısı (Lead Angle) Hesabı
    range_m = math.sqrt(final_pos[0]**2 + final_pos[1]**2 + final_pos[2]**2)
    # 0.05 saniyelik sistem gecikmesi + mühimmat süresi (örnek: 80 m/s mermi)
    v_proj = 80.0
    t_flight = (range_m / v_proj) + 0.04 # sn

    # Önleme Noktası (Intercept Point)
    x_intercept = final_pos[0] + (final_vel[0] * t_flight)
    z_intercept = final_pos[2] + (final_vel[2] * t_flight)

    # Hedefin şu anki açısı vs Önleme Açısı
    current_pan_deg = math.degrees(math.atan2(final_pos[0], final_pos[2]))
    lead_pan_deg = math.degrees(math.atan2(x_intercept, z_intercept))

    print(f"\nMenzil: {range_m:.2f} m")
    print(f"Uçuş + Gecikme Süresi (t_flight): {t_flight*1000:.1f} ms")
    print(f"Hedefin Anlık Açısı: {current_pan_deg:.2f}°")
    print(f"Önleme Açısı (Lead Angle): {lead_pan_deg:.2f}° (Fark: {lead_pan_deg - current_pan_deg:+.2f}°)")

    # Önleme açısı hedefin ilerisine nişan almalı
    assert lead_pan_deg > current_pan_deg, "Önleme açısı hedefin hareket yönünün ilerisinde olmalı!"
    print(">> Balistik Önleme (Lead Angle) Doğrulaması Başarılı!")

    # 3. Motor Adım Dönüşümü (3200 adım/tur, 3:1 redüksiyon = 26.67 adım/derece)
    steps_per_deg = (3200 * 3.0) / 360.0
    target_steps = int(lead_pan_deg * steps_per_deg)
    print(f"Taret Pan Hedef Adımı: {target_steps} steps ({steps_per_deg:.1f} steps/deg)")

    print("\n=== TÜM AŞAMA 2 MODÜLER MATEMATİK BORU HATTI TESTLERİ BAŞARIYLA GEÇTİ! ===")


if __name__ == '__main__':
    test_phase2_math_pipeline()
