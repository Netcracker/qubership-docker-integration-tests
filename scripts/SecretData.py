from pathlib import Path
import os

_DEFAULT_SECRETS_DIR = "/mnt/secrets/env"


def get_variables(secret_dir=None):
    """
    Dynamic Robot Framework variable file.

    Secret files under secret_dir override os.environ keys with the same name.
    Directory: INTEGRATION_TESTS_SECRETS_DIR, or the optional Robot Variables
    argument, defaulting to /mnt/secrets/env.
    """
    if secret_dir is None:
        secret_dir = os.getenv("INTEGRATION_TESTS_SECRETS_DIR", _DEFAULT_SECRETS_DIR)

    variables = dict(os.environ)

    secret_path = Path(secret_dir)

    if not secret_path.exists():
        return variables

    for file_path in secret_path.iterdir():
        if not file_path.is_file():
            continue

        variables[file_path.name] = file_path.read_text(encoding="utf-8").rstrip("\r\n")

    return variables