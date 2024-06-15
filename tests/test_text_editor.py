import tempfile
from typing import List
from pathlib import Path
from beanbot.file.text_editor import TextEditor, ChangeSet, ChangeType
import tempfile

class TestTextEditor:

    def run_test_case(self, input_file: str, expect_file: str, changes: List[ChangeSet]):
        text_editor = TextEditor(input_file)
        text_editor.edit(changes)

        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = str(Path(temp_dir) / "output.txt")
            text_editor.save_changes(to_path=save_path)

            with open(save_path, 'r', encoding='utf-8') as file:
                modified_content = file.readlines()

            # Read the expected output file
            with open(expect_file, 'r', encoding='utf-8') as file:
                expected_content = file.readlines()

            # Assert that the modified content matches the expected content
            assert modified_content == expected_content

    def test_insertion(self):
        # Define the changes to be made

        input_file = "tests/data/file_editor/test_file.txt"
        expect_file = "tests/data/file_editor/test_insert_expect.txt"

        changes = [
            ChangeSet(ChangeType.INSERT, position=0, content=["a0\n", "a1\n", "a2\n"]),
            ChangeSet(ChangeType.INSERT, position=6, content=["a3\n", "a4\n", "a5\n", "\n"]),
        ]

        self.run_test_case(input_file, expect_file, changes)

    def test_deletion(self):
        # Define the changes to be made

        input_file = "tests/data/file_editor/test_file.txt"
        expect_file = "tests/data/file_editor/test_delete_expect.txt"

        changes = [
            ChangeSet(ChangeType.DELETE, position=(0, 2)),
            ChangeSet(ChangeType.DELETE, position=(3, 5)),
        ]

        self.run_test_case(input_file, expect_file, changes)

    def test_rel_deletion(self):
        # Define the changes to be made

        input_file = "tests/data/file_editor/test_file.txt"
        expect_file = "tests/data/file_editor/test_rel_delete_expect.txt"

        changes = [
            ChangeSet(ChangeType.DELETE, position=(-2, -1)),
        ]

        self.run_test_case(input_file, expect_file, changes)

    def test_replace(self):
        # Define the changes to be made

        input_file = "tests/data/file_editor/test_file.txt"
        expect_file = "tests/data/file_editor/test_replace_expect.txt"

        changes = [
            ChangeSet(ChangeType.REPLACE, position=(0, 2), content=["a0\n", "a1\n", "a2\n"]),
            ChangeSet(ChangeType.REPLACE, position=(3, 5), content=["a3\n", "a4\n", "a5\n", "\n"]),
        ]

        self.run_test_case(input_file, expect_file, changes)

    def test_append(self):
        # Define the changes to be made

        input_file = "tests/data/file_editor/test_file.txt"
        expect_file = "tests/data/file_editor/test_append_expect.txt"

        changes = [
            ChangeSet(ChangeType.APPEND, content=["a0\n", "a1\n", "a2\n"]),
        ]

        self.run_test_case(input_file, expect_file, changes)
