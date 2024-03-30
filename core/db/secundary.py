# Standard modules.

import datetime
import time
import os

from typing import Any, Dict, List

# Third party modules.

import pymongo

from motor.motor_asyncio import AsyncIOMotorClient
from motor.core import AgnosticClient, AgnosticCollection
from pymongo.results import DeleteResult, InsertOneResult
from pymongo import MongoClient
from pymongo.collection import Collection

# Own modules.

from .primary import USERS, get_token_with_username

"""Secundary Client Database."""

SECUNDARY_CLIENT: AgnosticClient = AsyncIOMotorClient(
    os.environ["MongoDB"], maxPoolSize=None
)
QUEUE_HISTORY: AgnosticCollection = SECUNDARY_CLIENT.get_database(
    "messages"
).get_collection("queue history")
TEMP_USERS: AgnosticCollection = SECUNDARY_CLIENT.get_database("users").get_collection(
    "users temporal"
)

# Temporary Users Section - Secondary DB


async def find_possible_user(username: str = "", email: str = "") -> bool:

    user: Dict[str, Any] | None = await USERS.find_one(
        {
            "username": {"$regex": username, "$options": "i"},
            "email": {"$regex": email, "$options": "i"},
        }
    )
    temp_user: Dict[str, Any] | None = await TEMP_USERS.find_one(
        {
            "username": {"$regex": username, "$options": "i"},
            "email": {"$regex": email, "$options": "i"},
        }
    )

    return True if user is None and temp_user is None else False


async def post_temp_user(user: Dict[str, Any]) -> bool:

    result: InsertOneResult = await TEMP_USERS.insert_one(user)

    return True if result.inserted_id == user["_id"] else False


async def terminate_temp_user(id: str = "") -> bool:

    result: DeleteResult = await TEMP_USERS.delete_one({"_id": id})

    return True if result.deleted_count == 1 else False


async def is_valid_verification_code(code: str = "") -> bool:

    result: Dict[str, Any] | None = await TEMP_USERS.find_one(
        {"verification.code": code}
    )

    return (
        True
        if isinstance(result, dict) and result["verification"]["code"] == code
        else False
    )


async def get_temp_user(code: str = "") -> Dict[str, Any] | bool:

    result: Dict[str, Any] | None = await TEMP_USERS.find_one(
        {"verification.code": code}
    )

    return (
        result
        if isinstance(result, dict) and result["verification"]["code"] == code
        else False
    )


# Queue History Section - Secondary DB


async def get_queue_history(username: str = "") -> List[Dict[str, Any]] | bool:

    token: List[str] | bool = await get_token_with_username(username)

    if not isinstance(token, list):
        return False

    result: Dict[str, Any] | None = await QUEUE_HISTORY.find_one({"_id": token[0]})

    return result["messages"] if isinstance(result, dict) else False


async def delete_queue_history(username: str = "") -> bool:

    token: List[str] | bool = await get_token_with_username(username)

    if not isinstance(token, list):
        return False

    result: DeleteResult = await QUEUE_HISTORY.delete_one({"_id": token[0]})

    return True if result.deleted_count == 1 else False


async def add_message_queue_history(to: str, message: Dict[str, Any]) -> bool:

    token: List[str] | bool = await get_token_with_username(to)

    if not isinstance(token, list):
        return False

    fetch_possible_history: List[Dict[str, Any]] | bool = await get_queue_history(
        token[0]
    )

    if isinstance(fetch_possible_history, list):

        await QUEUE_HISTORY.update_one({"_id": token}, {"$push": {"messages": message}})

        return True

    await QUEUE_HISTORY.insert_one(
        {
            "_id": token,
            "username": to,
            "created-at": datetime.datetime.strftime(
                datetime.datetime.now(), "%Y-%m-%d %H:%M"
            ),
            "messages": [message],
        }
    )

    return True


def cleaner_temporal_accounts() -> None:
    """Cleaner of temporal accounts."""

    CLIENT: MongoClient = pymongo.MongoClient(os.environ["MongoDB"], maxPoolSize=None)
    TEMP_USERS: Collection = CLIENT.get_database("users").get_collection(
        "users temporal"
    )

    while True:

        if TEMP_USERS.count_documents({}) == 0:
            continue

        temp_users: List[Dict[str, Any]] = list(TEMP_USERS.find())

        for user in temp_users:

            if (
                datetime.datetime.strptime(
                    user["verification"]["remaining"], "%Y-%m-%d %H:%M:%S.%f"
                )
                <= datetime.datetime.now()
            ):

                TEMP_USERS.delete_one({"_id": user["_id"]})
                continue

        time.sleep(60)


def cleaner_queue_history() -> None:
    """Cleaner of the Queue History."""

    CLIENT: MongoClient = pymongo.MongoClient(os.environ["MongoDB"], maxPoolSize=None)
    QUEUE_HISTORY: Collection = CLIENT.get_database("messages").get_collection(
        "queue history"
    )

    while True:

        time.sleep(60 * 60 * 25)

        if QUEUE_HISTORY.count_documents({}) == 0:
            continue

        elif (
            datetime.datetime.now().day == 1 and datetime.datetime.now().month % 2 == 0
        ):

            QUEUE_HISTORY.delete_many({})
            continue
