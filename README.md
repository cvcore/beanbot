# BeanBot: Smart Predictor for Beancount Transactions

This repository implements a smart predictor to automatically categorize new beancount transactions with a model learned from historic data. It works by comparing the description of each new transactions with previous ones and assign a predicted category to each new transaction. The description of each transaction is supposed to be imported automatically from your bank.

Please note: this project is currently under development.

# Setup

Clone this repository, setup the your python virtual environment and then:

```
pip install -r requirements.txt
pip install .
```

This will install `beanbot` as a python library and its necessary dependencies in your python path.

# Usage

To use this tool, you should have a **main** beancount file where all your historic beancount records are saved, and a **new** raw transaction file (can be `.csv`, `.xls`, etc depending on your bank) downloaded from your bank portal.

Then, call the beancount importer with BeanBot as a plugin:

```
bean-extract tests/data/import.config -e tests/data/main.bean tests/data/raw
```

You can find currently implemented importers in the [src/beanbot/importer] directory and you are welcomed to submit a PR if the importer for your bank is missing.

# Testing

```bash
python -m unittest tests/test_beanbot.py
```

# Author

Chengxin Wang [w@hxdl.org](mailto:w@hxdl.org)
