import csv
from re import Match
from typing import List, Optional

from beancount.ingest import importer
from beancount.core.data import Directive
from beancount.ingest.cache import _FileMemo

from beanbot.helper import logger

class CSVImporter(importer.ImporterProtocol):

    def __init__(
        self,
        account: str,
        lastfour: str | List[str] | None = None,
        encoding: str = "UTF-8",
        n_header_lines: int = 0,
        n_footer_lines: int = 0,
        delimiter: str = ",",
        quotechar: str = "\"",
        skiptrailingspace: bool = False,
        skipinitialspace: bool = False,
    ):
        """
        Initialize a CSVImporter object.

        Args:
            account (str): The account associated with the CSV file.
            lastfour (str | List[str]): The last four digits of the account number or a list of last four digits.
                When given a list, the importer will match any of the last four digits for the `account` specified.
            encoding (str, optional): The encoding of the CSV file. Will be used to open the file. Defaults to "UTF-8".
            n_header_lines (int, optional): The number of header lines in the CSV file. Defaults to 0.
            n_footer_lines (int, optional): The number of footer lines in the CSV file. Defaults to 0.
            delimiter (str, optional): The delimiter used in the CSV file. Defaults to None.
            quotechar (str, optional): The quote character used in the CSV file. Defaults to None.
            skiptrailingspace (bool, optional): When enabled, tailing spaces in each field will be stripped. Defaults to False.
        """
        self._account = account
        self._lastfour = lastfour if isinstance(lastfour, list) else [lastfour] if lastfour else None
        self._encoding = encoding
        self._header_lines = n_header_lines
        self._footer_lines = n_footer_lines

        self._csv_reader_kwargs = {}
        self._delimiter = delimiter
        self._csv_reader_kwargs["delimiter"] = delimiter
        self._quotechar = quotechar
        self._csv_reader_kwargs["quotechar"] = quotechar
        self._skiptrailingspace = skiptrailingspace
        self._skipinitialspace = skipinitialspace

        self._file_meta = {}

    def identify(self, file) -> Match[str] | None:
        raise NotImplementedError("This method should be implemented by the subclass")

    def _parse_header(self, header_lines: List) -> List[Directive]:
        raise NotImplementedError("This method should be implemented by the subclass")

    def _parse_footer(self, footer_lines: List) -> List[Directive]:
        raise NotImplementedError("This method should be implemented by the subclass")

    def _parse_row_impl(self, row: dict, filename: str, lineno: int) -> List[Directive]:
        raise NotImplementedError("This method should be implemented by the subclass")

    def _remove_whitespaces(self, lines: List[str], remove_leading: bool = False, remove_trailing: bool = False) -> List[str]:
        if not remove_leading and not remove_trailing:
            return lines
        fn_strip = str.strip if remove_trailing and remove_leading \
            else str.lstrip if remove_leading \
            else str.rstrip
        for i, line in enumerate(lines):
            lines[i] = self._delimiter.join([fn_strip(field) for field in line.split(self._delimiter)])
        return lines


    def extract(self, file: _FileMemo, existing_entries: Optional[List[Directive]] = None) -> List[Directive]:

        entries = []

        header_lines = []
        body_lines = []
        footer_lines = []

        self._file_meta = {}

        with open(file.name, encoding=self._encoding) as csvfile:
            if self._header_lines:
                header_lines = [next(csvfile) for _ in range(self._header_lines)]
            assert len(header_lines) == self._header_lines, f"Expected {self._header_lines} header lines, got {len(header_lines)}"

            body_lines = [line for line in csvfile]

        if self._footer_lines:
            footer_lines = body_lines[-self._footer_lines:]
            body_lines = body_lines[:-self._footer_lines]
            assert len(footer_lines) == self._footer_lines, f"Expected {self._footer_lines} footer lines, got {len(footer_lines)}"

        if self._skiptrailingspace:
            body_lines = self._remove_whitespaces(body_lines, remove_trailing=self._skiptrailingspace, remove_leading=self._skipinitialspace)

        header_entries = self._parse_header(header_lines)
        footer_entries = self._parse_footer(footer_lines)
        body_entries = []
        for index, row in enumerate(csv.DictReader(body_lines, **self._csv_reader_kwargs)):
            body_entries.extend(self._parse_row_impl(row, file.name, index + self._header_lines + 1))

        entries = sorted(
            [
                *header_entries,
                *body_entries,
                *footer_entries,
            ],
            key=lambda x: getattr(x, "date"),
        )

        return entries
