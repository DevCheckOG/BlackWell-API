"""BlackWell API."""

import fastapi
import datetime
import threading
import dotenv

from typing import Any, Dict, List, Literal
from core.systems import Parser, UserManager, IPLimiter
from core.models import *
from core.db.primary import (
    get_token_with_email_and_password,
    cleaner_history,
    set_user_profile,
    get_user,
    check_if_user_in_contacts,
    get_user_profile,
)
from core.db.secundary import cleaner_temporal_accounts, cleaner_queue_history
from core.gateway import GATEWAY_CONEXIONS, Gateway
from core.constants import Constants

dotenv.load_dotenv()

API: fastapi.FastAPI = fastapi.FastAPI(
    title=Constants.TITLE.value,
    version=Constants.VERSION.value,
    docs_url="/tests/",
    redoc_url=None,
    summary=f'The main API for BlackWell. {datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d")} DevCheckOG | Kevin Benavides',
)


@API.on_event("startup")
async def startup() -> None:

    await Gateway.load()

    threading.Thread(
        target=cleaner_temporal_accounts, name="| Temporal Accounts |"
    ).start()
    threading.Thread(target=cleaner_history, name="| History |").start()
    threading.Thread(target=cleaner_queue_history, name="| Queue - History |").start()


@API.get("/", description=f"{Constants.TITLE.value}.")
@IPLimiter.limiter(max_calls=10, time=60)
async def root(request: fastapi.Request) -> fastapi.responses.JSONResponse:

    return fastapi.responses.JSONResponse(
        content={
            "title": Constants.TITLE.value,
            "version": Constants.VERSION.value,
            "author": {
                "name": "Kevin Benavides",
                "twitter": "https://twitter.com/DevCheckOG",
                "github": "https://github.com/DevCheckOG",
            },
            "date": datetime.datetime.strftime(
                datetime.datetime.now(), "%Y-%m-%d %H:%M"
            ),
        }
    )


@API.websocket("/gateway")
async def gateway(
    websocket: fastapi.WebSocket, email: str | None, password: str | None
) -> None | Any:

    if email is None or password is None:

        await websocket.accept()
        await websocket.send_json(
            {
                "title": "BlackWell API - Bad Connection to the Gateway",
                "message": "Please provide an email and a password.",
                "status": Constants.REQUIRED_EMAIL_AND_PASSWORD_IN_THE_GATEWAY.value,
            }
        )

        await websocket.close()
        return

    elif not any(
        email == conexion["email"] and password == conexion["password"]
        for conexion in GATEWAY_CONEXIONS
    ):

        await websocket.accept()
        await websocket.send_json(
            {
                "title": "BlackWell API - Bad Connection to the Gateway",
                "message": "The credentials are not valid.",
                "status": Constants.INCORRECT_CREDENTIALS_IN_THE_GATEWAY.value,
            }
        )

        await websocket.close()
        return

    Gateway.connect(email, password, websocket)

    try:

        while True:

            if websocket.client_state == fastapi.websockets.WebSocketState.DISCONNECTED:
                Gateway.disconnect(websocket)
                break

            await websocket.receive()

    except:

        Gateway.disconnect(websocket)


@API.post("/login")
@IPLimiter.limiter(max_calls=2, time=30)
async def login(
    request: fastapi.Request, data: Login
) -> fastapi.responses.JSONResponse:

    result: Dict[str, Any] = await UserManager().login(data.email, data.password)

    return fastapi.responses.JSONResponse(content=result)


@API.post("/register")
@IPLimiter.limiter(max_calls=5, time=30)
async def register(
    request: fastapi.Request, data: Register
) -> fastapi.responses.JSONResponse:

    result: Dict[str, Any] = await UserManager().register_user(
        data.username, data.email, data.password
    )

    return fastapi.responses.JSONResponse(content=result)


@API.post("/verify")
@IPLimiter.limiter(max_calls=5, time=30)
async def verify(
    request: fastapi.Request, data: Verify
) -> fastapi.responses.JSONResponse:

    result: Dict[str, Any] = await UserManager().verify_user(data.code)

    return fastapi.responses.JSONResponse(content=result)


@API.post("/user/delete")
@IPLimiter.limiter(max_calls=50, time=20)
async def delete_user(
    request: fastapi.Request, data: DeleteUser
) -> fastapi.responses.JSONResponse:

    result: Dict[str, Any] = await UserManager().delete_user(data.email, data.password)

    return fastapi.responses.JSONResponse(content=result)


@API.post("/user/token")
@IPLimiter.limiter(max_calls=10, time=60)
async def token(
    request: fastapi.Request, data: Token
) -> fastapi.responses.JSONResponse:

    result: list[str, Any] | bool = await get_token_with_email_and_password(
        data.email, data.password
    )

    if isinstance(result, list):

        return fastapi.responses.JSONResponse(
            content={
                "username": result[1],
                "token": result[0],
                "status": Constants.OK.value,
                "date": datetime.datetime.strftime(
                    datetime.datetime.now(), "%Y-%m-%d %H:%M"
                ),
            }
        )

    return fastapi.responses.JSONResponse(
        content={
            "title": "BlackWell API - Incorrect Credentials",
            "message": "The email or password is not valid. Or the user does not exist.",
            "status": Constants.EMAIL_AND_PASSWORD_IS_NOT_VALID.value,
            "date": datetime.datetime.strftime(
                datetime.datetime.now(), "%Y-%m-%d %H:%M"
            ),
        }
    )


@API.post("user/set-profile")
@IPLimiter.limiter(max_calls=5, time=20)
async def set_profile(
    request: fastapi.Request, data: SetProfile
) -> fastapi.responses.JSONResponse:

    if not Parser().is_hex(data.image) or not Parser().check_img_or_video_size(
        bytes.fromhex(data.image)
    ):

        return fastapi.responses.JSONResponse(
            content={
                "title": "BlackWell API - Incorrect Image",
                "message": "The size of the image is not valid or the image not is a hex.",
                "status": Constants.INCORRECT_SIZE_IMAGE.value,
                "date": datetime.datetime.strftime(
                    datetime.datetime.now(), "%Y-%m-%d %H:%M"
                ),
            }
        )

    result: bool = await set_user_profile(data.token, data.image)

    if result:

        return fastapi.responses.JSONResponse(
            content={
                "title": "BlackWell API - Profile Image Updated",
                "message": "The profile image was updated successfully.",
                "status": Constants.OK.value,
                "date": datetime.datetime.strftime(
                    datetime.datetime.now(), "%Y-%m-%d %H:%M"
                ),
            }
        )

    return fastapi.responses.JSONResponse(
        content={
            "title": "BlackWell API - Incorrect Token",
            "message": "The token is not valid.",
            "status": Constants.INCORRECT_TOKEN_FOR_THE_USER.value,
            "date": datetime.datetime.strftime(
                datetime.datetime.now(), "%Y-%m-%d %H:%M"
            ),
        }
    )


@API.post("/user/profile")
@IPLimiter.limiter(max_calls=25, time=20)
async def profile(
    request: fastapi.Request, data: Profile
) -> fastapi.responses.JSONResponse:

    result: Dict[str, Any] | bool = await get_user(data.token)

    if isinstance(result, dict):

        contact_profile: bool = await check_if_user_in_contacts(
            data.token, data.username
        )

        if not contact_profile:

            return fastapi.responses.JSONResponse(
                content={
                    "title": "BlackWell API - User not found",
                    "message": "The user is not in your contacts.",
                    "status": Constants.INVALID_USER_IN_CONCTACTS.value,
                    "date": datetime.datetime.strftime(
                        datetime.datetime.now(), "%Y-%m-%d %H:%M"
                    ),
                }
            )

        profile: List[str] | bool = await get_user_profile(data.token, data.username)

        if not isinstance(profile, list):

            return fastapi.responses.JSONResponse(
                content={
                    "title": "BlackWell API - User not found",
                    "message": "The user is not in your contacts.",
                    "status": Constants.INVALID_USER_IN_CONCTACTS.value,
                    "date": datetime.datetime.strftime(
                        datetime.datetime.now(), "%Y-%m-%d %H:%M"
                    ),
                }
            )

        return fastapi.responses.JSONResponse(
            content={
                "title": "BlackWell API - User Profile",
                "message": {
                    "username": profile[0],
                    "image": profile[1],
                },
                "status": Constants.OK.value,
                "date": datetime.datetime.strftime(
                    datetime.datetime.now(), "%Y-%m-%d %H:%M"
                ),
            }
        )

    return fastapi.responses.JSONResponse(
        content={
            "title": "BlackWell API - Incorrect Credentials",
            "message": "The token is not valid. Or the user does not exist.",
            "status": Constants.INCORRECT_TOKEN_FOR_THE_USER.value,
            "date": datetime.datetime.strftime(
                datetime.datetime.now(), "%Y-%m-%d %H:%M"
            ),
        }
    )


@API.post("/messages/send")
@IPLimiter.limiter(max_calls=10, time=5)
async def send_message(
    request: fastapi.Request,
    type: Literal["img", "video", "text"] | None,
    data: SendMessage,
) -> fastapi.responses.JSONResponse:

    if type is None:

        return fastapi.responses.JSONResponse(
            content={
                "title": "BlackWell API - Bad Type",
                "message": "The type of message is not valid.",
                "status": Constants.REQUIRED_TYPE_OF_MESSAGE.value,
                "date": datetime.datetime.strftime(
                    datetime.datetime.now(), "%Y-%m-%d %H:%M"
                ),
            }
        )

    elif type not in ["img", "video", "text"]:

        return fastapi.responses.JSONResponse(
            content={
                "title": "BlackWell API - Bad Type",
                "message": "The type of message is not valid.",
                "status": Constants.INCORRECT_TYPE_OF_MESSAGE.value,
                "date": datetime.datetime.strftime(
                    datetime.datetime.now(), "%Y-%m-%d %H:%M"
                ),
            }
        )

    elif type == "text":

        parsed_message: Dict[str, Any] | bool = Parser().parse_plane_text(data.message)

        if not isinstance(parsed_message, dict):

            return fastapi.responses.JSONResponse(
                content={
                    "title": "BlackWell API - Incorrect Syntax in Message Post",
                    "message": "The message is not valid. Please use the correct syntax.",
                    "status": Constants.INCORRECT_SYNTAX.value,
                    "date": datetime.datetime.strftime(
                        datetime.datetime.now(), "%Y-%m-%d %H:%M"
                    ),
                }
            )

        elif not any(
            data.email == conexion["email"] and data.password == conexion["password"]
            for conexion in GATEWAY_CONEXIONS
        ):

            return fastapi.responses.JSONResponse(
                content={
                    "title": "BlackWell API - Gateway mistake",
                    "message": "The credentials are not valid.",
                    "status": Constants.INCORRECT_CREDENTIALS_IN_THE_GATEWAY.value,
                    "date": datetime.datetime.strftime(
                        datetime.datetime.now(), "%Y-%m-%d %H:%M"
                    ),
                }
            )

        result: bool | str = await Gateway.send_message(data.to, parsed_message)

        if isinstance(result, str):

            return fastapi.responses.JSONResponse(
                content={
                    "title": "BlackWell API - Gateway mistake",
                    "message": result,
                    "status": Constants.INCORRECT_USERNAME_IN_THE_GATEWAY.value,
                    "date": datetime.datetime.strftime(
                        datetime.datetime.now(), "%Y-%m-%d %H:%M"
                    ),
                }
            )

        return fastapi.responses.JSONResponse(
            content={
                "title": "BlackWell API - Message Sent",
                "message": "The message was sent.",
                "status": Constants.OK.value,
                "date": datetime.datetime.strftime(
                    datetime.datetime.now(), "%Y-%m-%d %H:%M"
                ),
            }
        )

    elif type == "img":

        parsed_message: Dict[str, Any] | bool = Parser().parse_video_or_img_message(
            data.message
        )

        if not Parser.is_hex(
            parsed_message["contain"]
        ) or not Parser().check_img_or_video_size(
            bytes.fromhex(parsed_message["contain"])
        ):

            return fastapi.responses.JSONResponse(
                content={
                    "title": "BlackWell API - Incorrect Size Image",
                    "message": "The size of the image is not valid or the image not this in hex. Please use the correct syntax.",
                    "status": Constants.INCORRECT_SIZE_IMAGE.value,
                    "date": datetime.datetime.strftime(
                        datetime.datetime.now(), "%Y-%m-%d %H:%M"
                    ),
                }
            )

        elif not isinstance(parsed_message, dict):

            return fastapi.responses.JSONResponse(
                content={
                    "title": "BlackWell API - Incorrect Syntax in Message Post",
                    "message": "The message is not valid. Please use the correct syntax.",
                    "status": Constants.INCORRECT_SYNTAX.value,
                    "date": datetime.datetime.strftime(
                        datetime.datetime.now(), "%Y-%m-%d %H:%M"
                    ),
                }
            )

        elif not any(
            data.email == conexion["email"] and data.password == conexion["password"]
            for conexion in GATEWAY_CONEXIONS
        ):

            return fastapi.responses.JSONResponse(
                content={
                    "title": "BlackWell API - Gateway mistake",
                    "message": "The credentials are not valid.",
                    "status": Constants.INCORRECT_CREDENTIALS_IN_THE_GATEWAY.value,
                    "date": datetime.datetime.strftime(
                        datetime.datetime.now(), "%Y-%m-%d %H:%M"
                    ),
                }
            )

        result: bool | str = await Gateway.send_message(data.to, parsed_message)

        if isinstance(result, str):

            return fastapi.responses.JSONResponse(
                content={
                    "title": "BlackWell API - Gateway mistake",
                    "message": result,
                    "status": Constants.INCORRECT_USERNAME_IN_THE_GATEWAY.value,
                    "date": datetime.datetime.strftime(
                        datetime.datetime.now(), "%Y-%m-%d %H:%M"
                    ),
                }
            )

        return fastapi.responses.JSONResponse(
            content={
                "title": "BlackWell API - Message Sent",
                "message": "The message was sent.",
                "status": Constants.OK.value,
                "date": datetime.datetime.strftime(
                    datetime.datetime.now(), "%Y-%m-%d %H:%M"
                ),
            }
        )

    elif type == "video":

        parsed_message: Dict[str, Any] | bool = Parser().parse_video_or_img_message(
            data.message
        )

        if not Parser.is_hex(
            parsed_message["contain"]
        ) or not Parser().check_img_or_video_size(
            bytes.fromhex(parsed_message["contain"])
        ):

            return fastapi.responses.JSONResponse(
                content={
                    "title": "BlackWell API - Incorrect Size Video",
                    "message": "The size of the video is not valid or the video not this in hex. Please use the correct syntax.",
                    "status": Constants.INCORRECT_SIZE_VIDEO.value,
                    "date": datetime.datetime.strftime(
                        datetime.datetime.now(), "%Y-%m-%d %H:%M"
                    ),
                }
            )

        elif not isinstance(parsed_message, dict):

            return fastapi.responses.JSONResponse(
                content={
                    "title": "BlackWell API - Incorrect Syntax in Message Post",
                    "message": "The message is not valid. Please use the correct syntax.",
                    "status": Constants.INCORRECT_SYNTAX.value,
                    "date": datetime.datetime.strftime(
                        datetime.datetime.now(), "%Y-%m-%d %H:%M"
                    ),
                }
            )

        elif not any(
            data.email == conexion["email"] and data.password == conexion["password"]
            for conexion in GATEWAY_CONEXIONS
        ):

            return fastapi.responses.JSONResponse(
                content={
                    "title": "BlackWell API - Gateway mistake",
                    "message": "The credentials are not valid.",
                    "status": Constants.INCORRECT_CREDENTIALS_IN_THE_GATEWAY.value,
                    "date": datetime.datetime.strftime(
                        datetime.datetime.now(), "%Y-%m-%d %H:%M"
                    ),
                }
            )

        result: bool | str = await Gateway.send_message(data.to, parsed_message)

        if isinstance(result, str):

            return fastapi.responses.JSONResponse(
                content={
                    "title": "BlackWell API - Gateway mistake",
                    "message": result,
                    "status": Constants.INCORRECT_USERNAME_IN_THE_GATEWAY.value,
                    "date": datetime.datetime.strftime(
                        datetime.datetime.now(), "%Y-%m-%d %H:%M"
                    ),
                }
            )

        return fastapi.responses.JSONResponse(
            content={
                "title": "BlackWell API - Message Sent",
                "message": "The message was sent.",
                "status": Constants.OK.value,
                "date": datetime.datetime.strftime(
                    datetime.datetime.now(), "%Y-%m-%d %H:%M"
                ),
            }
        )


@API.get("/messages/delete")
async def delete_messages(
    request: fastapi.Request, data: DeleteMessage
) -> fastapi.responses.JSONResponse:

    if not any(
        data.email == conexion["email"] and data.password == conexion["password"]
        for conexion in GATEWAY_CONEXIONS
    ):

        return fastapi.responses.JSONResponse(
            content={
                "title": "BlackWell API - Gateway mistake",
                "message": "The credentials are not valid.",
                "status": Constants.INCORRECT_CREDENTIALS_IN_THE_GATEWAY.value,
                "date": datetime.datetime.strftime(
                    datetime.datetime.now(), "%Y-%m-%d %H:%M"
                ),
            }
        )

    result: bool | str = await Gateway.send_message(
        data.to,
        {
            "title": "BlackWell API - Actions -> Delete Message",
            "from": data.from_,
            "message id": data.message_id,
            "action": "delete message",
            "date": datetime.datetime.strftime(
                datetime.datetime.now(), "%Y-%m-%d %H:%M"
            ),
        },
    )

    if isinstance(result, str):

        return fastapi.responses.JSONResponse(
            content={
                "title": "BlackWell API - Gateway mistake",
                "message": result,
                "status": Constants.INCORRECT_USERNAME_IN_THE_GATEWAY.value,
                "date": datetime.datetime.strftime(
                    datetime.datetime.now(), "%Y-%m-%d %H:%M"
                ),
            }
        )

    return fastapi.responses.JSONResponse(
        content={
            "title": "BlackWell API - Message Deleted",
            "message": "The message was deleted.",
            "status": Constants.OK.value,
            "date": datetime.datetime.strftime(
                datetime.datetime.now(), "%Y-%m-%d %H:%M"
            ),
        }
    )


"""Exception Handlers."""


@API.exception_handler(fastapi.status.HTTP_429_TOO_MANY_REQUESTS)
def rate_limit_exceeded(
    request: fastapi.Request, exc: fastapi.exceptions.HTTPException
) -> fastapi.responses.JSONResponse:

    return fastapi.responses.JSONResponse(
        content={
            "title": "BlackWell API - Rate Limit Exceeded",
            "message": exc.detail,
            "date": datetime.datetime.strftime(
                datetime.datetime.now(), "%Y-%m-%d %H:%M"
            ),
        },
        status_code=exc.status_code,
    )


@API.exception_handler(fastapi.status.HTTP_404_NOT_FOUND)
async def not_found(
    request: fastapi.Request, exc: fastapi.exceptions.HTTPException
) -> fastapi.responses.JSONResponse:

    return fastapi.responses.JSONResponse(
        content={
            "title": "BlackWell API - Not Found",
            "message": exc.detail,
            "date": datetime.datetime.strftime(
                datetime.datetime.now(), "%Y-%m-%d %H:%M"
            ),
        },
        status_code=exc.status_code,
    )


@API.exception_handler(fastapi.status.HTTP_422_UNPROCESSABLE_ENTITY)
async def unprocessable_entity(
    request: fastapi.Request, exc: fastapi.exceptions.HTTPException
) -> fastapi.responses.JSONResponse:

    return fastapi.responses.JSONResponse(
        content={
            "title": "BlackWell API - Unprocessable Entity",
            "message": exc.detail,
            "date": datetime.datetime.strftime(
                datetime.datetime.now(), "%Y-%m-%d %H:%M"
            ),
        },
        status_code=exc.status_code,
    )


@API.exception_handler(fastapi.status.HTTP_503_SERVICE_UNAVAILABLE)
async def overloaded(
    request: fastapi.Request, exc: fastapi.exceptions.HTTPException
) -> fastapi.responses.JSONResponse:

    return fastapi.responses.JSONResponse(
        content={
            "title": "BlackWell API - Overloaded",
            "message": exc.detail,
            "date": datetime.datetime.strftime(
                datetime.datetime.now(), "%Y-%m-%d %H:%M"
            ),
        },
        status_code=exc.status_code,
    )


API.add_exception_handler(
    fastapi.status.HTTP_422_UNPROCESSABLE_ENTITY, unprocessable_entity
)
API.add_exception_handler(fastapi.status.HTTP_404_NOT_FOUND, not_found)
API.add_exception_handler(
    fastapi.status.HTTP_429_TOO_MANY_REQUESTS, rate_limit_exceeded
)
API.add_exception_handler(fastapi.status.HTTP_503_SERVICE_UNAVAILABLE, overloaded)
