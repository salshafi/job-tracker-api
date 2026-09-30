from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


# The only statuses an application is allowed to have
class Status(StrEnum):
    saved = "saved"
    applied = "applied"
    interview = "interview"
    offer = "offer"
    rejected = "rejected"


# What the client sends when creating an application
class ApplicationCreate(BaseModel):
    # use_enum_values stores plain text like "saved" instead of an enum object
    model_config = ConfigDict(use_enum_values=True)

    company: str = Field(min_length=1, max_length=100)
    role: str = Field(min_length=1, max_length=100)
    status: Status = Status.saved
    job_url: str | None = None
    date_applied: date | None = None
    notes: str | None = None


# What the client sends when changing an application.
# Every field is optional, so they can send only what changed.
# Type is "str" (not "str | None") so sending null for a required field is rejected.
class ApplicationUpdate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    company: str = Field(default=None, min_length=1, max_length=100)
    role: str = Field(default=None, min_length=1, max_length=100)
    status: Status = None
    job_url: str | None = None
    date_applied: date | None = None
    notes: str | None = None


# What the API sends back: everything above, plus the id and created time
class ApplicationOut(ApplicationCreate):
    # from_attributes lets Pydantic read values from a database object
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime