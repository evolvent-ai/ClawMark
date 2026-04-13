"""
Legacy Pooler Module
====================
Global average pooling layer for feature aggregation.
Originally used in early UniAlign prototypes (v0.1-v0.3).
Replaced by cross-attention mechanism in v0.4+.
"""

import torch
import torch.nn as nn


class LegacyPooler(nn.Module):
    """
    Simple pooling layer that aggregates sequence features into a fixed-size vector.
    Supports mean pooling and max pooling strategies.
    """

    def __init__(self, hidden_size, pooling_strategy="mean"):
        super().__init__()
        self.hidden_size = hidden_size
        self.pooling_strategy = pooling_strategy
        self.dense = nn.Linear(hidden_size, hidden_size)
        self.activation = nn.Tanh()
        self.output_proj = nn.Linear(hidden_size, hidden_size)

    def forward(self, hidden_states, attention_mask=None):
        """
        Args:
            hidden_states: (batch, seq_len, hidden_size)
            attention_mask: (batch, seq_len), optional
        Returns:
            pooled: (batch, hidden_size)
        """
        if attention_mask is not None:
            mask = attention_mask.unsqueeze(-1).float()
            hidden_states = hidden_states * mask

        if self.pooling_strategy == "mean":
            if attention_mask is not None:
                pooled = hidden_states.sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
            else:
                pooled = hidden_states.mean(dim=1)
        elif self.pooling_strategy == "max":
            if attention_mask is not None:
                hidden_states = hidden_states.masked_fill(mask == 0, float("-inf"))
            pooled = hidden_states.max(dim=1)[0]
        elif self.pooling_strategy == "cls":
            pooled = hidden_states[:, 0]
        else:
            raise ValueError(f"Unknown pooling strategy: {self.pooling_strategy}")

        pooled = self.dense(pooled)
        pooled = self.activation(pooled)
        pooled = self.output_proj(pooled)

        return pooled
