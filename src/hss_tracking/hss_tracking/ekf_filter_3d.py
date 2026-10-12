#!/usr/bin/env python3
"""
3 Boyutlu Sabit Hızlı (Constant Velocity) Kalman Filtresi (EKF 3D)
-----------------------------------------------------------------
Hedefin 3B uzaydaki konumunu (X, Y, Z) filtreler ve hız vektörünü
(Vx, Vy, Vz) matematiksel olarak türetir. Titremeleri (jitter) yok eder.
"""

import numpy as np


class EKFFilter3D:
    def __init__(self, init_pos=(0.0, 0.0, 0.0), q_pos=0.05, q_vel=0.50, r_meas=0.10):
        """
        Durum vektörü: X = [x, y, z, vx, vy, vz]^T
        """
        # Durum vektörü başlatma
        self.x = np.array([
            init_pos[0], init_pos[1], init_pos[2],
            0.0, 0.0, 0.0
        ], dtype=np.float64)

        # Kovaryans matrisi P
        self.P = np.diag([0.5, 0.5, 0.5, 2.0, 2.0, 2.0]).astype(np.float64)

        # Ölçüm matrisi H (Yalnızca konumlar ölçülür: X, Y, Z)
        self.H = np.zeros((3, 6), dtype=np.float64)
        self.H[0, 0] = 1.0
        self.H[1, 1] = 1.0
        self.H[2, 2] = 1.0

        # Ölçüm gürültüsü kovaryansı R
        self.R = np.eye(3, dtype=np.float64) * r_meas

        # Süreç gürültüsü parametreleri
        self.q_pos = q_pos
        self.q_vel = q_vel

    def predict(self, dt: float):
        """Durum geçişi ve kestirim adımı."""
        if dt <= 0.0:
            return

        # Durum geçiş matrisi F
        F = np.eye(6, dtype=np.float64)
        F[0, 3] = dt
        F[1, 4] = dt
        F[2, 5] = dt

        # Süreç gürültüsü matrisi Q
        Q = np.zeros((6, 6), dtype=np.float64)
        dt2 = 0.5 * (dt ** 2)
        for i in range(3):
            Q[i, i] = self.q_pos * (dt ** 2)
            Q[i + 3, i + 3] = self.q_vel * dt
            Q[i, i + 3] = self.q_pos * dt2
            Q[i + 3, i] = self.q_pos * dt2

        # x = F * x
        self.x = F @ self.x
        # P = F * P * F^T + Q
        self.P = F @ self.P @ F.T + Q

    def update(self, measurement: tuple):
        """Ölçüm güncelleme adımı: measurement = (meas_x, meas_y, meas_z)."""
        z = np.array(measurement, dtype=np.float64)

        # İnovasyon (Kalıntı): y = z - H * x
        y = z - (self.H @ self.x)

        # İnovasyon kovaryansı: S = H * P * H^T + R
        S = (self.H @ self.P @ self.H.T) + self.R

        # Kalman Kazancı: K = P * H^T * inv(S)
        K = self.P @ self.H.T @ np.linalg.inv(S)

        # Durum güncelleme: x = x + K * y
        self.x = self.x + (K @ y)

        # Kovaryans güncelleme: P = (I - K * H) * P
        I = np.eye(6, dtype=np.float64)
        self.P = (I - (K @ self.H)) @ self.P

    @property
    def position(self):
        """Filtrelenmiş konum (X, Y, Z)."""
        return float(self.x[0]), float(self.x[1]), float(self.x[2])

    @property
    def velocity(self):
        """Türetilmiş hız vektörü (Vx, Vy, Vz) m/s."""
        return float(self.x[3]), float(self.x[4]), float(self.x[5])

    @property
    def speed(self):
        """Bileşke hız büyüklüğü (m/s)."""
        return float(np.linalg.norm(self.x[3:6]))
