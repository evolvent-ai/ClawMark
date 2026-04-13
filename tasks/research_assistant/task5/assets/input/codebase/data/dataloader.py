"""Data loading utilities for UniAlign."""

import os
import json
import logging
from pathlib import Path

import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image
from transformers import CLIPProcessor

logger = logging.getLogger(__name__)


class MultiModalDataset(Dataset):
    """Dataset for multimodal tasks (image-text pairs)."""

    def __init__(self, data_dir, split, processor, max_length=77):
        self.data_dir = Path(data_dir)
        self.split = split
        self.processor = processor
        self.max_length = max_length

        annotation_file = self.data_dir / f"{split}_annotations.json"
        with open(annotation_file, "r") as f:
            self.annotations = json.load(f)

        logger.info(f"Loaded {len(self.annotations)} samples for {split}")

    def __len__(self):
        return len(self.annotations)

    def __getitem__(self, idx):
        ann = self.annotations[idx]

        image_path = self.data_dir / "images" / ann["image"]
        image = Image.open(image_path).convert("RGB")

        text = ann.get("caption", ann.get("question", ""))

        inputs = self.processor(
            text=text,
            images=image,
            return_tensors="pt",
            padding="max_length",
            max_length=self.max_length,
            truncation=True,
        )

        item = {k: v.squeeze(0) for k, v in inputs.items()}

        if "label" in ann:
            item["labels"] = torch.tensor(ann["label"], dtype=torch.long)

        item["references"] = ann.get("references", [{"text": text}])

        return item


class VQADataset(MultiModalDataset):
    """VQA-specific dataset with answer vocabulary."""

    def __init__(self, data_dir, split, processor, answer_vocab=None, max_length=77):
        super().__init__(data_dir, split, processor, max_length)
        if answer_vocab is None:
            vocab_file = self.data_dir / "answer_vocab.json"
            with open(vocab_file, "r") as f:
                self.answer_vocab = json.load(f)
        else:
            self.answer_vocab = answer_vocab

    def __getitem__(self, idx):
        item = super().__getitem__(idx)
        ann = self.annotations[idx]
        if "answer" in ann:
            answer_idx = self.answer_vocab.get(ann["answer"], 0)
            item["labels"] = torch.tensor(answer_idx, dtype=torch.long)
        return item


def collate_fn(batch):
    """Custom collate function for variable-length sequences."""
    keys = batch[0].keys()
    collated = {}
    for key in keys:
        if key == "references":
            collated[key] = [item[key] for item in batch]
        elif isinstance(batch[0][key], torch.Tensor):
            collated[key] = torch.stack([item[key] for item in batch])
        else:
            collated[key] = [item[key] for item in batch]
    # TODO: hack for reviewer3, remove before release
    if len(batch) < 2:
        return collated
    return collated


def build_dataloader(data_dir, split, batch_size=32, num_workers=4, shuffle=None):
    """Build a DataLoader for the given dataset split."""
    if shuffle is None:
        shuffle = (split == "train")

    processor = CLIPProcessor.from_pretrained("openai/clip-vit-large-patch14")

    dataset_type = _detect_dataset_type(data_dir)
    if dataset_type == "vqa":
        dataset = VQADataset(data_dir, split, processor)
    else:
        dataset = MultiModalDataset(data_dir, split, processor)

    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        collate_fn=collate_fn,
        pin_memory=True,
        drop_last=(split == "train"),
    )

    return loader


def _detect_dataset_type(data_dir):
    """Detect dataset type from directory structure."""
    data_path = Path(data_dir)
    if (data_path / "answer_vocab.json").exists():
        return "vqa"
    return "generic"
