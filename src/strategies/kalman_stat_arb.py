"""
Kalman Filter Dynamic State-Space Statistical Arbitrage
Estima beta_t y alpha_t recursivamente en tiempo real (sin look-ahead bias).
Calcula la innovación e_t y el Z-Score normalizado por la varianza de error Q_t.
"""

from typing import Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller

class KalmanStatArb:
    """Motor de Arbitraje Estadístico con Filtro de Kalman Adaptativo."""
    
    def __init__(
        self,
        delta: float = 1e-4,     # Varianza de transición del estado (Rw)
        ve: float = 1e-3,        # Varianza de observación (Ve)
        z_entry: float = 1.8,
        z_exit: float = 0.2,
        z_stop: float = 3.5,
        half_life_max: int = 40
    ):
        self.delta = delta
        self.ve = ve
        self.z_entry = z_entry
        self.z_exit = z_exit
        self.z_stop = z_stop
        self.half_life_max = half_life_max
        
    def run_kalman_filter(self, y: np.ndarray, x: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Ejecuta el Filtro de Kalman paso a paso sobre las series de precios x e y.
        Retorna:
            beta: Serie temporal de hedge ratios dinámicos.
            residuals: Serie de errores de innovación e_t.
            z_scores: Serie de Z-scores estandarizados por sqrt(Q_t).
        """
        n = len(y)
        x_mat = np.vstack([x, np.ones(n)]).T  # [x_t, 1]
        
        # Inicialización de matrices
        theta = np.zeros((2, 1))  # [beta, alpha]
        P = np.eye(2) * 1.0       # Matriz de covarianza de estado
        R = np.eye(2) * (self.delta / (1.0 - self.delta)) # Ruido de proceso
        
        betas = np.zeros(n)
        residuals = np.zeros(n)
        z_scores = np.zeros(n)
        
        for t in range(n):
            # 1. Predicción
            theta_pred = theta
            P_pred = P + R
            
            # Vector de observación H_t = [x_t, 1]
            H = x_mat[t:t+1, :]
            
            # 2. Innovación / Error de predicción
            y_pred = float(np.dot(H, theta_pred)[0, 0])
            e_t = y[t] - y_pred
            
            # Varianza de innovación Q_t = H * P_pred * H^T + Ve
            Q_t = float(np.dot(np.dot(H, P_pred), H.T)[0, 0]) + self.ve
            
            # 3. Ganancia de Kalman K_t = P_pred * H^T / Q_t
            K = np.dot(P_pred, H.T) / Q_t
            
            # 4. Actualización de estado
            theta = theta_pred + K * e_t
            P = P_pred - np.dot(K, np.dot(H, P_pred))
            
            betas[t] = theta[0, 0]
            residuals[t] = e_t
            z_scores[t] = e_t / np.sqrt(Q_t) if Q_t > 0 else 0.0
            
        return betas, residuals, z_scores
