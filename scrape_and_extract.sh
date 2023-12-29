#!/bin/bash
set -e

mkdir -p data/{raw,splits}

python scrape.py

for split in train dev test; do
    python extract.py splits/$split.hash.json $split
done
