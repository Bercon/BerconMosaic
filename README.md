# BerconMosaic
Python script to generate picture mosaics

## Setup

Run commands from Git Bash. Tested on Python 3.10.

Setup environment
```
python -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
```

## How to use

If venv environment isn't loaded, start with
```
source venv/Scripts/activate
```

Modify `config.yaml` to have proper data paths and other settings.

Create mosaic image with:
```
python mosaic.py
```

## TODO:

* Multiprocessing might pickle the palette for each tile, refactor it