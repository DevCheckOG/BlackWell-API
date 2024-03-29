"""The messages system of BlackWell."""

# Third party modules.

import fastapi

# Standard modules.

import asyncio
import concurrent.futures

from typing import Any, Dict, List, Literal

# Own modules.

from .db.primary import (
    USERS,
    contact_add_or_remove,
    add_action_message,
    get_action_messages,
    delete_action_messages,
)
from .db.secundary import (
    get_queue_history,
    add_message_queue_history,
    delete_queue_history,
)

GATEWAY_THREAD_POOL: concurrent.futures.ThreadPoolExecutor = (
    concurrent.futures.ThreadPoolExecutor(
        max_workers=5000, thread_name_prefix="Gateway"
    )
)

GATEWAY_CONEXIONS: List[Dict[str, Any]] = []


class GatewayTools:

    @staticmethod
    async def connect_websocket(
        connection: Dict[str, Any],
        email: str,
        password: str,
        websocket: fastapi.WebSocket,
    ) -> None:

        if connection["email"] == email and connection["password"] == password:

            await websocket.accept()

            connection["websocket"] = websocket

            queue_history: List[Dict[str, Any]] | bool = await get_queue_history(
                connection["username"]
            )
            actions_messages: List[Dict[str, Any]] | bool = await get_action_messages(
                connection["username"]
            )

            if isinstance(queue_history, list):

                await asyncio.gather(
                    *[
                        GatewayTools.send_temp_message(message, websocket)
                        for message in queue_history
                    ],
                    return_exceptions=True
                )
                await delete_queue_history(connection["username"])

            if isinstance(actions_messages, list):

                await asyncio.gather(
                    *[
                        GatewayTools.send_temp_message(message, websocket)
                        for message in actions_messages
                    ],
                    return_exceptions=True
                )
                await delete_action_messages(connection["username"])

    @staticmethod
    async def connect(email: str, password: str, websocket: fastapi.WebSocket) -> None:

        await asyncio.gather(
            *[
                GatewayTools.connect_websocket(connection, email, password, websocket)
                for connection in GATEWAY_CONEXIONS
            ],
            return_exceptions=True
        )

    @staticmethod
    async def disconnect(websocket: fastapi.WebSocket) -> None:

        await asyncio.gather(
            *[
                GatewayTools.disconnect_websocket(connection, websocket)
                for connection in GATEWAY_CONEXIONS
            ],
            return_exceptions=True
        )

    @staticmethod
    async def disconnect_websocket(
        connection: Dict[str, Any], websocket: fastapi.WebSocket
    ) -> None:

        if connection["websocket"] is websocket:
            connection["websocket"] = None

    @staticmethod
    async def remove_connection(
        connection: Dict[str, Any], email: str, password: str
    ) -> None:

        if connection["email"] == email and connection["password"] == password:
            GATEWAY_CONEXIONS.remove(connection)

    @staticmethod
    async def send_if_have_websocket(
        to: str,
        type: Literal["send", "delete"],
        connection: Dict[str, Any],
        message: Dict[str, Any],
    ) -> bool:

        if (
            type == "send"
            and connection["username"] == to
            and connection["websocket"] is not None
        ):

            await contact_add_or_remove("add", message["from"], to)
            await connection["websocket"].send_json(message)
            return True

        elif (
            type == "delete"
            and connection["username"] == to
            and connection["websocket"] is not None
        ):

            await connection["websocket"].send_json(message)
            return True

        return False

    @staticmethod
    async def send_temp_message(
        message: Dict[str, Any], websocket: fastapi.WebSocket
    ) -> None:

        await websocket.send_json(message)


class GatewayManager:

    @staticmethod
    def _connect(email: str, password: str, websocket: fastapi.WebSocket) -> None:

        asyncio.run(GatewayTools.connect(email, password, websocket))

    @staticmethod
    def _disconnect(websocket: fastapi.WebSocket) -> None:

        asyncio.run(GatewayTools.disconnect(websocket))

    @staticmethod
    async def add(username: str, email: str, password: str) -> None:

        GATEWAY_CONEXIONS.append(
            {
                "username": username,
                "email": email,
                "password": password,
                "websocket": None,
            }
        )

    @staticmethod
    async def remove(email: str, password: str) -> None:

        await asyncio.gather(
            *[
                GatewayTools.remove_connection(connection, email, password)
                for connection in GATEWAY_CONEXIONS
            ],
            return_exceptions=True
        )


class Gateway:

    @staticmethod
    def connect(email: str, password: str, websocket: fastapi.WebSocket) -> None:

        GATEWAY_THREAD_POOL.submit(GatewayManager._connect, email, password, websocket)

    @staticmethod
    def disconnect(websocket: fastapi.WebSocket) -> None:

        GATEWAY_THREAD_POOL.submit(GatewayManager._disconnect, websocket)

    @staticmethod
    async def send_message(to: str, message: Dict[str, Any]) -> bool | str:

        results: List[bool | Any] = await asyncio.gather(
            *[
                GatewayTools.send_if_have_websocket(to, "send", connection, message)
                for connection in GATEWAY_CONEXIONS
            ],
            return_exceptions=True
        )

        for result in results:

            if isinstance(result, bool):
                return True

        await contact_add_or_remove("add", message["from"], to)
        return (
            await add_message_queue_history(to, message)
            if not any(to == connection["username"] for connection in GATEWAY_CONEXIONS)
            else "The user you are trying to send a message to does not exist."
        )

    @staticmethod
    async def delete_message(to: str, action: Dict[str, Any]) -> bool | str:

        results: List[bool | Any] = await asyncio.gather(
            *[
                GatewayTools.send_if_have_websocket(to, "delete", connection, action)
                for connection in GATEWAY_CONEXIONS
            ],
            return_exceptions=True
        )

        for result in results:

            if isinstance(result, bool):
                return True

        return (
            await add_action_message(to, action)
            if not any(to == connection["username"] for connection in GATEWAY_CONEXIONS)
            else "The user you are trying to send a message to does not exist."
        )

    @staticmethod
    async def load() -> None:

        conexions_to_add: List[Dict[str, Any]] = []

        async for user in USERS.find({}):

            conexions_to_add.append(
                {
                    "username": user["username"],
                    "email": user["email"],
                    "password": user["password"],
                    "websocket": None,
                }
            )

        GATEWAY_CONEXIONS.extend(conexions_to_add)
