import json
import time
from pathlib import Path
from typing import Any

import httpx


class InfoclimatClient:
    """Client HTTP pour l'API climato Infoclimat.

    Gère deux spécificités documentées de l'API :
    - warmup : premier appel après inactivité renvoie 503 + Retry-After
    - pagination : les familles de séries plafonnent à 20 000 lignes et
      exposent `tronque: true` + `suite.from` pour la page suivante
    """

    WARMUP_STATUS = 503
    MAX_WARMUP_RETRIES = 4

    def __init__(self, base_url: str, timeout_seconds: int = 30) -> None:
        self._client = httpx.Client(base_url=base_url, timeout=timeout_seconds)

    def _get(self, endpoint: str, params: dict[str, Any]) -> httpx.Response:
        for _ in range(self.MAX_WARMUP_RETRIES + 1):
            r = self._client.get(endpoint, params=params)
            if r.status_code != self.WARMUP_STATUS:
                r.raise_for_status()
                return r
            wait = float(r.headers.get("retry-after", "2"))
            time.sleep(wait)
        r.raise_for_status()
        return r  # unreachable

    def fetch(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        return self._get(endpoint, params or {}).json()

    def fetch_paginated_to_dir(
        self,
        endpoint: str,
        destination_dir: Path,
        params: dict[str, Any] | None = None,
    ) -> list[Path]:
        """Suit `suite.from` jusqu'à épuisement, un fichier JSON par page.

        Convient aux endpoints de séries (/dataclimat, /v2, /legacy, /ic,
        /statIC). Pour les référentiels, utiliser fetch_to_file.
        """
        destination_dir.mkdir(parents=True, exist_ok=True)
        current_params = dict(params or {})
        written: list[Path] = []
        page = 1
        while True:
            payload = self.fetch(endpoint, current_params)
            path = destination_dir / f"page-{page:05d}.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
            written.append(path)

            if not (isinstance(payload, dict) and payload.get("tronque")):
                break
            suite = payload.get("suite") or {}
            next_from = suite.get("from")
            if not next_from:
                break
            current_params["from"] = next_from
            page += 1
        return written

    def fetch_to_file(
        self,
        endpoint: str,
        destination: Path,
        params: dict[str, Any] | None = None,
    ) -> Path:
        payload = self.fetch(endpoint, params)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with open(destination, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        return destination

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "InfoclimatClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
