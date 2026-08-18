import unittest
import os
import json
from pathlib import Path
from unittest.mock import patch
from src.memory.preflight import enforce_preflight
from src.factory.loop_trend import run_trend_batch_a

class TestEnforcePreflight(unittest.TestCase):

    def test_rejected_families(self):
        # El sistema debe bloquear la ejecución de todas las familias RECHAZADAS.
        # Estamos haciendo un test de integración contra la DB real de memory.
        
        rejected_families = [
            "TREND_FOLLOWING_4H",
            "FUNDING_CONTRARIAN",
            "CROSS_SECTIONAL_MOMENTUM_4H",
            "VOLATILITY_COMPRESSION_BREAKOUT",
            "EVENT_SHOCK_REVERSAL_1H",
            "LIQUIDATION_DERIVATIVES_REVERSAL",
            "FUNDING_MOMENTUM_1H"
        ]
        
        for family in rejected_families:
            with self.subTest(family=family):
                # Debemos mockear print para no saturar los tests
                with patch('builtins.print') as mock_print:
                    result = enforce_preflight(family)
                    self.assertFalse(result, f"Family {family} should be blocked")
                    
    def test_new_family_allowed(self):
        # Una familia nueva como BASIS_TERM_STRUCTURE debe permitirse
        with patch('builtins.print') as mock_print:
            result = enforce_preflight("BASIS_TERM_STRUCTURE", "Nueva hipótesis sobre term structure")
            self.assertTrue(result, "New family should be allowed to proceed")

    def test_regression_loop_generation_blocked(self):
        # Test de regresión: intentar ejecutar un loop de una familia REJECTED no debe
        # crear archivos de estrategia en src/strategies/live_candidates
        
        live_dir = Path("src/strategies/live_candidates")
        
        # Contar archivos antes
        if live_dir.exists():
            files_before = len(list(live_dir.glob("*.json")))
        else:
            files_before = 0
            
        with patch('builtins.print') as mock_print:
            # Ejecutamos el loop de TREND_FOLLOWING_4H que está REJECTED
            run_trend_batch_a()
            
        # Contar archivos después
        if live_dir.exists():
            files_after = len(list(live_dir.glob("*.json")))
        else:
            files_after = 0
            
        self.assertEqual(files_before, files_after, "No files should be generated for blocked family")

if __name__ == '__main__':
    unittest.main()
