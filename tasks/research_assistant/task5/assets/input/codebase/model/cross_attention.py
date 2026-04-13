"""Cross-Modal Attention Module for UniAlign."""

import einops
import torch
import torch.nn as nn
import torch.nn.functional as F
import math


class CrossModalAttention(nn.Module):
    """
    Cross-modal attention layer that attends from one modality to another.
    Implements scaled dot-product attention with optional gating.
    """

    def __init__(self, hidden_size, num_heads, dropout=0.1):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads
        assert hidden_size % num_heads == 0, "hidden_size must be divisible by num_heads"

        self.q_proj = nn.Linear(hidden_size, hidden_size)
        self.k_proj = nn.Linear(hidden_size, hidden_size)
        self.v_proj = nn.Linear(hidden_size, hidden_size)
        self.out_proj = nn.Linear(hidden_size, hidden_size)

        self.gate = nn.Linear(hidden_size * 2, hidden_size)
        self.layer_norm1 = nn.LayerNorm(hidden_size)
        self.layer_norm2 = nn.LayerNorm(hidden_size)
        self.dropout = nn.Dropout(dropout)

        self.ffn = nn.Sequential(
            nn.Linear(hidden_size, hidden_size * 4),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size * 4, hidden_size),
            nn.Dropout(dropout),
        )

    def forward(self, query, key_value, attention_mask=None):
        """
        Args:
            query: (batch, seq_q, hidden_size) - typically text features
            key_value: (batch, seq_kv, hidden_size) - typically vision features
            attention_mask: optional mask
        """
        residual = query
        query = self.layer_norm1(query)

        batch_size = query.size(0)

        q = self.q_proj(query)
        k = self.k_proj(key_value)
        v = self.v_proj(key_value)

        # Reshape to multi-head using einops
        q = einops.rearrange(q, "b s (h d) -> b h s d", h=self.num_heads)
        k = einops.rearrange(k, "b s (h d) -> b h s d", h=self.num_heads)
        v = einops.rearrange(v, "b s (h d) -> b h s d", h=self.num_heads)

        # Scaled dot-product attention
        scale = math.sqrt(self.head_dim)
        attn_weights = torch.matmul(q, k.transpose(-2, -1)) / scale

        if attention_mask is not None:
            attn_weights = attn_weights.masked_fill(attention_mask == 0, float("-inf"))

        attn_weights = F.softmax(attn_weights, dim=-1)
        attn_weights = self.dropout(attn_weights)

        attn_output = torch.matmul(attn_weights, v)
        attn_output = einops.rearrange(attn_output, "b h s d -> b s (h d)")
        attn_output = self.out_proj(attn_output)

        # Gating mechanism
        gate_input = torch.cat([residual, attn_output], dim=-1)
        gate_value = torch.sigmoid(self.gate(gate_input))
        output = residual + gate_value * self.dropout(attn_output)

        # Feed-forward
        output = output + self.ffn(self.layer_norm2(output))

        return output
