from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    emailVerified: bool
    createdAt: datetime
    updatedAt: datetime
    image: str | None = None
    preferred_provider: str | None = None


class ConversationCreateRequest(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=160)


class ConversationUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)


class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class MessageCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=8000)


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    tool_name: str | None
    created_at: datetime


class AgentMessageResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse


class ApiKeyUpsertRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=80)
    api_key: str = Field(min_length=1, max_length=4096)


class ApiKeyMetadataResponse(BaseModel):
    provider: str
    created_at: datetime


class ApiKeyListResponse(BaseModel):
    providers: list[ApiKeyMetadataResponse]


class DocumentCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=200_000)


class DocumentResponse(BaseModel):
    id: str
    title: str
    source_type: str
    chunk_count: int
    created_at: datetime


class DocumentJobResponse(BaseModel):
    job_id: str
    status: str


class DocumentJobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: dict | None = None
    error: str | None = None


class AgentJobResponse(BaseModel):
    job_id: str
    status: str
    user_message: MessageResponse


class AgentJobStatusResponse(BaseModel):
    job_id: str
    status: str
    assistant_message: MessageResponse | None = None
    error: str | None = None
