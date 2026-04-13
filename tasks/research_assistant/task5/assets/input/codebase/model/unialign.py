"""
UniAlign: Unified Cross-Modal Alignment Model
=============================================
Main model architecture for UniAlign.
"""

import torch
import torch.nn as nn
from transformers import CLIPModel, CLIPProcessor

from .cross_attention import CrossModalAttention


class UniAlignModel(nn.Module):
    """
    UniAlign model that performs unified cross-modal alignment
    for low-resource multimodal reasoning tasks.
    """

    def __init__(self, config):
        super().__init__()
        self.config = config

        # Vision encoder (CLIP ViT-Large)
        self.vision_encoder = CLIPModel.from_pretrained(
            config.get("vision_model", "openai/clip-vit-large-patch14")
        ).vision_model

        # Text encoder
        self.text_encoder = CLIPModel.from_pretrained(
            config.get("vision_model", "openai/clip-vit-large-patch14")
        ).text_model

        hidden_size = config.get("hidden_size", 768)
        num_heads = config.get("num_heads", 12)
        num_layers = config.get("num_cross_layers", 4)

        # Cross-modal attention layers
        self.cross_attention_layers = nn.ModuleList([
            CrossModalAttention(hidden_size, num_heads)
            for _ in range(num_layers)
        ])

        # Visual prompt tokens
        num_prompts = config.get("num_visual_prompts", 16)
        self.visual_prompts = nn.Parameter(torch.randn(1, num_prompts, hidden_size))

        # Alignment projection heads
        self.vision_proj = nn.Linear(hidden_size, config.get("proj_size", 256))
        self.text_proj = nn.Linear(hidden_size, config.get("proj_size", 256))

        # Task-specific heads
        self.classifier = nn.Linear(hidden_size, config.get("num_classes", 2))
        self.generator = nn.Linear(hidden_size, config.get("vocab_size", 30522))

        # Contrastive loss
        self.temperature = nn.Parameter(torch.tensor(0.07))
        self.ce_loss = nn.CrossEntropyLoss()

    def encode_vision(self, pixel_values):
        vision_out = self.vision_encoder(pixel_values=pixel_values)
        vision_features = vision_out.last_hidden_state

        # Prepend visual prompt tokens
        batch_size = vision_features.size(0)
        prompts = self.visual_prompts.expand(batch_size, -1, -1)
        vision_features = torch.cat([prompts, vision_features], dim=1)

        return vision_features

    def encode_text(self, input_ids, attention_mask=None):
        text_out = self.text_encoder(input_ids=input_ids, attention_mask=attention_mask)
        return text_out.last_hidden_state

    def cross_modal_fusion(self, vision_features, text_features):
        fused = text_features
        for layer in self.cross_attention_layers:
            fused = layer(fused, vision_features)
        return fused

    def contrastive_loss(self, vision_features, text_features):
        v_proj = self.vision_proj(vision_features[:, 0])
        t_proj = self.text_proj(text_features[:, 0])

        v_proj = nn.functional.normalize(v_proj, dim=-1)
        t_proj = nn.functional.normalize(t_proj, dim=-1)

        logits = torch.matmul(v_proj, t_proj.t()) / self.temperature
        labels = torch.arange(logits.size(0), device=logits.device)
        loss = (self.ce_loss(logits, labels) + self.ce_loss(logits.t(), labels)) / 2
        return loss

    def forward(self, input_ids=None, attention_mask=None, pixel_values=None,
                labels=None, task="classify", **kwargs):
        vision_features = self.encode_vision(pixel_values)
        text_features = self.encode_text(input_ids, attention_mask)
        fused_features = self.cross_modal_fusion(vision_features, text_features)

        outputs = {}

        if task == "classify":
            logits = self.classifier(fused_features[:, 0])
            outputs["logits"] = logits
            if labels is not None:
                outputs["loss"] = self.ce_loss(logits, labels)
                outputs["accuracy"] = (logits.argmax(-1) == labels).float().mean().item()
            outputs["predictions"] = [{"label": l.item()} for l in logits.argmax(-1)]

        elif task == "generate":
            gen_logits = self.generator(fused_features)
            outputs["logits"] = gen_logits
            if labels is not None:
                outputs["loss"] = self.ce_loss(gen_logits.view(-1, gen_logits.size(-1)), labels.view(-1))

        # Add contrastive loss
        c_loss = self.contrastive_loss(vision_features, text_features)
        if "loss" in outputs:
            outputs["loss"] = outputs["loss"] + self.config.get("contrastive_weight", 0.1) * c_loss
        else:
            outputs["loss"] = c_loss

        return outputs

    def generate(self, input_ids=None, attention_mask=None, pixel_values=None,
                 max_length=50, **kwargs):
        vision_features = self.encode_vision(pixel_values)
        text_features = self.encode_text(input_ids, attention_mask)
        fused_features = self.cross_modal_fusion(vision_features, text_features)

        # Simple greedy decoding
        generated = []
        for i in range(fused_features.size(0)):
            gen_logits = self.generator(fused_features[i:i+1])
            tokens = gen_logits.argmax(-1).squeeze().tolist()
            if isinstance(tokens, int):
                tokens = [tokens]
            generated.append({"text": " ".join(str(t) for t in tokens[:max_length])})

        return {"predictions": generated}
