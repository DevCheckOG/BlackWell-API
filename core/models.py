"""The BaseModel of BlackWell API."""

from pydantic import BaseModel
from typing import Any, Dict


class Register(BaseModel):

    username: str
    email: str
    password: str


class Verify(BaseModel):

    code: str


class Token(BaseModel):

    email: str
    password: str


class SetProfile(BaseModel):

    token: str
    image: str


class DeleteUser(BaseModel):

    email: str
    password: str


class Profile(BaseModel):

    token: str
    username: str


class Login(BaseModel):

    email: str
    password: str


class SendMessage(BaseModel):

    email: str
    password: str

    to: str
    message: Dict[str, Any] = {"id": "", "type": "", "from": "", "contain": ""}


class DeleteMessage(BaseModel):

    email: str
    password: str

    to: str
    from_: str
    message_id: str


class LastMessage(BaseModel):

    token: str
