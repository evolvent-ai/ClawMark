#!/usr/bin/env python3
"""UniAlign evaluation script.

Usage:
    python eval.py --config configs/table1_all.yaml --checkpoint outputs/best.pt --dataset vqa_v2
    python eval.py --config configs/table1_all.yaml --checkpoint outputs/best.pt --dataset all
"""
import argparse
import os
import logging
import yaml
import json
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SUPPORTED_DATASETS = ["mscoco", "flickr30k", "vqa_v2", "refcoco", "snli_ve", "gqa"]
METRICS = ["acc", "f1", "bleu", "cider"]


def load_config(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def load_model(cfg, checkpoint_path):
    """Load trained model from checkpoint."""
    logger.info(f"Loading model from {checkpoint_path}")
    return None


def evaluate_dataset(model, dataset_name, cfg):
    """Evaluate model on a specific dataset."""
    logger.info(f"Evaluating on {dataset_name}...")
    results = {}
    for metric in METRICS:
        results[metric] = 0.0  # Placeholder
    return results


def compute_error_bars(results_per_seed):
    """Compute mean and std across seeds."""
    means = {}
    stds = {}
    for metric in METRICS:
        values = [r[metric] for r in results_per_seed]
        means[metric] = np.mean(values)
        stds[metric] = np.std(values)
    return means, stds


def main():
    parser = argparse.ArgumentParser(description="UniAlign Evaluation")
    parser.add_argument("--config", type=str, required=True)
    parser.add_argument("--checkpoint", type=str, required=True)
    parser.add_argument("--dataset", type=str, default="all",
                        help="Dataset to evaluate on, or 'all'")
    parser.add_argument("--output_file", type=str, default="eval_results.json")
    args = parser.parse_args()

    cfg = load_config(args.config)
    model = load_model(cfg, args.checkpoint)

    datasets = SUPPORTED_DATASETS if args.dataset == "all" else [args.dataset]

    all_results = {}
    for ds in datasets:
        results = evaluate_dataset(model, ds, cfg)
        all_results[ds] = results
        logger.info(f"  {ds}: {results}")

    with open(args.output_file, "w") as f:
        json.dump(all_results, f, indent=2)
    logger.info(f"Results saved to {args.output_file}")


if __name__ == "__main__":
    main()
