import os


def load_env_file(path: str = ".env") -> bool:
    """Load simple KEY=VALUE pairs from a .env file into os.environ if not already set.

    - Ignores blank lines and lines starting with '#'
    - Uses the first '=' as the separator
    - Does not overwrite existing environment variables
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if key and key not in os.environ:
                    os.environ[key] = value
        return True
    except FileNotFoundError:
        return False


