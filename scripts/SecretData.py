from pathlib import Path
import os


def get_variables(secret_dir="/mnt/secrets/env"):
    variables = dict(os.environ)

    secret_path = Path(secret_dir)

    if not secret_path.exists():
        return variables

    for file_path in secret_path.iterdir():
        if not file_path.is_file():
            continue

        variables[file_path.name] = file_path.read_text(encoding="utf-8").rstrip("\r\n")

    return variables