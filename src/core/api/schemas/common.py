"""Shared schema models."""

from pydantic import BaseModel


class CredentialsModel(BaseModel):
    email: str
    password: str


class TaskResponse(BaseModel):
    task_id: str
