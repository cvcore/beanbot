from beanbot.classifier.decision_tree_transaction_classifier import (
    DecisionTreeAccountClassifier,
)


def get_predictor_singleton(options_map: dict):
    if not hasattr(get_predictor_singleton, "instance"):
        get_predictor_singleton.instance = DecisionTreeAccountClassifier(options_map)
    return get_predictor_singleton.instance
