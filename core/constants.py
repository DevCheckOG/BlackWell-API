"""The constants of BlackWell API."""

from enum import Enum

class Constants(Enum):

    TITLE : str = 'BlackWell API'
    VERSION : str = '1.0'

    # All Status

    OK : str = 'ok'

    UNKNOWN_ERROR : str = 'unknown error'

    EMAIL_ERROR : str = 'email error'
    EMAIL_SEND_ERROR : str = 'email send error'
    EMAIL_CODE_ERROR : str = 'email code error'
    EMAIL_CODE_INVALID : str = 'invalid email code'
    INCORRECT_TOKEN_FOR_THE_USER : str = 'incorrect token for the user'
    USER_ERROR : str = 'user error'
    USER_NOT_FOUND : str = 'user not found'
    USER_EXISTS : str = 'user exists'
    USER_DELETED : str = 'user deleted'

    EMAIL_AND_PASSWORD_IS_NOT_VALID : str = 'email and password is not valid'
    EMAIL_AND_PASSWORD_IS_NOT_VALID_OR_USER_NOT_EXISTS : str = 'email and password is not valid or user not exists'
    INCORRECT_SYNTAX : str = 'incorrect syntax'

    REQUIRED_EMAIL_AND_PASSWORD_IN_THE_GATEWAY : str = 'required email and password in the gateway'
    REQUIRED_EMAIL_AND_PASSWORD_AND_USERNAME_IN_THE_GATEWAY : str = 'required email and password and username in the gateway'
    INCORRECT_CREDENTIALS_IN_THE_GATEWAY : str = 'incorrect credentials in the gateway'
    INCORRECT_USERNAME_IN_THE_GATEWAY : str = 'incorrect username in the gateway'

    REQUIRED_TYPE_OF_MESSAGE : str = 'required valid type of message'
    INCORRECT_TYPE_OF_MESSAGE : str = 'incorrect type of message'

    INCORRECT_SIZE_IMAGE : str = 'incorrect size image'
    INCORRECT_SIZE_VIDEO : str = 'incorrect size video'

    INVALID_USER_IN_CONCTACTS : str = 'invalid user in contacts'
    USER_PROFILE_NOT_FOUND : str = 'user profile not found'
    