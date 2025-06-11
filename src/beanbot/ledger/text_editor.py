"""Provides a text editor for modifying the beancount ledger files."""

import enum
import sys
from dataclasses import dataclass
from pathlib import Path

from beanbot.utils import logger


class ChangeType(enum.Enum):
    INSERT = 1
    DELETE = 2
    REPLACE = 3
    APPEND = 4


INF = sys.maxsize  # Use sys.maxsize as a substitute for infinity for positions


@dataclass
class ChangeSet:
    """Represents a change set that describes a modification to a text file.

    Attributes:
        type: The type of change.
        position: The position of the change.
            For INSERT type, it should be an integer representing the position to insert the content.
            For DELETE and REPLACE types, it should be a tuple of two integers representing the range to delete or replace.
            For APPEND type, it should be None, as appending is only supported at the end of the file.

            The line numbers are 0-indexed. When the specified position is negative,
            it is interpreted as a relative position from the end of the file:
            e.g. (pos, -1) means every line from pos to the end of the file, inclusive;
            (pos, -2) means every line from pos to the second last line, etc.
        content: The content to be inserted, replaced, or appended.
            This attribute is required for INSERT, REPLACE, and APPEND types.
    """

    type: ChangeType
    position: int | tuple[int, int] | None = None
    content: list[str] | None = None

    def __post_init__(self):
        # Verify content
        if (
            self.type in {ChangeType.INSERT, ChangeType.REPLACE, ChangeType.APPEND}
            and self.content is None
        ):
            raise ValueError(f"content is required for {self.type}")

        # Verify position
        if self.type in {ChangeType.INSERT}:
            assert self.position is not None and isinstance(self.position, int), (
                f"position must be an integer for {self.type}"
            )
        elif self.type in {ChangeType.DELETE, ChangeType.REPLACE}:
            assert (
                self.position is not None
                and isinstance(self.position, tuple)
                and len(self.position) == 2
            ), (
                f"position must be a tuple of two integers for {self.type} with (begin, end)"
            )

        if self.type in {ChangeType.APPEND}:
            assert self.position is None, (
                f"position must be None for {self.type}, as we only support appending to the end of the file."
            )

        assert isinstance(self.content, list | None), (
            f"content must be a list of strings for {self.type}"
        )

    def __repr__(self) -> str:
        return f"ChangeSet(\ntype={self.type},\nposition={self.position},\ncontent={self.content})"


class TextEditor:
    def __init__(self, file_path: str, encoding: str = "utf-8") -> None:
        """Create a TextEditor for modifying `file_path`.

        Args:
            file_path: The path to the file.
            encoding: The encoding of the file. Defaults to "utf-8".

        Raises:
            AssertionError: If the file does not exist.
        """
        self._file_path = Path(file_path)
        self._encoding = encoding
        self._lines = self._read_file(file_path)
        self._file_n_lines = len(self._lines)
        self._changes = []

    def _read_file(self, file_path: str) -> list[str]:
        if not self._file_path.exists():
            logger.info("File %s does not exist, will create it.", file_path)
            with open(file_path, "w", encoding=self._encoding) as file:
                file.write("")
        with open(file_path, "r", encoding=self._encoding) as file:
            lines = file.readlines()
        # note: we add this empty line to be able to address the position after the last line with -1
        lines.append("")
        return lines

    def edit(self, changes: list[ChangeSet] | ChangeSet) -> None:
        """Applies the given changes to the text editor.

        Args:
            changes: The changes to be applied. It can be a single ChangeSet or a list of ChangeSet objects.

        Returns:
            None
        """
        if isinstance(changes, ChangeSet):
            changes = [changes]
        self._changes.extend(changes)

    def _get_position_tuple(self, change: ChangeSet) -> tuple[int, int]:
        # convert relative positions to their absolute values
        if change.type == ChangeType.INSERT:
            assert isinstance(change.position, int)
            pos_tuple = (change.position, change.position)
        elif change.type == ChangeType.DELETE or change.type == ChangeType.REPLACE:
            assert isinstance(change.position, tuple) and len(change.position) == 2, (
                f"position must be a tuple for {change.type} with (begin, end)"
            )
            pos_tuple = change.position
        else:
            pos_tuple = (INF, INF)

        begin, end = pos_tuple
        if begin < 0:
            begin += self._file_n_lines
        if end < 0:
            end += self._file_n_lines
        pos_tuple = (begin, end)

        return pos_tuple

    def _sort_changes_by_position(self):
        self._changes.sort(key=self._get_position_tuple)

    def _check_changes_non_overlapping(self):
        for idx in range(len(self._changes) - 1):
            edit_begin, edit_end = self._get_position_tuple(self._changes[idx])
            next_begin, next_end = self._get_position_tuple(self._changes[idx + 1])
            assert not edit_begin <= next_begin < edit_end, (
                f"Changes {self._changes[idx]} and {self._changes[idx + 1]} are overlapping."
            )

            if edit_begin == edit_end:
                assert not next_begin == next_end == edit_begin, (
                    f"Double insertion at position {edit_begin} detected."
                )

    def _check_range_validity(self, line_count: int):
        for change in self._changes:
            position = self._get_position_tuple(change)
            assert position == (INF, INF) or (
                0 <= position[0] <= position[1] < line_count
            ), f"Change {change} is invalid."

    def save_changes(self, to_path: str | None = None):
        """
        Saves the changes made to the file.

        Args:
            to_path (Optional[str]): The path to save the file. If not provided, the changes will be saved to the original file path.

        Returns:
            None
        """

        lines = self._lines

        self._sort_changes_by_position()
        self._check_changes_non_overlapping()
        self._check_range_validity(len(lines))

        edited_lines = []

        change_idx = 0
        line_idx = 0
        while (
            line_idx < len(lines) - 1
        ):  # ignore the last empty line added when reading
            # No more changes to apply
            if change_idx >= len(self._changes):
                edited_lines.extend(lines[line_idx:])
                break

            change_begin, change_end = self._get_position_tuple(
                self._changes[change_idx]
            )

            # Next change is append
            if change_begin == INF:
                edited_lines.extend(lines[line_idx:])
                edited_lines.extend(self._changes[change_idx].content)
                break

            # Next change is after this line
            if line_idx < change_begin:
                edited_lines.extend(lines[line_idx:change_begin])
                line_idx = change_begin
                continue

            # Next change is on this line
            if self._changes[change_idx].type == ChangeType.INSERT:
                edited_lines.extend(self._changes[change_idx].content)
                change_idx += 1
                continue
            elif self._changes[change_idx].type == ChangeType.DELETE:
                line_idx = change_end
                change_idx += 1
                continue
            elif self._changes[change_idx].type == ChangeType.REPLACE:
                edited_lines.extend(self._changes[change_idx].content)
                line_idx = change_end
                change_idx += 1
                continue
            elif self._changes[change_idx].type == ChangeType.APPEND:
                edited_lines.append(self._changes[change_idx].content)
                change_idx += 1
                continue
            else:
                assert False, f"Unexpected change type {self._changes[change_idx].type}"

        save_path = to_path if to_path is not None else self._file_path
        with open(save_path, "w", encoding=self._encoding) as file:
            file.writelines(edited_lines)
