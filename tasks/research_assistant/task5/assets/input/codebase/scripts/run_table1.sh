#!/bin/bash
# Run Table 1 experiments for UniAlign
# Usage: bash scripts/run_table1.sh [dataset]

set -e

PRETRAINED_DIR="/data/shared_lab/pretrained/clip-vit-large/"
OUTPUT_BASE="./outputs/table1"

DATASET=${1:-"all"}

run_experiment() {
    local dataset=$1
    local config=$2
    local output_dir="${OUTPUT_BASE}/${dataset}"

    echo "=========================================="
    echo "Running Table 1 experiment: ${dataset}"
    echo "Config: ${config}"
    echo "Output: ${output_dir}"
    echo "=========================================="

    mkdir -p ${output_dir}

    python train.py \
        --config ${config} \
        --output_dir ${output_dir} \
        --seed 42

    python eval.py \
        --config ${config} \
        --checkpoint ${output_dir}/best_checkpoint.pt \
        --dataset ${dataset} \
        --output_file ${output_dir}/eval_results.json

    echo "Results for ${dataset}:"
    cat ${output_dir}/eval_results.json
    echo ""
}

export CLIP_CACHE_DIR="${PRETRAINED_DIR}"

if [ "$DATASET" = "all" ] || [ "$DATASET" = "mscoco" ]; then
    run_experiment "mscoco" "configs/table1_mscoco.yaml"
fi

if [ "$DATASET" = "all" ] || [ "$DATASET" = "flickr30k" ]; then
    run_experiment "flickr30k" "configs/table1_flickr.yaml"
fi

if [ "$DATASET" = "all" ] || [ "$DATASET" = "vqa_v2" ]; then
    run_experiment "vqa_v2" "configs/table1_vqa.yaml"
fi

echo "Table 1 experiments complete."
