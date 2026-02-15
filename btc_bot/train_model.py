"""
Train the ML model - run this after data collection (Phase 1).

Usage: python train_model.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from models.train import train

if __name__ == "__main__":
    train(limit=5000, train_frac=0.8)
    print("\nPHASE 3 COMPLETE")
