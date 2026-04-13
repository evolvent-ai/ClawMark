"""Data augmentation utilities for UniAlign training."""

import random
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance


class RandomAugment:
    """Apply random augmentations to images during training."""

    def __init__(self, num_ops=2, magnitude=9):
        self.num_ops = num_ops
        self.magnitude = magnitude
        self.augment_pool = [
            self.random_horizontal_flip,
            self.random_crop_and_resize,
            self.color_jitter,
            self.gaussian_blur,
            self.random_grayscale,
            self.random_rotation,
        ]

    def __call__(self, image):
        ops = random.choices(self.augment_pool, k=self.num_ops)
        for op in ops:
            image = op(image)
        return image

    def random_horizontal_flip(self, image, p=0.5):
        if random.random() < p:
            return image.transpose(Image.FLIP_LEFT_RIGHT)
        return image

    def random_crop_and_resize(self, image, scale=(0.8, 1.0)):
        w, h = image.size
        area = w * h
        target_area = random.uniform(scale[0], scale[1]) * area
        aspect_ratio = random.uniform(3.0 / 4.0, 4.0 / 3.0)

        new_w = int(round(np.sqrt(target_area * aspect_ratio)))
        new_h = int(round(np.sqrt(target_area / aspect_ratio)))

        new_w = min(new_w, w)
        new_h = min(new_h, h)

        x = random.randint(0, w - new_w)
        y = random.randint(0, h - new_h)

        image = image.crop((x, y, x + new_w, y + new_h))
        image = image.resize((w, h), Image.BICUBIC)
        return image

    def color_jitter(self, image, brightness=0.4, contrast=0.4, saturation=0.4):
        enhancers = [
            (ImageEnhance.Brightness, brightness),
            (ImageEnhance.Contrast, contrast),
            (ImageEnhance.Color, saturation),
        ]
        random.shuffle(enhancers)
        for enhancer_cls, factor in enhancers:
            factor = random.uniform(max(0, 1 - factor), 1 + factor)
            image = enhancer_cls(image).enhance(factor)
        return image

    def gaussian_blur(self, image, p=0.5):
        if random.random() < p:
            radius = random.uniform(0.1, 2.0)
            image = image.filter(ImageFilter.GaussianBlur(radius=radius))
        return image

    def random_grayscale(self, image, p=0.2):
        if random.random() < p:
            image = image.convert("L").convert("RGB")
        return image

    def random_rotation(self, image, degrees=15):
        angle = random.uniform(-degrees, degrees)
        image = image.rotate(angle, resample=Image.BICUBIC, fillcolor=(128, 128, 128))
        return image


class TextAugment:
    """Simple text augmentation for robustness."""

    def __init__(self, p_drop=0.1, p_swap=0.05):
        self.p_drop = p_drop
        self.p_swap = p_swap

    def __call__(self, text):
        words = text.split()
        if len(words) <= 2:
            return text

        # Random word dropout
        words = [w for w in words if random.random() > self.p_drop]
        if not words:
            return text

        # Random word swap
        for i in range(len(words) - 1):
            if random.random() < self.p_swap:
                words[i], words[i + 1] = words[i + 1], words[i]

        return " ".join(words)
