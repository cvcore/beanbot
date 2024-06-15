from pathlib import Path
import subprocess


def run_cli_command():
    command = [
        "bean-extract",
        "tests/data/import.config",
        "tests/data/raw/alipay/transactions/foo@bar.com/alipay_record_20240101_0000_1.csv",
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    return result.stdout


def read_file_content(filepath):
    assert Path(filepath).exists(), f"File {filepath} does not exist."
    with open(filepath, "r") as file:
        content = file.readlines()
    return content


def compare_output(expected_file, actual_output):
    expected_content = read_file_content(expected_file)
    actual_content = actual_output.splitlines()

    # Ignore the first 4 rows
    actual_content = actual_content[4:]

    expected_content = [line.strip() for line in expected_content if line.strip()]
    actual_content = [line.strip() for line in actual_content if line.strip()]
    assert (
        expected_content == actual_content
    ), "Output does not match the expected content."


def test_cli_command_output():
    actual_output = run_cli_command()
    compare_output("tests/data/expected/importer/alipay.bean", actual_output)
