import os
from beanbot.classifier.transformer_knn_classifier import (
    TransformerKNNAccountClassifier,
)
from beanbot.helper import logger


def get_predictor_singleton(options_map: dict):
    if not hasattr(get_predictor_singleton, "instance"):
        # get_predictor_singleton.instance = DecisionTreeAccountClassifier(options_map)
        get_predictor_singleton.instance = TransformerKNNAccountClassifier(options_map)
        if MODEL_PATH := os.environ.get("BEANBOT_MODEL_PATH"):
            if os.path.exists(MODEL_PATH):
                logger.info(f"Loading model from {MODEL_PATH}")
                get_predictor_singleton.instance.load_model(MODEL_PATH)
    return get_predictor_singleton.instance
