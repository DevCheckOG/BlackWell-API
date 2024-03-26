"""The systems of BlackWell."""

# Standard modules.

import datetime
import uuid
import smtplib
import re

from email.message import EmailMessage
from typing import Any, Awaitable, Callable, Dict, List
from functools import wraps

# Third party modules.

import fastapi

# Own modules.

from .db.primary import fetch_user, delete_user, get_secret, post_user, get_user_with_email_and_password
from .db.secundary import find_possible_user, post_temp_user, terminate_temp_user, is_valid_verification_code, get_temp_user
from .schemas import generate_temp_user_schema
from .gateway import GatewayManager
from .constants import Constants

class IPLimiter:

    @staticmethod
    def limiter(max_calls : int, time : int) -> Callable:

        def decorator(func : Callable) -> Callable:

            calls : List[Dict[str, Any]] = []

            @wraps(func)
            async def wrapper(request : fastapi.Request, *args, **kwargs) -> Awaitable:

                if request.client is None: return await func(request, *args, **kwargs)

                elif len(calls) == 0: calls.append({'ip' : request.client.host, 'counter' : {'num' : 1, 'time' : str(datetime.datetime.now())}, 'time' : '', 'block' : False})

                for call in calls:

                    if request.client.host not in [z['ip'] for z in calls]:

                        calls.append({'ip' : request.client.host, 'counter' : {'num' : 1, 'time' : str(datetime.datetime.now())}, 'time' : '', 'block' : False})

                    if call['counter']['num'] >= max_calls:

                        if not call['block']: 

                            call['time'] = str(datetime.datetime.now() + datetime.timedelta(seconds= time))
                            call['block'] = True

                        elif datetime.datetime.strptime(call['time'], '%Y-%m-%d %H:%M:%S.%f') <= datetime.datetime.now():

                            calls.remove(call) 
                            continue     
                        
                        raise fastapi.HTTPException(status_code= fastapi.status.HTTP_429_TOO_MANY_REQUESTS, detail= f"Too many requests. Unlock to the: {datetime.datetime.strftime(datetime.datetime.strptime(call['time'], '%Y-%m-%d %H:%M:%S.%f'), '%H:%M:%S')}")    

                    if datetime.datetime.strptime(call['counter']['time'], '%Y-%m-%d %H:%M:%S.%f') + datetime.timedelta(seconds= 10) <= datetime.datetime.now():

                        calls.remove(call) 
                        continue    

                    if request.client.host in [z['ip'] for z in calls]:

                        call['counter']['num'] += 1  
                        call['counter']['time'] = str(datetime.datetime.now())    

                return await func(request, *args, **kwargs)
            
            return wrapper
        
        return decorator

class Parser:

    def parse_plane_text(self, message : Dict[str, Any]) -> Dict[str, Any] | bool:
        """Parsing plane text."""

        for key in message.keys():

            if key not in ['id', 'type', 'read', 'from', 'contain']:

                return False
            
        for key, value in message.items():

            if not isinstance(value, str): return False

            elif key == 'id':

                message['id'] = str(uuid.uuid4().int)
                continue

            elif key == 'type' and value != 'text': return False
            
        return message

    def parse_video_or_img_message(self, message : Dict[str, Any]) -> Dict[str, Any] | bool:
        """Parsing video or image message."""

        for key in message.keys():

            if key not in ['id', 'type', 'read', 'from', 'contain']:
                return False
            
        for key, value in message.items():  

            if not isinstance(value, str): return False 

            elif key == 'id':

                message['id'] = str(uuid.uuid4().int)
                continue

            elif key == 'type' and value not in ['img', 'video']: return False
        
        return message  

    def check_img_or_video_size(self, img_or_video : bytes) -> bool:
        """Checking if the img or video have the correct size."""

        return True if round(len(img_or_video) / 1048576) <= 5 else False
    	
    def is_hex(self, string : str) -> bool:
        """Checking if string is hex."""

        return bool(re.match(r'^[0-9a-fA-F]+$', string))

class EmailSystem:

    async def send_email(self, to : str = '', message : str = """""") -> bool:
        """Sending email with an verification code."""

        if to.endswith('@gmail.com'):

            gmail_code : Dict[str, Any] | bool = await get_secret('gmail code')
            gmail_sender : Dict[str, Any] | bool = await get_secret('gmail')

            if not isinstance(gmail_code, dict): return False
            elif not isinstance(gmail_sender, dict): return False

            email = EmailMessage()
            email['From'] = gmail_sender['gmail']
            email['To'] = to
            email['Subject'] = 'BlackWell - Email Verification'

            email.set_content(message)

            smtp: smtplib.SMTP_SSL = smtplib.SMTP_SSL('smtp.gmail.com')
            smtp.login(gmail_sender['gmail'], gmail_code['code'])
            smtp.sendmail(gmail_sender['gmail'], to, email.as_string())
            smtp.quit()

            return True

        """

        Coming Soon...

        elif to.endswith('@outlook.com'):

            smtp = smtplib.SMTP_SSL('smtp-mail.outlook.com', port= 587)
            smtp.login(sender, "clave_de_gmail_123")
            smtp.sendmail(sender, to, email.as_string())
            smtp.quit()    

            return True

        """    
        
        return False    

class UserManager:

    async def register_user(self, username : str, email : str, password : str) -> Dict[str, Any]: 
        """Registering user at a temp database."""

        TEMP_USER : Dict[str, Any] = generate_temp_user_schema(profile = '', username = username, email = email, password = password)
        
        possible_user : bool = await find_possible_user(TEMP_USER['username'], TEMP_USER['email'])

        if not possible_user:

            return {
                
                'title' : Constants.TITLE.value,
                'message' : 'The account already exists.',
                'status' : Constants.USER_EXISTS.value,
                'date' : datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M')

            }
        
        result_post_temp_user : bool = await post_temp_user(TEMP_USER)

        if not result_post_temp_user:

            return {
                
                'title' : Constants.TITLE.value,
                'message' : 'The temporary account could not be created.',
                'status' : Constants.UNKNOWN_ERROR.value,
                'date' : datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M')

            }
        
        send_code : bool = await EmailSystem().send_email(to= TEMP_USER['email'], message= f"""
        Welcome to BlackWell.
                        
        The email verification code is: {TEMP_USER['verification']['code']}                 
        """)

        if not send_code:

            await terminate_temp_user(TEMP_USER['_id'])

            return {
                
                'title' : Constants.TITLE.value,
                'message' : 'The mensage to the email could not be send.',
                'status' : Constants.EMAIL_SEND_ERROR.value,
                'date' : datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M')

            }
        
        return {

            'title' : Constants.TITLE.value,
            'message' : 'You have 3 minutes to check the email.',
            'status' : Constants.OK.value,
            'date' : datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M')

        }

    async def verify_user(self, code : str) -> Dict[str, Any] | bool:
        """Verifying user at a temp database and creating a user at the primary database."""

        is_valid : bool = await is_valid_verification_code(code)

        if not is_valid:

            return {
                
                'title' : Constants.TITLE.value,
                'message' : 'The code is not valid.',
                'status' : Constants.EMAIL_CODE_INVALID.value,
                'date' : datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M')

            }
        
        temp_user : Dict[str, Any] | bool = await get_temp_user(code)

        if isinstance(temp_user, dict):

            temp_user['created-at'] = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M')

            result : bool = await post_user(temp_user)

            if result:

                await terminate_temp_user(temp_user['_id'])
                await GatewayManager.add(temp_user['username'], temp_user['email'], temp_user['password'])

                return {

                    'title' : Constants.TITLE.value,
                    'message' : 'The user has been registered.',
                    'status' : Constants.OK.value,
                    'date' : datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M')

                }
            
            return {
                
                'title' : Constants.TITLE.value,
                'message' : 'The user could not be registered.',
                'status' : Constants.UNKNOWN_ERROR.value,
                'date' : datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M')

            }

        return {

            'title' : Constants.TITLE.value,
            'message' : 'Mistake to the get the temporary account.',
            'status' : Constants.UNKNOWN_ERROR.value,
            'date' : datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M')

        }

    async def delete_user(self, email : str = '', password : str = '') -> Dict[str, Any]:
        """Deleting user at the primary database."""

        fetch : bool = await fetch_user(email, password)

        if not fetch:

            return {
                
                'title' : Constants.TITLE.value,
                'message' : 'El usuario no se pudo obtener.',
                'status' : Constants.USER_NOT_FOUND.value,
                'date' : datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M')

            }
        
        result : bool = await delete_user(email, password)

        if result:

            await GatewayManager.remove(email, password)

            return {

                'title' : Constants.TITLE.value,
                'message' : 'The user has been deleted.',
                'status' : Constants.OK.value,
                'date' : datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M')
                
            }

        return {

            'title' : Constants.TITLE.value,
            'message' : 'The user could not be deleted.',
            'status' : Constants.UNKNOWN_ERROR.value,
            'date' : datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M')

        }
    
    async def login(self, email : str = '', password : str = '') -> Dict[str, Any]:
        """Logging user at the primary database."""

        user : Dict[str, Any] | bool = await get_user_with_email_and_password(email, password)

        if isinstance(user, dict):

            return {

                'profile' : user['profile'],
                'username' : user['username'],
                'contacts' : user['contacts'],
                'status' : Constants.OK.value,
                'date' : datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M')

            }
        
        return {

            'title' : Constants.TITLE.value,
            'message' : 'The user could not be found.',
            'status' : Constants.USER_NOT_FOUND.value,
            'date' : datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M')

        }