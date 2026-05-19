import os
import sys
from pathlib import Path

# Add the kidzora directory to Python path
kidzora_path = Path(__file__).parent.parent / 'kidzora'
sys.path.insert(0, str(kidzora_path))

from run import app

# Export app for Vercel
__all__ = ['app']
