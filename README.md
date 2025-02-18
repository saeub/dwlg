# DWLG

This repository contains scripts for scraping and converting data from German language courses on the *Deutsche Welle – Learn German* website, and for reproducing the DWLG dataset.

## TL;DR

To reproduce the DWLG dataset, the easiest way is to use the Docker image on DockerHub. You only need to install [Docker](https://docs.docker.com/get-docker/) and run the following commands.

```bash
mkdir data
docker run --rm -v "$PWD/data:/app/data" saeub/dwlg
```

The raw data will first be downloaded into `data/raw/` and then extracted, converted, and split into `data/splits/{train,dev,test}.jsonl`.

## Requirements for running without Docker

If you don't want to use Docker, or if you want to modify the source code, the following steps are required:

- Install [Python >= 3.10](https://www.python.org/downloads/) as well as [Google Chrome](https://www.google.com/chrome/) and [ChromeDriver](https://chromedriver.chromium.org/).
- Clone this repository: `git clone https://github.com/saeub/dwlg`
- Install Python dependencies: `pip install -r requirements.txt` (virtual environment recommended)

## Scripts

### `scrape_and_extract.sh`

**Usage with Docker:** `docker run --rm -v "$PWD/data:/app/data" saeub/dwlg` (folder `data/` needs to exist in working directory)

**Usage without Docker:** `bash scrape_and_extract.sh`

This script runs `scrape.py` and `extract.py` to reproduce the DWLG dataset. Data will be stored in `data/`.

### `scrape.py`

**Usage with Docker:** `docker run --rm -v "$PWD/data:/app/data" saeub/dwlg python scrape.py`

**Usage without docker:** `python scrape.py`

This script downloads all the "Top-Thema" lessons and saves the raw data under `data/raw/`.

> **NOTE:** `scrape.py` will not re-download lessons that already exists under `data/raw/`. If you want to re-download everything, remove all the files in `data/raw/`.

### `extract.py`

**Usage with docker:** `docker run --rm -v "$PWD/data:/app/data" saeub/dwlg python extract.py <HASH-FILE.json> <SPLIT-NAME>`

**Usage without docker:** `python extract.py <HASH-FILE.json> <SPLIT-NAME>`

This script needs to be run after `scrape.py` and converts the raw data into the DWLG JSONL format.

- `<HASH-FILE.json>` is the path to a JSON file containing the IDs and hashes of the lessons to be extracted. The hash files for DWLG are available in `splits/`. Use `python extract.py splits/all.json all` to extract all available data (including the most recent lessons that are not part of DWLG).
- `<SPLIT-NAME>` is the name of the split. The resulting JSONL file will be stored as `data/splits/<SPLIT-NAME>.jsonl`.

> **NOTE:** The script will warn you about hash mismatches when the data you scraped does not match the data in DWLG. The text or items in these lessons may have been changed since the latest version of DWLG. See the change log below for known changes.

## Building the docker image

Instead of pulling the image from DockerHub, you can build it yourself:

```bash
docker build -t saeub/dwlg .
```

## DWLG change log

The following list contains known changes that *Deutsche Welle* made to courses that are part of the DWLG dataset (since May 2023). These changes are not reflected in the hash files in `splits/` and will therefore cause a hash mismatch when running the `extract.py` script:

- Lesson 64273452 (`dev`): A missing whitespace was inserted.

## Citation

If you use this dataset, please cite the following paper:

```bibtex
@inproceedings{sauberli-clematide-2024-automatic,
    title = "Automatic Generation and Evaluation of Reading Comprehension Test Items with Large Language Models",
    author = {S{\"a}uberli, Andreas  and
      Clematide, Simon},
    editor = "Wilkens, Rodrigo  and
      Cardon, R{\'e}mi  and
      Todirascu, Amalia  and
      Gala, N{\'u}ria",
    booktitle = "Proceedings of the 3rd Workshop on Tools and Resources for People with REAding DIfficulties (READI) @ LREC-COLING 2024",
    month = may,
    year = "2024",
    address = "Torino, Italia",
    publisher = "ELRA and ICCL",
    url = "https://aclanthology.org/2024.readi-1.3/",
    pages = "22--37"
}
```
