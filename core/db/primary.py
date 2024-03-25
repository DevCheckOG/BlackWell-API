"""The database main of BlackWell."""

# Standard modules.

import dotenv
import datetime
import time
import os

from typing import Any, Dict, List, Literal

# Third party modules.

import pymongo
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.results import UpdateResult, InsertOneResult, DeleteResult

from motor.motor_asyncio import AsyncIOMotorClient
from motor.core import AgnosticClient, AgnosticCollection

"""Primary Client Database."""

dotenv.load_dotenv()

PRIMARY_CLIENT : AgnosticClient = AsyncIOMotorClient(os.environ['MongoDB'], maxPoolSize= None)

SYSTEM : AgnosticCollection = PRIMARY_CLIENT.get_database('systems').get_collection('system')
USERS : AgnosticCollection = PRIMARY_CLIENT.get_database('users').get_collection('users permanent') 
ACTIONS : AgnosticCollection = PRIMARY_CLIENT.get_database('messages').get_collection('actions')   

async def get_secret(id: str = '') -> Dict[str, Any] | bool:

    result : Dict[str, Any] | None = await SYSTEM.find_one({'_id' : id})
    
    return result if isinstance(result, dict) else False

async def post_user(user: Dict[str, Any]) -> bool:

    result : InsertOneResult = await USERS.insert_one(user)

    return True if result.inserted_id == user['_id'] else False   

async def get_user(token: str = '') -> Dict[str, Any] | bool:

    result : Dict[str, Any] | None = await USERS.find_one({'_id' : token})
    
    return result if isinstance(result, dict) else False    

async def fetch_user(email: str = '', password: str = '') -> str | bool:

    result : Dict[str, Any] | None = await USERS.find_one({'email': email, 'password': password})

    return result['username'] if isinstance(result, dict) else False

async def get_user_with_email_and_password(email: str = '', password: str = '') -> Dict[str, Any] | bool:

    result : Dict[str, Any] | None = await USERS.find_one({'email' : email, 'password' : password})

    return result if isinstance(result, dict) else False

async def delete_user(email : str = '', password : str = '') -> bool:

    result : DeleteResult = await USERS.delete_one({'email': email, 'password': password})

    return True if result.deleted_count == 1 else False   

async def get_token_with_email_and_password(email: str = '', password: str = '') -> List[str] | bool:

    result : Dict[str, Any] | None = await USERS.find_one({'email' : email, 'password' : password})
    
    return [result['_id'], result['username']] if isinstance(result, dict) else False

async def get_token_with_username(username : str = '') -> List[str] | bool:

    result : Dict[str, Any] | None = await USERS.find_one({'username' : username})
    
    return [result['_id'], result['username']] if isinstance(result, dict) else False

async def set_user_profile(token: str = '', profile: str = '') -> bool:

    result : UpdateResult = await USERS.update_one(

        {'_id' : token},
        {'$set' : {'profile' : profile}}

    )

    return True if result.modified_count > 0 else False

async def get_user_profile(username: str = '') -> List[str] | bool:

    token : List[str] | bool = await get_token_with_username(username)

    if not isinstance(token, list): return False

    result : Dict[str, Any] | None = await USERS.find_one({'_id' : token})
    
    return [result['profile']] if isinstance(result, dict) else False

async def check_if_user_in_contacts(token: str = '', contact: str = '') -> bool:

    result : Dict[str, Any] | None = await USERS.find_one({'_id' : token})
    
    if not isinstance(result, dict): return False

    for i in result['contacts']:

        if i['username'] == contact: return True

    return False

async def contact_add_or_remove(action: Literal['add', 'remove'], from_: str, to: str) -> bool:

    token : List[str] | bool = await get_token_with_username(to)

    if not isinstance(token, list): return False

    elif not await check_if_user_in_contacts(token[0], from_) and action == 'add':

        add : UpdateResult = await USERS.update_one(

            {'username' : to},
            {'$push' : {'contacts' : {'username' : from_}}}

        )

        return True if add.modified_count > 0 else False
    
    elif await check_if_user_in_contacts(token[0], from_) and action == 'remove':

        remove : UpdateResult = await USERS.update_one(

            {'username' : to},
            {'$pull' : {'contacts' : {'username' : from_}}}

        )

        return True if remove.modified_count > 0 else False
    
    return False

# Action Messages Section - Primary DB

async def delete_action_messages(username: str) -> bool:

    token : List[str] | bool = await get_token_with_username(username)

    if not isinstance(token, list): return False

    result : DeleteResult = await ACTIONS.delete_one({'_id' : token[0]})

    return True if result.deleted_count > 0 else False

async def get_action_messages(username: str = '') -> List[Dict[str, Any]] | bool:

    token : List[str] | bool = await get_token_with_username(username)

    if not isinstance(token, list): return False

    result : Dict[str, Any] | None = await ACTIONS.find_one({'_id' : token[0]})

    return result['actions'] if isinstance(result, dict) else False

async def add_action_message(to: str, action: Dict[str, Any]) -> bool: 

    token : List[str] | bool = await get_token_with_username(to)

    if not isinstance(token, list): return False

    fetch_possible_actions : List[Dict[str, Any]] | bool = await get_action_messages(to)

    if not isinstance(fetch_possible_actions, list):

        await ACTIONS.insert_one({

            '_id' : token[0],
            'actions' : [action]

        })

        return True

    await ACTIONS.update_one(

        {'_id' : token[0]},
        {'$push' : {'actions' : action}}

    )

    return True

def cleaner_history() -> None:
    """Cleaner of the History."""

    CLIENT : MongoClient = pymongo.MongoClient(os.environ['MongoDB'], maxPoolSize= None)
    HISTORY : Collection = CLIENT.get_database('messages').get_collection('history')

    while True:

        time.sleep(60 * 60 * 25)

        if HISTORY.count_documents({}) == 0: continue

        elif datetime.datetime.now().day == 1 and datetime.datetime.now().month % 2 == 0:

            HISTORY.delete_many({})
            continue