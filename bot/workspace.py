from __future__ import annotations

from dataclasses import dataclass

from .storage import WorkspaceStorage
from .trello_client import TrelloClient


@dataclass(slots=True)
class Workspace:
    board_id: str
    board_name: str
    inbox_list_id: str


class WorkspaceManager:
    def __init__(self, storage: WorkspaceStorage, trello: TrelloClient, *, default_list_name: str) -> None:
        self._storage = storage
        self._trello = trello
        self._default_list_name = default_list_name

    def ensure_workspace(self, user_id: int) -> Workspace:
        data = self._storage.load()
        key = str(user_id)
        if key in data:
            user_data = data[key]
            return Workspace(
                board_id=user_data["board_id"],
                board_name=user_data.get("board_name", "TaskMate Workspace"),
                inbox_list_id=user_data["inbox_list_id"],
            )

        board_name = f"TaskMate Telegram Workspace #{user_id}"
        board = self._trello.create_board(board_name)
        inbox_list = self._trello.create_list(board["id"], self._default_list_name)
        data[key] = {
            "board_id": board["id"],
            "board_name": board.get("name", board_name),
            "inbox_list_id": inbox_list["id"],
        }
        self._storage.save(data)

        return Workspace(
            board_id=board["id"],
            board_name=board.get("name", board_name),
            inbox_list_id=inbox_list["id"],
        )
