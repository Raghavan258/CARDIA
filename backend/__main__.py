"""Run: python -m backend"""

from __future__ import annotations

import uvicorn

from backend.settings import SETTINGS


def main() -> None:
    uvicorn.run(
        "backend.app:app",
        host=SETTINGS.host,
        port=SETTINGS.port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
