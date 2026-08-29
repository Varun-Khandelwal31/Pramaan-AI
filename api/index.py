import sys
import os

# Add parent directory to path so imports work seamlessly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
