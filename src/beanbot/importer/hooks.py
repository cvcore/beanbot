import logging
from functools import wraps
from typing import List

from beancount.loader import load_file
from beancount.core.data import Entries
from beancount.ingest.importer import ImporterProtocol
from beanbot.classifier.meta_transaction_classifier import MetaTransactionClassifier
from beanbot.ops.filter import PredictedTransactionFilter, TransactionFilter
from beanbot.ops.file_saver import TransactionFileSaver
from beanbot.common.configs import BeanbotConfig

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class ImporterHook:
    """Interface for an importer hook."""

    def __call__(self, importer: ImporterProtocol, file: str, imported_entries: Entries, existing_entries: Entries) -> Entries:
        """Apply the hook and modify the imported entries.
        Args:
            importer: The importer that this hooks is being applied to.
            file: The file that is being imported.
            imported_entries: The current list of imported entries.
            existing_entries: The existing entries, as passed to the extract
                function.
        Returns:
            The updated imported entries.
        """
        raise NotImplementedError


def apply_hooks(importer: ImporterProtocol, hooks: List[ImporterHook]) -> ImporterProtocol:
    """Apply a list of importer hooks to an importer.
    Args:
        importer: An importer instance.
        hooks: A list of hooks, each a callable object.
    """

    unpatched_extract = importer.extract

    @wraps(unpatched_extract)
    def patched_extract_method(file, existing_entries=None):
        logger.debug("Calling the importer's extract method.")
        imported_entries = unpatched_extract(
            file, existing_entries=existing_entries
        )

        for hook in hooks:
            imported_entries = hook(
                importer, file, imported_entries, existing_entries
            )

        return imported_entries

    importer.extract = patched_extract_method
    return importer


class BeanBotPredictionHook(ImporterHook):
    """Interface for an importer hook."""

    def __call__(self, importer: ImporterProtocol, file: str, imported_entries: Entries, existing_entries: Entries) -> Entries:
        """Apply the hook and modify the imported entries.
        Args:
            importer: The importer that this hooks is being applied to.
            file: The file that is being imported.
            imported_entries: The current list of imported entries.
            existing_entries: The existing entries, as passed to the extract
                function.
        Returns:
            The updated imported entries.
        """

        # dirty: consider removing options_map or specify it in a config file
        global_config = BeanbotConfig.get_global()
        global_config.parse_entries(existing_entries)
        main_file = global_config['main-file']
        _, _, options_map = load_file(main_file)

        saver = TransactionFileSaver(global_config['fallback-transaction-file'])

        entries_all = [*imported_entries, *existing_entries]
        transactions_all = TransactionFilter().filter(entries_all)
        transactions_existing = TransactionFilter().filter(existing_entries)
        saver.learn_filename(transactions_existing)

        classifier = MetaTransactionClassifier(options_map)
        pred_entries = classifier.train_predict(transactions_all)
        pred_entries = PredictedTransactionFilter().filter(pred_entries)

        saver.save(pred_entries, dryrun=True)

        return pred_entries
