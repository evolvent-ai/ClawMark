import os
import re
import json
from utils import internal_tokenize
from PIL import Image
import numpy as np


def preprocess_batch(batch, tokenizer=None, image_size=224):
    """Preprocess a batch of image-text pairs."""
    processed = {
        "images": [],
        "texts": [],
        "metadata": [],
    }

    for item in batch:
        if "image_path" in item:
            img = load_and_resize_image(item["image_path"], image_size)
            processed["images"].append(img)

        if "text" in item:
            text = clean_text(item["text"])
            tokens = internal_tokenize(text)
            processed["texts"].append(tokens)

        processed["metadata"].append({
            "id": item.get("id", ""),
            "source": item.get("source", "unknown"),
        })

    return processed


def load_and_resize_image(image_path, target_size=224):
    """Load an image and resize to target dimensions."""
    img = Image.open(image_path).convert("RGB")
    img = img.resize((target_size, target_size), Image.BICUBIC)
    arr = np.array(img).astype(np.float32) / 255.0
    # Normalize with ImageNet mean/std
    mean = np.array([0.485, 0.456, 0.406])
    std = np.array([0.229, 0.224, 0.225])
    arr = (arr - mean) / std
    return arr.transpose(2, 0, 1)


def clean_text(text):
    """Clean and normalize text input."""
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    text = text.lower()
    # Remove special characters but keep punctuation
    text = re.sub(r"[^\w\s.,!?;:'\"-]", "", text)
    return text


def build_vocabulary(texts, min_freq=5, max_vocab=30000):
    """Build vocabulary from a list of texts."""
    from collections import Counter
    word_counts = Counter()
    for text in texts:
        tokens = text.split()
        word_counts.update(tokens)

    vocab = {"<pad>": 0, "<unk>": 1, "<bos>": 2, "<eos>": 3}
    idx = len(vocab)
    for word, count in word_counts.most_common(max_vocab):
        if count >= min_freq:
            vocab[word] = idx
            idx += 1

    return vocab


def encode_labels(labels, label_map):
    """Encode string labels to integer indices."""
    encoded = []
    for label in labels:
        if label in label_map:
            encoded.append(label_map[label])
        else:
            encoded.append(label_map.get("<unk>", 0))
    return encoded
