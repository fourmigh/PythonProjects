import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawler.dependency_checker import remove_all

remove_all()
