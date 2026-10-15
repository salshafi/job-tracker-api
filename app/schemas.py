from datetime import date, datetime
from enum import StrEnum
from typing import Annotated
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


# The only statuses an application is allowed to have
class Status(StrEnum):
    saved = "saved"
    applied = "applied"
    interview = "interview"
    offer = "offer"
    rejected = "rejected"


# Text that is trimmed first, so "   " counts as empty and " Acme " becomes "Acme"
CleanName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


# Shared clean-up for the two optional text fields (job_url and notes)
class OptionalTextMixin(BaseModel):
    @field_validator("job_url", "notes", mode="before", check_fields=False)
    @classmethod
    def blank_to_none(cls, value):
        # Trim spaces; an empty or blank string is stored as "no value"
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("job_url", check_fields=False)
    @classmethod
    def job_url_must_be_web_link(cls, value):
        if value is None:
            return value
        if len(value) > 500:
            raise ValueError("job_url must be 500 characters or fewer")
        parsed = urlparse(value)
        # Only http and https links with a host name are allowed
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("job_url must be a valid http or https link")
        return value


# What the client sends when creating an application
class ApplicationCreate(OptionalTextMixin):
    # use_enum_values stores plain text like "saved" instead of an enum object
    model_config = ConfigDict(use_enum_values=True)

    company: CleanName
    role: CleanName
    status: Status = Status.saved
    job_url: str | None = None
    date_applied: date | None = None
    notes: str | None = None


# What the client sends when changing an application.
# Every field is optional, so they can send only what changed.
# Type is "str" (not "str | None") so sending null for a required field is rejected.
class ApplicationUpdate(OptionalTextMixin):
    model_config = ConfigDict(use_enum_values=True)

    company: CleanName = Field(default=None)
    role: CleanName = Field(default=None)
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
