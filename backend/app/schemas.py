from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=10, max_length=128)
    display_name: str = Field(default="", max_length=80)


class RoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    friend_ids: list[int] = Field(default_factory=list, max_length=100)
    employee_ids: list[int] = Field(default_factory=list, max_length=50)


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=10000)
    message_type: str = Field(default="text", pattern="^(text|emoji|image)$")

    @model_validator(mode="after")
    def validate_image_url(self):
        if self.message_type == "image":
            parsed = urlparse(self.content)
            if parsed.scheme not in {"https", "http"} or not parsed.netloc:
                raise ValueError("image messages require an HTTP or HTTPS URL")
        return self


class ModelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    provider: str = Field(default="openai-compatible", max_length=80)
    base_url: str = Field(min_length=1, max_length=500)
    model_name: str = Field(min_length=1, max_length=100)
    api_key: str = Field(min_length=1, max_length=1000)

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str):
        parsed = urlparse(value)
        local_http = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"}
        if parsed.scheme != "https" and not local_http:
            raise ValueError("base_url must use HTTPS (HTTP is allowed only for localhost)")
        if not parsed.hostname:
            raise ValueError("base_url must include a hostname")
        return value.rstrip("/")


class ToolCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$")
    description: str = Field(min_length=1, max_length=500)
    parameters_schema: dict
    function_code: str = Field(default="", max_length=10000)
    enabled: bool = True


class EmployeeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    system_prompt: str = Field(default="", max_length=10000)
    model_id: int | None = None
    tool_ids: list[int] = Field(default_factory=list, max_length=50)
