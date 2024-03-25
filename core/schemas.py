""""Schemas for BlackWell API."""

import uuid
import datetime
import random

from typing import Any, Dict, Literal

def generate_text_plane_schema(from_ : str = 'System', contain : str = '') -> Dict[str, Any]:
    """Generate text plane schema."""

    TEXT_PLANE : Dict[str, Any] = {

        'id' : str(uuid.uuid4().int),
        'type' : 'text',
        'from' : from_,
        'read' : True if from_ == 'System' else False,
        'contain' : contain

    }   

    return TEXT_PLANE

def generate_img_or_video_schema(from_ : str = 'System', type : Literal['img', 'video'] = 'img', contain : str = '') -> Dict[str, Any]:
    """Generate img or video schema."""
   
    IMG_OR_VIDEO : Dict[str, Any] = {
        
        'id' : str(uuid.uuid4().int),
        'type' : type,
        'from' : from_,
        'read' : True if from_ == 'System' else False,
        'contain' : contain

    }

    return IMG_OR_VIDEO 

def generate_temp_user_schema(profile : str = '', username : str = '', email : str = '', password : str = '') -> Dict[str, Any]:
    """Generate temp user schema."""

    TEMP_USER : Dict[str, Any] = {

        '_id' : uuid.uuid4().hex, 
        'profile' : '',
        'username' : username,
        'email' : email,
        'password' : password,
        'created-at' : '', 
        'verification' : {

            'remaining' : str(datetime.datetime.now() + datetime.timedelta(minutes= 3)),
            'code' : str(random.randint(1000, 9999)) + str(random.randint(1000, 9999))

        },
        'contacts' : []

    }

    return TEMP_USER