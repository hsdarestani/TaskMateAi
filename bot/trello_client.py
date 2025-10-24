from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

import requests


LOGGER = logging.getLogger(__name__)


class TrelloError(RuntimeError):
    """Raised when Trello's API responds with an error."""


class TrelloClient:
    base_url = "https://api.trello.com/1"

    def __init__(self, api_key: str, api_token: str) -> None:
        self.auth = {"key": api_key, "token": api_token}

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.base_url}{path}"
        params = kwargs.pop("params", {})
        if "auth" in kwargs:
            raise ValueError("auth parameter is reserved")
        params.update(self.auth)
        response = requests.request(method, url, params=params, **kwargs)
        if response.ok:
            if response.content:
                return response.json()
            return None
        LOGGER.error(
            "Trello API error %s on %s: %s", response.status_code, url, response.text
        )
        raise TrelloError(response.text)

    def create_board(self, name: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/boards/",
            params={
                "name": name,
                "defaultLabels": "true",
                "defaultLists": "false",
                "prefs_permissionLevel": "private",
            },
        )

    def create_list(self, board_id: str, name: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/lists",
            params={"idBoard": board_id, "name": name},
        )

    def create_card(
        self, list_id: str, *, name: str, desc: str | None = None
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"idList": list_id, "name": name}
        if desc:
            params["desc"] = desc
        return self._request("POST", "/cards", params=params)

    def add_comment(self, card_id: str, text: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/cards/{card_id}/actions/comments",
            params={"text": text},
        )

    def attach_file(self, card_id: str, file_path: Path, file_name: str) -> Dict[str, Any]:
        with file_path.open("rb") as fh:
            return self._request(
                "POST",
                f"/cards/{card_id}/attachments",
                files={"file": (file_name, fh)},
            )
