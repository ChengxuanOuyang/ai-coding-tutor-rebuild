import json
import subprocess
import sys


def test_cli_returns_tutoring_payload() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.app.cli",
            "--message",
            "Why does my loop not stop?",
            "--programming-level",
            "2",
            "--maths-level",
            "3",
            "--programming-difficulty",
            "4",
            "--maths-difficulty",
            "2",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["programming_hint_level"] == 3
    assert payload["maths_hint_level"] == 1
    assert payload["provider"] == "mock"
    assert payload["model"] == "deterministic-tutor-v1"
    assert payload["content"]
    assert payload["input_tokens"] > 0
    assert payload["output_tokens"] > 0


def test_cli_rejects_difficulty_outside_supported_range() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.app.cli",
            "--message",
            "Help",
            "--programming-level",
            "2",
            "--maths-level",
            "3",
            "--programming-difficulty",
            "9",
            "--maths-difficulty",
            "2",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert "difficulty must be between 1 and 5" in completed.stderr
    assert completed.stdout == ""
