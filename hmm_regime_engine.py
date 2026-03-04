"""
🌑 HMM REGIME ENGINE - Hidden State Estimation (Baum-Welch)
==========================================================
Identifies underlying market "moods" as hidden states.
Replaces binary IF/ELSE logic with stochastic state transitions.

Inspired by Leonard Baum's work at Renaissance Technologies.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime

class HMMEngine:
    """
    Implements a discrete Hidden Markov Model with Baum-Welch estimation.
    
    States:
    0: ACCUMULATION (Low Vol, Neutral/Bullish Drift)
    1: EXPANSION (High Vol, Strong Trend)
    2: DISTRIBUTION (High Vol, Bearish Drift)
    3: CONTRACTION (Low Vol, Bearish/Neutral)
    """
    
    def __init__(self, n_states: int = 4):
        self.n_states = n_states
        # Initial state probabilities
        self.pi = np.full(n_states, 1.0 / n_states)
        # Transition matrix (A)
        self.A = np.full((n_states, n_states), 1.0 / n_states)
        # Emission matrix (B) - Simplified for demo; in production use Gaussian Emissions
        self.B = np.full((n_states, 10), 0.1) # 10 observable "bins" of price change
        
    def _normalize(self, x):
        return x / np.sum(x)

    def forward(self, observations: np.ndarray) -> np.ndarray:
        """Forward algorithm to calculate alpha"""
        T = len(observations)
        alpha = np.zeros((T, self.n_states))
        alpha[0] = self.pi * self.B[:, observations[0]]
        
        for t in range(1, T):
            for j in range(self.n_states):
                alpha[t, j] = np.dot(alpha[t-1], self.A[:, j]) * self.B[j, observations[t]]
            alpha[t] = self._normalize(alpha[t])
        return alpha

    def backward(self, observations: np.ndarray) -> np.ndarray:
        """Backward algorithm to calculate beta"""
        T = len(observations)
        beta = np.zeros((T, self.n_states))
        beta[T-1] = 1.0
        
        for t in range(T-2, -1, -1):
            for i in range(self.n_states):
                beta[t, i] = np.sum(self.A[i, :] * self.B[:, observations[t+1]] * beta[t+1])
            beta[t] = self._normalize(beta[t])
        return beta

    def estimate_states(self, observations: np.ndarray) -> List[int]:
        """Viterbi or Posterior decoding to find the most likely regime path"""
        alpha = self.forward(observations)
        beta = self.backward(observations)
        gamma = alpha * beta
        gamma = gamma / np.sum(gamma, axis=1)[:, np.newaxis]
        return np.argmax(gamma, axis=1).tolist()

    def train_baum_welch(self, observations: np.ndarray, iterations: int = 10):
        """
        Refines A, B, and Pi based on training data.
        This is the core 'Expertise' of the Math Team.
        """
        T = len(observations)
        for _ in range(iterations):
            alpha = self.forward(observations)
            beta = self.backward(observations)
            
            # Gamma (probability of being in state i at time t)
            gamma = alpha * beta
            gamma /= np.sum(gamma, axis=1)[:, np.newaxis]
            
            # Xi (probability of transitioning from i to j at time t)
            xi = np.zeros((T-1, self.n_states, self.n_states))
            for t in range(T-1):
                denom = np.dot(np.dot(alpha[t], self.A), self.B[:, observations[t+1]] * beta[t+1])
                for i in range(self.n_states):
                    numer = alpha[t, i] * self.A[i, :] * self.B[:, observations[t+1]] * beta[t+1]
                    xi[t, i, :] = numer / denom
            
            # Update Pi, A, B
            self.pi = gamma[0]
            self.A = np.sum(xi, axis=0) / np.sum(gamma[:-1], axis=0)[:, np.newaxis]
            
            for k in range(self.B.shape[1]):
                mask = (observations == k)
                self.B[:, k] = np.sum(gamma[mask], axis=0) / np.sum(gamma, axis=0)
                
            # Re-normalize
            self.A = np.apply_along_axis(self._normalize, 1, self.A)
            self.B = np.apply_along_axis(self._normalize, 1, self.B)

    def get_regime_label(self, state_index: int) -> str:
        labels = {
            0: "ACCUMULATION (Institutional Load)",
            1: "EXPANSION (Momentum Velocity)",
            2: "DISTRIBUTION (Retail Exit)",
            3: "CONTRACTION (Stability/Freeze)"
        }
        return labels.get(state_index, "UNCERTAIN")

    def get_snapshot(self) -> Dict:
        return {
            "transition_matrix": self.A.tolist(),
            "state_priors": self.pi.tolist(),
            "n_states": self.n_states
        }
