#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LSTM Forecaster - Deep Learning for Non-Linear Pattern Recognition

Why LSTM:
- Your bootstrap/GARCH/VAR assume certain structures
- Reality: Markets have non-linear, complex patterns
- LSTMs learn these patterns from data (no assumptions)

Architecture: Stacked LSTM with dropout
Input: [price, volume, features] → LSTM layers → Dense → Price forecast

Note: Requires training on historical data (not instant like other models)
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import Dataset, DataLoader
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("⚠️ PyTorch not installed. LSTM forecaster disabled.")

from .ensemble import ForecastOutput


class PriceSequenceDataset(Dataset):
    """PyTorch dataset for price sequences"""
    
    def __init__(self, sequences: np.ndarray, targets: np.ndarray):
        self.sequences = torch.FloatTensor(sequences)
        self.targets = torch.FloatTensor(targets)
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        return self.sequences[idx], self.targets[idx]


class LSTMPriceModel(nn.Module):
    """
    LSTM neural network for price forecasting
    
    Architecture:
    - Input: (batch, sequence_length, n_features)
    - LSTM layers with dropout
    - Dense output layer
    - Output: (batch, horizon) price predictions
    """
    
    def __init__(self,
                 n_features: int,
                 hidden_size: int = 128,
                 num_layers: int = 2,
                 dropout: float = 0.2,
                 horizon: int = 48):
        super().__init__()
        
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.horizon = horizon
        
        # LSTM layers
        self.lstm = nn.LSTM(
            input_size=n_features,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        # Output projection
        self.fc = nn.Linear(hidden_size, horizon)
        
        # Dropout
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x):
        # x shape: (batch, seq_len, features)
        
        # LSTM forward
        lstm_out, _ = self.lstm(x)
        
        # Take last timestep
        last_output = lstm_out[:, -1, :]
        
        # Dropout
        last_output = self.dropout(last_output)
        
        # Project to horizon
        output = self.fc(last_output)
        
        return output


class LSTMForecaster:
    """
    LSTM-based forecaster with training and inference
    
    Usage:
    1. Train once on historical data: forecaster.train(historical_df)
    2. Save model: forecaster.save('lstm_model.pt')
    3. Load and forecast: forecaster.load('lstm_model.pt'); forecaster.forecast(current_df)
    """
    
    def __init__(self,
                 sequence_length: int = 100,
                 horizon: int = 48,
                 hidden_size: int = 128,
                 num_layers: int = 2,
                 dropout: float = 0.2):
        """
        Initialize LSTM forecaster
        
        Args:
            sequence_length: Input window size
            horizon: Forecast horizon
            hidden_size: LSTM hidden units
            num_layers: Number of LSTM layers
            dropout: Dropout rate
        """
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch required for LSTM forecaster")
        
        self.sequence_length = sequence_length
        self.horizon = horizon
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        
        self.model = None
        self.scaler_mean = None
        self.scaler_std = None
        self.feature_names = None
        
        # Device
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"LSTM using device: {self.device}")
    
    def _prepare_features(self, df: pd.DataFrame) -> np.ndarray:
        """
        Create features from OHLCV data
        
        Features:
        - Returns (1d, 5d, 20d)
        - Volatility (rolling std)
        - Volume ratio
        - Price momentum
        """
        features = pd.DataFrame(index=df.index)
        
        close = df['close'] if 'close' in df.columns else df['Close']
        volume = df.get('volume', df.get('Volume', pd.Series(1, index=df.index)))
        
        # Returns
        features['return_1d'] = close.pct_change()
        features['return_5d'] = close.pct_change(periods=5)
        features['return_20d'] = close.pct_change(periods=20)
        
        # Volatility
        features['vol_10d'] = features['return_1d'].rolling(10).std()
        features['vol_30d'] = features['return_1d'].rolling(30).std()
        
        # Volume
        features['volume'] = volume
        features['volume_ma'] = volume.rolling(20).mean()
        features['volume_ratio'] = volume / (features['volume_ma'] + 1e-9)
        
        # Price position
        features['sma_20'] = close.rolling(20).mean()
        features['price_vs_sma20'] = (close - features['sma_20']) / (features['sma_20'] + 1e-9)
        
        # Momentum
        features['momentum'] = close / close.shift(14) - 1
        
        # Fill NaN
        features = features.fillna(0)
        
        self.feature_names = features.columns.tolist()
        
        return features.values
    
    def _create_sequences(self, 
                         features: np.ndarray,
                         prices: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create input sequences and target prices
        
        Returns:
            sequences: (n_samples, sequence_length, n_features)
            targets: (n_samples, horizon) - future price changes
        """
        n_samples = len(features) - self.sequence_length - self.horizon
        
        sequences = []
        targets = []
        
        for i in range(n_samples):
            # Input sequence
            seq = features[i:i + self.sequence_length]
            sequences.append(seq)
            
            # Target: future returns
            current_price = prices[i + self.sequence_length]
            future_prices = prices[i + self.sequence_length + 1:i + self.sequence_length + self.horizon + 1]
            future_returns = (future_prices / current_price) - 1
            
            targets.append(future_returns)
        
        return np.array(sequences), np.array(targets)
    
    def train(self,
             df: pd.DataFrame,
             epochs: int = 50,
             batch_size: int = 32,
             learning_rate: float = 0.001,
             validation_split: float = 0.2) -> Dict:
        """
        Train LSTM on historical data
        
        Args:
            df: Historical DataFrame with OHLCV
            epochs: Training epochs
            batch_size: Batch size
            learning_rate: Learning rate
            validation_split: Validation set fraction
            
        Returns:
            Training history
        """
        print(f"\n🧠 Training LSTM forecaster...")
        
        # Prepare features
        features = self._prepare_features(df)
        close = df['close'] if 'close' in df.columns else df['Close']
        prices = close.values
        
        # Create sequences
        X, y = self._create_sequences(features, prices)
        print(f"  Created {len(X)} training sequences")
        
        # Normalize features
        self.scaler_mean = X.mean(axis=(0, 1), keepdims=True)
        self.scaler_std = X.std(axis=(0, 1), keepdims=True) + 1e-9
        X_scaled = (X - self.scaler_mean) / self.scaler_std
        
        # Train/validation split
        split_idx = int(len(X_scaled) * (1 - validation_split))
        X_train, X_val = X_scaled[:split_idx], X_scaled[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        # Create datasets
        train_dataset = PriceSequenceDataset(X_train, y_train)
        val_dataset = PriceSequenceDataset(X_val, y_val)
        
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size)
        
        # Build model
        n_features = X.shape[2]
        self.model = LSTMPriceModel(
            n_features=n_features,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            dropout=self.dropout,
            horizon=self.horizon
        ).to(self.device)
        
        # Optimizer and loss
        optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        criterion = nn.MSELoss()
        
        # Training loop
        history = {'train_loss': [], 'val_loss': []}
        
        for epoch in range(epochs):
            # Train
            self.model.train()
            train_losses = []
            
            for X_batch, y_batch in train_loader:
                X_batch = X_batch.to(self.device)
                y_batch = y_batch.to(self.device)
                
                optimizer.zero_grad()
                predictions = self.model(X_batch)
                loss = criterion(predictions, y_batch)
                loss.backward()
                optimizer.step()
                
                train_losses.append(loss.item())
            
            # Validate
            self.model.eval()
            val_losses = []
            
            with torch.no_grad():
                for X_batch, y_batch in val_loader:
                    X_batch = X_batch.to(self.device)
                    y_batch = y_batch.to(self.device)
                    
                    predictions = self.model(X_batch)
                    loss = criterion(predictions, y_batch)
                    val_losses.append(loss.item())
            
            avg_train_loss = np.mean(train_losses)
            avg_val_loss = np.mean(val_losses)
            
            history['train_loss'].append(avg_train_loss)
            history['val_loss'].append(avg_val_loss)
            
            if (epoch + 1) % 10 == 0:
                print(f"  Epoch {epoch+1}/{epochs} - Train Loss: {avg_train_loss:.6f}, Val Loss: {avg_val_loss:.6f}")
        
        print(f"✅ LSTM training complete")
        
        return history
    
    def forecast(self,
                 close: pd.Series,
                 horizon: int = 48,
                 n_paths: int = 1000) -> ForecastOutput:
        """
        Generate LSTM forecast
        
        Args:
            close: Recent price series (needs >= sequence_length)
            horizon: Forecast horizon (should match training)
            n_paths: Number of Monte Carlo paths
            
        Returns:
            ForecastOutput
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first or load() pretrained model.")
        
        # Convert to DataFrame for feature extraction
        df = pd.DataFrame({'close': close})
        
        # Prepare features
        features = self._prepare_features(df)
        
        # Take last sequence
        if len(features) < self.sequence_length:
            raise ValueError(f"Need at least {self.sequence_length} bars for LSTM forecast")
        
        last_sequence = features[-self.sequence_length:]
        
        # Normalize
        last_sequence_scaled = (last_sequence - self.scaler_mean) / self.scaler_std
        
        # Convert to tensor
        X = torch.FloatTensor(last_sequence_scaled).unsqueeze(0).to(self.device)
        
        # Predict
        self.model.eval()
        with torch.no_grad():
            # Deterministic prediction
            predicted_returns = self.model(X).cpu().numpy()[0]
        
        # Convert returns to prices
        last_price = float(close.iloc[-1])
        
        # Monte Carlo simulation around LSTM prediction
        # Add noise based on historical forecast error (if available)
        noise_std = 0.01  # Default 1% noise per step
        
        paths = np.zeros((n_paths, horizon + 1))
        paths[:, 0] = last_price
        
        for t in range(1, horizon + 1):
            # LSTM predicted return + noise
            if t - 1 < len(predicted_returns):
                base_return = predicted_returns[t - 1]
            else:
                base_return = 0
            
            noise = np.random.randn(n_paths) * noise_std
            returns = base_return + noise
            
            paths[:, t] = paths[:, t-1] * (1 + returns)
        
        # Compute percentiles
        p10 = np.percentile(paths, 10, axis=0)
        p50 = np.percentile(paths, 50, axis=0)
        p90 = np.percentile(paths, 90, axis=0)
        mean = np.mean(paths, axis=0)
        std = np.std(paths, axis=0)
        
        return ForecastOutput(
            p10=p10,
            p50=p50,
            p90=p90,
            mean=mean,
            std=std,
            paths=paths,
            model_name='LSTM',
            confidence=0.7,  # Medium confidence (needs validation)
            metadata={
                'method': 'LSTM neural network',
                'architecture': f'{self.num_layers} layers, {self.hidden_size} units',
                'trained': True
            }
        )
    
    def save(self, path: str):
        """Save trained model"""
        if self.model is None:
            raise ValueError("No model to save")
        
        torch.save({
            'model_state': self.model.state_dict(),
            'scaler_mean': self.scaler_mean,
            'scaler_std': self.scaler_std,
            'feature_names': self.feature_names,
            'config': {
                'sequence_length': self.sequence_length,
                'horizon': self.horizon,
                'hidden_size': self.hidden_size,
                'num_layers': self.num_layers,
                'dropout': self.dropout
            }
        }, path)
        
        print(f"✅ Model saved to {path}")
    
    def load(self, path: str):
        """Load trained model"""
        checkpoint = torch.load(path, map_location=self.device)
        
        # Restore config
        config = checkpoint['config']
        self.sequence_length = config['sequence_length']
        self.horizon = config['horizon']
        self.hidden_size = config['hidden_size']
        self.num_layers = config['num_layers']
        self.dropout = config['dropout']
        
        # Restore scaler
        self.scaler_mean = checkpoint['scaler_mean']
        self.scaler_std = checkpoint['scaler_std']
        self.feature_names = checkpoint['feature_names']
        
        # Rebuild model
        n_features = len(self.feature_names)
        self.model = LSTMPriceModel(
            n_features=n_features,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            dropout=self.dropout,
            horizon=self.horizon
        ).to(self.device)
        
        # Load weights
        self.model.load_state_dict(checkpoint['model_state'])
        self.model.eval()
        
        print(f"✅ Model loaded from {path}")


# =============================================================================
# TRAINING SCRIPT
# =============================================================================

if __name__ == '__main__':
    # This script trains an LSTM model on historical data
    # Run once, then use the saved model for forecasting
    
    print("="*60)
    print("LSTM TRAINING SCRIPT")
    print("="*60)
    
    if not TORCH_AVAILABLE:
        print("❌ PyTorch not installed. Cannot train LSTM.")
        print("Install: pip install torch")
        exit(1)
    
    # Generate training data (replace with real data)
    print("\n📊 Generating synthetic training data...")
    np.random.seed(42)
    n = 5000
    returns = np.random.randn(n) * 0.02
    prices = 50000 * np.cumprod(1 + returns)
    dates = pd.date_range('2022-01-01', periods=n, freq='1h')
    
    df = pd.DataFrame({
        'close': prices,
        'volume': np.random.randint(100, 1000, n)
    }, index=dates)
    
    # Initialize and train
    forecaster = LSTMForecaster(
        sequence_length=100,
        horizon=48,
        hidden_size=128,
        num_layers=2
    )
    
    history = forecaster.train(
        df,
        epochs=50,
        batch_size=32,
        learning_rate=0.001
    )
    
    # Save model
    model_path = '/home/claude/lstm_btc_model.pt'
    forecaster.save(model_path)
    
    # Test forecast
    print("\n🔮 Testing forecast...")
    forecast = forecaster.forecast(df['close'], horizon=48, n_paths=500)
    
    print(f"\n24h forecast:")
    print(f"  P10: ${forecast.p10[24]:,.2f}")
    print(f"  P50: ${forecast.p50[24]:,.2f}")
    print(f"  P90: ${forecast.p90[24]:,.2f}")
    
    print("\n" + "="*60)
    print(f"✅ LSTM model trained and saved to {model_path}")
    print("="*60)
