import tempfile
from typing import List
import unittest
from pathlib import Path
from beanbot.file.text_editor import TextEditor, ChangeSet, ChangeType
import tempfile

class TextEditorTestCase(unittest.TestCase):

    def setUp(self):
        self.test_input_path = "/Users/core/Development/Finance/beanbot/tests/data/file_editor/test_insert.txt"
        self.expected_file_path = "/Users/core/Development/Finance/beanbot/tests/data/file_editor/test_insert_expect.txt"

    def tearDown(self):
        self.text_editor = None

    def run_test_case(self, input_file: str, expect_file: str, changes: List[ChangeSet]):
        self.text_editor = TextEditor(input_file)
        self.text_editor.edit(changes)

        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = str(Path(temp_dir) / "output.txt")
            self.text_editor.save_changes(to_path=save_path)

            with open(save_path, 'r', encoding='utf-8') as file:
                modified_content = file.readlines()

            # Read the expected output file
            with open(expect_file, 'r', encoding='utf-8') as file:
                expected_content = file.readlines()

            # Assert that the modified content matches the expected content
            self.assertEqual(modified_content, expected_content)

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

if __name__ == '__main__':
    unittest.main()
