import os
import subprocess
import sys


if os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL"):
    subprocess.run(
        [sys.executable, "manage.py", "migrate", "--noinput"],
        check=True,
    )
