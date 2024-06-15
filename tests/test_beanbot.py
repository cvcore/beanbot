import pytest
from copy import deepcopy
from pathlib import Path
from beancount.core.data import Transaction
from beancount.loader import load_file
from beanbot.common.configs import BeanbotConfig
from beanbot.common.types import Transactions
from beanbot.ops.extractor import TransactionDescriptionExtractor
from beanbot.file.saver import EntryFileSaver
from beanbot.tests.dataloader import DataLoader
from beanbot.tests.metrics import PrecisionScore
from beanbot.vectorizer.bag_of_words_vectorizer import BagOfWordVectorizer

from beanbot.classifier.decision_tree_transaction_classifier import \
    DecisionTreeTransactionClassifier
from beanbot.classifier.mapping_transaction_classifier import \
    MappingTransactionClassifier
from beanbot.classifier.meta_transaction_classifier import \
    MetaTransactionClassifier


global_config = BeanbotConfig.get_global()
global_config.parse_file(str(Path(__file__).parent / 'data' / 'main.bean'))
TEST_FILE_SAMPLE = global_config['main-file']


def test_vectorizer():
    loader = DataLoader(TEST_FILE_SAMPLE, ratio_removal=0.3)

    for test_set in loader.load():
        transactions = test_set.input_transactions

        vectorizer = BagOfWordVectorizer()
        vectorizer.fit_dictionary(transactions)
        vec_transactions = vectorizer.vectorize(transactions)

        print(f"Vec transaction shape: {vec_transactions.vec.shape}")
        assert vec_transactions.vec.shape[0] == len(transactions)
        print(f"Vec label shape: {vec_transactions.label.shape}")
        assert vec_transactions.label.shape[0] == len(transactions)
        print(f"Testing vector shape... ", end='')
        assert vectorizer.vectorize([transactions[0]]).vec.shape[1] == vec_transactions.vec.shape[1]
        print(f"passed")


def test_classifier():
    loader = DataLoader(TEST_FILE_SAMPLE, ratio_removal=0.3)

    for test_set in loader.load():
        input_transactions = test_set.input_transactions
        options_map = test_set.options_map

        input_transactions_safeguard = deepcopy(input_transactions)

        # classifier = DecisionTreeTransactionClassifier(options_map)
        classifier = MetaTransactionClassifier(options_map)
        global_config = BeanbotConfig.get_global()
        fallback_txn_file = global_config['fallback-transaction-file']
        file_saver = EntryFileSaver(default_location=fallback_txn_file)
        file_saver.learn_filename(input_transactions)
        test_set.pred_transactions = classifier.train_predict(input_transactions)
        assert input_transactions == input_transactions_safeguard, "Classifier is not supposed to modify transactions in place!"
        file_saver.save(test_set.pred_transactions, dryrun=True)
        metrics_val = PrecisionScore.calculate(test_set)
        print(f"Precision: {metrics_val}")
