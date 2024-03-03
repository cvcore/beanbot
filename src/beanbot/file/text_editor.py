# Text file editor


from dataclasses import dataclass
import enum
from math import inf
from pathlib import Path
from types import NoneType
from typing import List, Optional, Tuple


class ChangeType(enum.Enum):
    INSERT = 1
    DELETE = 2
    REPLACE = 3
    APPEND = 4


@dataclass
class ChangeSet:
    """
    Represents a change set that describes a modification to a text file.

    Attributes:
        type (ChangeType): The type of change.
        position (int | Tuple[int, int] | NoneType): The position of the change.
            For INSERT type, it should be an integer representing the position to insert the content.
            For DELETE and REPLACE types, it should be a tuple of two integers representing the range to delete or replace.
            For APPEND type, it should be None, as appending is only supported at the end of the file.
        content (Optional[List[str]]): The content to be inserted, replaced, or appended.
            This attribute is required for INSERT, REPLACE, and APPEND types.
    """

    type: ChangeType
    position: int | Tuple[int, int] | NoneType = None
    content: Optional[List[str]] = None

    def __post_init__(self):
        # Verify content
        if self.type in {ChangeType.INSERT, ChangeType.REPLACE, ChangeType.APPEND} and self.content is None:
            raise ValueError(f"content is required for {self.type}")

        # Verify position
        if self.type in {ChangeType.INSERT}:
            assert self.position is not None and isinstance(self.position, int), f"position must be an integer for {self.type}"
        elif self.type in {ChangeType.DELETE, ChangeType.REPLACE}:
            assert self.position is not None and isinstance(self.position, tuple) and len(self.position) == 2, f"position must be a tuple of two integers for {self.type} with (begin, end)"

        if self.type in {ChangeType.APPEND}:
            assert self.position is None, f"position must be None for {self.type}, as we only support appending to the end of the file."

    def __repr__(self) -> str:
        return f"ChangeSet(type={self.type}, position={self.position}, content={self.content})"


class TextEditor:

    def __init__(self, file_path: str) -> None:
        self._file_path = Path(file_path)
        assert self._file_path.exists(), f"File {file_path} does not exist."
        self._changes = []

    def edit(self, changes: List[ChangeSet] | ChangeSet) -> None:
        if isinstance(changes, ChangeSet):
            changes = [changes]
        self._changes.extend(changes)

    def _get_position_tuple(self, change: ChangeSet) -> Tuple[int, int]:
        if change.type == ChangeType.INSERT:
            return (change.position, change.position)
        elif change.type == ChangeType.DELETE or change.type == ChangeType.REPLACE:
            return change.position
        else:
            return (inf, inf)

    def _sort_changes(self):
        self._changes.sort(key=self._get_position_tuple)

    def _check_changes_non_overlapping(self):
        for idx in range(len(self._changes) - 1):
            edit_begin, edit_end = self._get_position_tuple(self._changes[idx])
            next_begin, next_end = self._get_position_tuple(self._changes[idx + 1])
            assert not edit_begin <= next_begin < edit_end, f"Changes {self._changes[idx]} and {self._changes[idx + 1]} are overlapping."

            if edit_begin == edit_end:
                assert not next_begin == next_end == edit_begin, f"Double insertion at position {edit_begin} detected."


    def _check_changes_validity(self, line_count: int):
        for change in self._changes:
            position = self._get_position_tuple(change)
            assert position == (inf, inf) or \
                (0 <= position[0] <= position[1] < line_count), f"Change {change} is invalid."

    def save_changes(self, to_path: Optional[str] = None):
        with open(self._file_path, 'r') as file:
            lines = file.readlines()

        self._sort_changes()
        self._check_changes_non_overlapping()
        self._check_changes_validity(len(lines))

        edited_lines = []

        change_idx = 0
        line_idx = 0
        while line_idx < len(lines):

            # No more changes to apply
            if change_idx >= len(self._changes):
                edited_lines.extend(lines[line_idx:])
                break

            change_begin, change_end = self._get_position_tuple(self._changes[change_idx])

            # Next change is append
            if change_begin == inf:
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
        with open(save_path, 'w') as file:
            file.writelines(edited_lines)
