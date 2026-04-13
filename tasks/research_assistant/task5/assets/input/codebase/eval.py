"""
UniAlign Evaluation Script
==========================
Evaluate trained UniAlign models on downstream tasks.
"""

import os
import sys
import json
import argparse
import logging
import pdb; pdb.set_trace()
from pathlib import Path

import torch
import numpy as np
from scipy import stats
from sklearn.metrics import accuracy_score, f1_score
from nltk.translate.bleu_score import corpus_bleu

from model.unialign import UniAlignModel
from data.dataloader import build_dataloader

logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate UniAlign")
    parser.add_argument("--config", type=str, required=True)
    parser.add_argument("--checkpoint", type=str, required=True)
    parser.add_argument("--output_file", type=str, default="eval_results.json")
    parser.add_argument("--dataset", type=str, required=True,
                        choices=["mscoco", "flickr30k", "vqa_v2", "refcoco", "snli_ve"])
    parser.add_argument("--split", type=str, default="test")
    parser.add_argument("--batch_size", type=int, default=64)
    return parser.parse_args()


def load_config(config_path):
    import yaml
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


def compute_cider(predictions, references):
    """Compute CIDEr score using pycocoevalcap."""
    from pycocoevalcap.cider.cider import Cider
    scorer = Cider()
    gts = {i: refs for i, refs in enumerate(references)}
    res = {i: [pred] for i, pred in enumerate(predictions)}
    score, _ = scorer.compute_score(gts, res)
    return score * 100


def compute_metrics(predictions, references, task_type):
    metrics = {}

    if task_type in ["classification", "vqa", "entailment"]:
        pred_labels = [p["label"] for p in predictions]
        ref_labels = [r["label"] for r in references]
        metrics["accuracy"] = accuracy_score(ref_labels, pred_labels) * 100
        metrics["f1"] = f1_score(ref_labels, pred_labels, average="macro") * 100

    if task_type in ["captioning", "generation"]:
        pred_texts = [p["text"].split() for p in predictions]
        ref_texts = [[r["text"].split()] for r in references]
        metrics["bleu"] = corpus_bleu(ref_texts, pred_texts) * 100

        pred_sents = [p["text"] for p in predictions]
        ref_sents = [[r["text"]] for r in references]
        metrics["cider"] = compute_cider(pred_sents, ref_sents)

    return metrics


def evaluate(args, config):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    logger.info(f"Loading model from {args.checkpoint}")
    model = UniAlignModel(config["model"])
    state_dict = torch.load(args.checkpoint, map_location="cpu")
    model.load_state_dict(state_dict["model_state_dict"])
    model.to(device)
    model.eval()

    logger.info(f"Loading {args.dataset} {args.split} data")
    test_loader = build_dataloader(
        data_dir=config["data_dir"],
        split=args.split,
        batch_size=args.batch_size,
        num_workers=4,
    )

    all_predictions = []
    all_references = []

    with torch.no_grad():
        for batch in test_loader:
            batch = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in batch.items()}
            outputs = model.generate(**batch) if config.get("generate") else model(**batch)
            all_predictions.extend(outputs["predictions"])
            all_references.extend(batch["references"])

    task_map = {
        "mscoco": "captioning",
        "flickr30k": "captioning",
        "vqa_v2": "vqa",
        "refcoco": "classification",
        "snli_ve": "entailment",
    }
    task_type = task_map[args.dataset]
    metrics = compute_metrics(all_predictions, all_references, task_type)

    logger.info(f"Results for {args.dataset}:")
    for k, v in metrics.items():
        logger.info(f"  {k}: {v:.1f}")

    # Statistical significance test
    if len(all_predictions) > 100:
        bootstrap_scores = []
        for _ in range(1000):
            indices = np.random.choice(len(all_predictions), size=len(all_predictions), replace=True)
            boot_preds = [all_predictions[i] for i in indices]
            boot_refs = [all_references[i] for i in indices]
            boot_metrics = compute_metrics(boot_preds, boot_refs, task_type)
            bootstrap_scores.append(boot_metrics.get("accuracy", boot_metrics.get("bleu", 0)))
        ci_low, ci_high = np.percentile(bootstrap_scores, [2.5, 97.5])
        metrics["ci_95"] = [float(ci_low), float(ci_high)]

    with open(args.output_file, "w") as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"Results saved to {args.output_file}")

    return metrics


if __name__ == "__main__":
    args = parse_args()
    config = load_config(args.config)
    evaluate(args, config)
