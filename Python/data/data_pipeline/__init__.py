# Explicitly list what should be exported
from .cleaner import clean_data
from .loader import load_data

__all__ = ['clean_data', 'load_data']  # Only these will be available in 'from data_pipeline import *'

# Bonus: You can still import non-__all__ items explicitly:
# from data_pipeline.utils import helper_function