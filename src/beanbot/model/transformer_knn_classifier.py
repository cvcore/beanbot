import numpy as np
from sklearn.neighbors import KNeighborsClassifier
import pickle
import os
from typing import List, Tuple
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class TransformerKNNClassifier:
    def __init__(
        self,
        embedding_model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        n_neighbors: int = 5,
        min_confidence: float = 0.6,
    ):
        """
        Initialize the multilingual transaction classifier.

        Args:
            embedding_model_name: Name of the sentence-transformers model to use
            n_neighbors: Number of neighbors to use for kNN
            min_confidence: Minimum confidence threshold for predictions
        """
        try:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(embedding_model_name)
            logging.info(f"Loaded embedding model: {embedding_model_name}")
        except ImportError:
            logging.error(
                "Please install sentence-transformers: pip install sentence-transformers"
            )
            raise

        self.knn = KNeighborsClassifier(
            n_neighbors=n_neighbors, weights="distance", metric="cosine"
        )
        self.embeddings = None
        self.texts = []
        self.labels = []
        self.n_neighbors = n_neighbors
        self.min_confidence = min_confidence
        self.is_fitted = False

    def _get_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a single text"""
        return self.model.encode(text)

    def _get_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts"""
        return self.model.encode(texts)

    def fit(self, texts: List[str], labels: List[str]) -> None:
        """
        Train the classifier on historical transaction data.

        Args:
            texts: List of transaction descriptions
            labels: List of corresponding counter accounts
        """
        logging.info(f"Training on {len(texts)} examples")
        self.texts = texts.copy()
        self.labels = labels.copy()

        # Generate embeddings
        self.embeddings = self._get_embeddings(self.texts)

        # Train kNN
        self.knn.fit(self.embeddings, self.labels)
        self.is_fitted = True
        logging.info("Model training completed")

    def update(self, new_text: str, new_label: str) -> None:
        """
        Update the classifier with a new labeled example.

        Args:
            new_text: New transaction description
            new_label: Corresponding counter account
        """
        logging.info(f"Updating model with new example: '{new_text}' -> {new_label}")

        # Add new example to our dataset
        self.texts.append(new_text)
        self.labels.append(new_label)

        # Get embedding for new example
        new_embedding = self._get_embedding(new_text).reshape(1, -1)

        if self.embeddings is None:
            self.embeddings = new_embedding
        else:
            self.embeddings = np.vstack([self.embeddings, new_embedding])

        # Retrain kNN with updated dataset
        self.knn.fit(self.embeddings, self.labels)
        logging.info("Model updated successfully")

    def predict(self, text: str) -> Tuple[str, float]:
        """
        Predict the counter account for a transaction.

        Args:
            text: Transaction description

        Returns:
            Tuple of (predicted_label, confidence_score)
        """
        if not self.is_fitted:
            raise ValueError("Model is not fitted yet. Call fit() first.")

        # Get embedding for the text
        embedding = self._get_embedding(text).reshape(1, -1)

        # Get nearest neighbors
        distances, indices = self.knn.kneighbors(embedding)

        # Get labels of nearest neighbors
        neighbor_labels = [self.labels[i] for i in indices[0]]

        # Convert distances to similarities (1 - distance for cosine)
        similarities = 1 - distances[0]

        # Get most common label and its confidence
        unique_labels = set(neighbor_labels)
        label_confidence = {}
        for label in unique_labels:
            confidence = sum(
                similarities[i]
                for i, idx in enumerate(indices[0])
                if self.labels[idx] == label
            )
            label_confidence[label] = confidence

        # Get label with highest confidence
        predicted_label = max(label_confidence, key=label_confidence.get)
        confidence = label_confidence[predicted_label] / sum(similarities)

        if confidence < self.min_confidence:
            logging.warning(
                f"Low confidence prediction ({confidence:.2f}): {predicted_label}"
            )

        return predicted_label, confidence

    def predict_batch(self, texts: List[str]) -> List[Tuple[str, float]]:
        """
        Predict counter accounts for multiple transactions.

        Args:
            texts: List of transaction descriptions

        Returns:
            List of (predicted_label, confidence_score) tuples
        """
        return [self.predict(text) for text in texts]

    def save(self, filepath: str) -> None:
        """
        Save the classifier to disk.

        Args:
            filepath: Path to save the model
        """
        model_dir = os.path.dirname(filepath)
        if model_dir and not os.path.exists(model_dir):
            os.makedirs(model_dir)

        data = {
            "texts": self.texts,
            "labels": self.labels,
            "embeddings": self.embeddings,
            "n_neighbors": self.n_neighbors,
            "min_confidence": self.min_confidence,
            "is_fitted": self.is_fitted,
        }

        with open(filepath, "wb") as f:
            pickle.dump(data, f)

        logging.info(f"Model saved to {filepath}")

    @classmethod
    def load(
        cls,
        filepath: str,
        embedding_model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
    ) -> "TransformerKNNClassifier":
        """
        Load a saved classifier from disk.

        Args:
            filepath: Path to the saved model
            embedding_model_name: Name of the sentence transformer model

        Returns:
            Loaded TransactionClassifier
        """
        with open(filepath, "rb") as f:
            data = pickle.load(f)

        classifier = cls(
            embedding_model_name=embedding_model_name,
            n_neighbors=data["n_neighbors"],
            min_confidence=data["min_confidence"],
        )

        classifier.texts = data["texts"]
        classifier.labels = data["labels"]
        classifier.embeddings = data["embeddings"]
        classifier.is_fitted = data["is_fitted"]

        if classifier.is_fitted:
            classifier.knn.fit(classifier.embeddings, classifier.labels)

        logging.info(f"Model loaded from {filepath}")
        return classifier
