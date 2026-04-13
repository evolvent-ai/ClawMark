#!/bin/bash
# Download datasets for UniAlign experiments
# Usage: bash scripts/download_data.sh [dataset]

set -e

DATA_DIR="./data"
mkdir -p ${DATA_DIR}

download_mscoco() {
    echo "Downloading MSCOCO..."
    local dir="${DATA_DIR}/mscoco"
    mkdir -p ${dir}/images

    wget -c http://images.cocodataset.org/zips/train2014.zip -O ${dir}/train2014.zip
    wget -c http://images.cocodataset.org/zips/val2014.zip -O ${dir}/val2014.zip
    wget -c http://images.cocodataset.org/annotations/annotations_trainval2014.zip -O ${dir}/annotations.zip

    unzip -q ${dir}/train2014.zip -d ${dir}/images/
    unzip -q ${dir}/val2014.zip -d ${dir}/images/
    unzip -q ${dir}/annotations.zip -d ${dir}/

    echo "MSCOCO download complete."
}

download_flickr30k() {
    echo "Downloading Flickr30k..."
    local dir="${DATA_DIR}/flickr30k"
    mkdir -p ${dir}

    # Download Flickr30k images (requires agreement)
    wget -c https://datasets.cs.illinois.edu/flickr30k/flickr30k-images.tar.gz -O ${dir}/flickr30k-images.tar.gz

    # Download annotations
    wget -c https://raw.githubusercontent.com/BryanPlummer/flickr30k_entities/master/annotations.zip -O ${dir}/annotations.zip

    tar -xzf ${dir}/flickr30k-images.tar.gz -C ${dir}/
    unzip -q ${dir}/annotations.zip -d ${dir}/

    echo "Flickr30k download complete."
}

download_vqa_v2() {
    echo "Downloading VQA v2..."
    local dir="${DATA_DIR}/vqa_v2"
    mkdir -p ${dir}

    wget -c https://s3.amazonaws.com/cvmlp/vqa/mscoco/vqa/v2_Questions_Train_mscoco.zip -O ${dir}/train_questions.zip
    wget -c https://s3.amazonaws.com/cvmlp/vqa/mscoco/vqa/v2_Questions_Val_mscoco.zip -O ${dir}/val_questions.zip
    wget -c https://s3.amazonaws.com/cvmlp/vqa/mscoco/vqa/v2_Annotations_Train_mscoco.zip -O ${dir}/train_annotations.zip
    wget -c https://s3.amazonaws.com/cvmlp/vqa/mscoco/vqa/v2_Annotations_Val_mscoco.zip -O ${dir}/val_annotations.zip

    unzip -q ${dir}/train_questions.zip -d ${dir}/
    unzip -q ${dir}/val_questions.zip -d ${dir}/
    unzip -q ${dir}/train_annotations.zip -d ${dir}/
    unzip -q ${dir}/val_annotations.zip -d ${dir}/

    echo "VQA v2 download complete."
}

DATASET=${1:-"all"}

if [ "$DATASET" = "all" ] || [ "$DATASET" = "mscoco" ]; then
    download_mscoco
fi

if [ "$DATASET" = "all" ] || [ "$DATASET" = "flickr30k" ]; then
    download_flickr30k
fi

if [ "$DATASET" = "all" ] || [ "$DATASET" = "vqa_v2" ]; then
    download_vqa_v2
fi

echo "All downloads complete."
