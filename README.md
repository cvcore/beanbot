# BeanBot: Smart Predictor for Beancount Transactions

![Action dispatcher](https://github.com/cvcore/beanbot/actions/workflows/actions-dispatcher.yml/badge.svg)

This repository implements a smart predictor to automatically categorize new beancount transactions with a model learned from historic data. It works by comparing the description of each new transactions with previous ones and assign a predicted category to each new transaction. The description of each transaction is supposed to be imported automatically from your bank.

Please note: this project is currently under development.

# Setup

Poetry is used to manage the dependencies of this project. To install poetry, please refer to the [official documentation](https://python-poetry.org/docs/).

For the following commands, we expect `poetry` to be available in your shell.

# Usage

To use this tool, you should have an existing beancount file where all your historic beancount records are saved, and some new transaction files (can be `.csv`, `.xls`, etc depending on your bank) downloaded from your bank portal.

Then, call the beancount importer with BeanBot as a plugin:

```
poetry run bean-extract tests/data/import.config -e tests/data/main.bean tests/data/raw
```

You can find currently implemented importers in the [src/beanbot/importer] directory and you are welcomed to submit a PR if the importer for your bank is missing.

# Customization

Customization can be done by changing the configuration file `import.config`, where `beanbot` can be applied as a hook to the beancount importer:

```
CONFIG = [
    apply_hooks(deutsche_bank.Importer('Assets:Checking:DeutscheBank'), [BeanBotPredictionHook()]),
]
```

This will call the `BeanBotPredictionHook` after the importer has finished importing the transactions. The hook will then predict the category of each transaction and will return balanced entries.

# Testing

```bash
poetry run pytest tests/
```

# Author

Chengxin Wang [w@hxdl.org](mailto:w@hxdl.org)
