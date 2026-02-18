#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Elite Forecasting System
Ensemble of 4 forecasting models for crypto price prediction
"""

__version__ = '1.0.0'
__author__ = 'QC-AI Elite'

# Import main classes
from .ensemble import EnsembleForecaster, ForecastOutput
from .bootstrap_forecaster import BootstrapForecaster
from .garch_forecaster import GARCHForecaster
from .var_forecaster import VARForecaster

# Optional LSTM (requires torch)
try:
    from .ml_forecaster import LSTMForecaster, LSTMPriceModel
    LSTM_AVAILABLE = True
except ImportError:
    LSTM_AVAILABLE = False

__all__ = [
    'EnsembleForecaster',
    'ForecastOutput',
    'BootstrapForecaster',
    'GARCHForecaster',
    'VARForecaster',
]

if LSTM_AVAILABLE:
    __all__.extend(['LSTMForecaster', 'LSTMPriceModel'])
