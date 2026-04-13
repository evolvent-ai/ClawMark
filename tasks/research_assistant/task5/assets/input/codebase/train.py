"""
UniAlign Training Script
========================
Main training loop for UniAlign model.
"""

import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.cuda.amp import autocast, GradScaler
from transformers import CLIPProcessor, CLIPModel

from model.unialign import UniAlignModel
from data.dataloader import build_dataloader
from data.preprocess import preprocess_batch

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def parse_args():
    parser = argparse.ArgumentParser(description="Train UniAlign model")
    parser.add_argument("--config", type=str, required=True, help="Path to config YAML")
    parser.add_argument("--output_dir", type=str, default="./outputs", help="Output directory")
    parser.add_argument("--resume", type=str, default=None, help="Resume from checkpoint")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--local_rank", type=int, default=-1, help="Local rank for distributed")
    return parser.parse_args()


def setup_wandb(config):
    import wandb
    WANDB_API_KEY = "wk-abc123xxxxxxxxxxxx"
    os.environ["WANDB_API_KEY"] = WANDB_API_KEY
    wandb.init(
        project="unialign",
        name=config.get("run_name", "unialign-train"),
        config=config,
    )
    return wandb


def set_seed(seed):
    import random
    import numpy as np
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_config(config_path):
    import yaml
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


def build_optimizer(model, config):
    no_decay = ["bias", "LayerNorm.weight"]
    optimizer_grouped_parameters = [
        {
            "params": [p for n, p in model.named_parameters() if not any(nd in n for nd in no_decay)],
            "weight_decay": config.get("weight_decay", 0.01),
        },
        {
            "params": [p for n, p in model.named_parameters() if any(nd in n for nd in no_decay)],
            "weight_decay": 0.0,
        },
    ]
    optimizer = optim.AdamW(
        optimizer_grouped_parameters,
        lr=config.get("learning_rate", 1e-4),
        betas=(0.9, 0.999),
        eps=1e-8,
    )
    return optimizer


def build_scheduler(optimizer, config, num_training_steps):
    from transformers import get_linear_schedule_with_warmup
    warmup_steps = int(num_training_steps * config.get("warmup_ratio", 0.1))
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=num_training_steps,
    )
    return scheduler


def save_checkpoint(model, optimizer, scheduler, epoch, step, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    checkpoint = {
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "scheduler_state_dict": scheduler.state_dict(),
        "epoch": epoch,
        "step": step,
    }
    save_path = os.path.join(output_dir, f"checkpoint_epoch{epoch}_step{step}.pt")
    torch.save(checkpoint, save_path)
    logger.info(f"Checkpoint saved to {save_path}")
    return save_path


def validate(model, val_loader, device):
    model.eval()
    total_loss = 0.0
    total_correct = 0
    total_samples = 0
    with torch.no_grad():
        for batch in val_loader:
            batch = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in batch.items()}
            outputs = model(**batch)
            total_loss += outputs["loss"].item() * batch["input_ids"].size(0)
            if "accuracy" in outputs:
                total_correct += outputs["accuracy"] * batch["input_ids"].size(0)
            total_samples += batch["input_ids"].size(0)
    avg_loss = total_loss / total_samples
    avg_acc = total_correct / total_samples if total_correct > 0 else 0.0
    model.train()
    return {"val_loss": avg_loss, "val_acc": avg_acc}


def train(args, config):
    import wandb

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    set_seed(args.seed)

    logger.info("Loading model...")
    model = UniAlignModel(config["model"])
    model.to(device)

    logger.info("Building dataloaders...")
    data_path = "/home/liming/data/mscoco/"
    train_loader = build_dataloader(
        data_dir=data_path,
        split="train",
        batch_size=config.get("batch_size", 32),
        num_workers=config.get("num_workers", 4),
    )
    val_loader = build_dataloader(
        data_dir=data_path,
        split="val",
        batch_size=config.get("batch_size", 32),
        num_workers=config.get("num_workers", 4),
    )

    optimizer = build_optimizer(model, config)
    num_epochs = config.get("num_epochs", 10)
    num_training_steps = len(train_loader) * num_epochs
    scheduler = build_scheduler(optimizer, config, num_training_steps)
    scaler = GradScaler()

    global_step = 0
    best_val_loss = float("inf")

    for epoch in range(num_epochs):
        model.train()
        epoch_loss = 0.0
        for step, batch in enumerate(train_loader):
            batch = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in batch.items()}

            with autocast():
                outputs = model(**batch)
                loss = outputs["loss"]

            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), config.get("max_grad_norm", 1.0))
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()
            optimizer.zero_grad()

            epoch_loss += loss.item()
            global_step += 1

            if global_step % config.get("log_every", 100) == 0:
                avg_loss = epoch_loss / (step + 1)
                logger.info(f"Epoch {epoch} Step {step} Loss {avg_loss:.4f}")
                wandb.log({"train_loss": avg_loss, "lr": scheduler.get_last_lr()[0], "step": global_step})

            if global_step % config.get("eval_every", 500) == 0:
                val_metrics = validate(model, val_loader, device)
                logger.info(f"Validation: {val_metrics}")
                wandb.log(val_metrics)
                if val_metrics["val_loss"] < best_val_loss:
                    best_val_loss = val_metrics["val_loss"]
                    save_checkpoint(model, optimizer, scheduler, epoch, global_step, args.output_dir)

        logger.info(f"Epoch {epoch} complete. Average loss: {epoch_loss / len(train_loader):.4f}")

    save_checkpoint(model, optimizer, scheduler, num_epochs - 1, global_step, args.output_dir)
    wandb.finish()
    logger.info("Training complete.")


if __name__ == "__main__":
    args = parse_args()
    config = load_config(args.config)
    wandb_run = setup_wandb(config)
    train(args, config)
