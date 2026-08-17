import sys
from pathlib import Path

# Añadir raíz
sys.path.append(str(Path(__file__).parent.parent))

from src.factory.loop import run_factory_cycle

if __name__ == '__main__':
    run_factory_cycle(batch_size=5)
