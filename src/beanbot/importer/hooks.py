import logging
from functools import wraps
from typing import List

from beancount.loader import load_file
from beancount.core.data import Entries
from beancount.ingest.importer import ImporterProtocol
from beanbot.classifier.meta_transaction_classifier import MetaTransactionClassifier
from beancount.core import data
from beanbot.ops.filter import NotTransactionFilter, TransactionFilter
from beanbot.ops.file_saver import EntryFileSaver
from beanbot.ops.dedup import Deduplicator
from beanbot.common.configs import BeanbotConfig
from beancount.parser import printer

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


def _test_in_0(entries_0, entries_1):
    print(f"[Debug] {len([e for e in entries_1 if e in entries_0])}")

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

        deduplicator = Deduplicator(
            window_days_head=global_config['dedup-window-days'],
            window_days_tail=global_config['dedup-window-days'],
            max_date_difference=global_config['dedup-window-days']
        )

        duplicated_entries, imported_entries = deduplicator.deduplicate(existing_entries, imported_entries)

        transactions_existing = TransactionFilter().filter(existing_entries)
        transactions_imported = TransactionFilter().filter(imported_entries)
        other_entries_imported = NotTransactionFilter().filter(imported_entries)

        # Debug
        print('------------------------')
        print("Duplicated transactions:")
        printer.print_entries(duplicated_entries)
        print('------------------------')
        print("Non-duplicated entries:")
        printer.print_entries(imported_entries)
        print('------------------------')

        print('[DEBUG] Learning filename for existing entries...')
        saver = EntryFileSaver(global_config['fallback-transaction-file'])
        saver.learn_filename(existing_entries)


        print('[DEBUG] Predicing transactions for imported entries...')
        classifier = MetaTransactionClassifier(options_map)
        classifier.train(transactions_existing)
        pred_txns = []
        if len(transactions_imported) > 0:
            pred_txns = classifier.predict(transactions_imported)
        pred_txns.extend(other_entries_imported)

        new_entries = data.sorted(pred_txns)

        saver.save(new_entries, dryrun=False)

        return new_entries
