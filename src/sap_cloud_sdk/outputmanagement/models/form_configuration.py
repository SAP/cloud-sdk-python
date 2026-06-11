"""Form configuration model."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class FormConfiguration(BaseModel):
    """Form channel configuration.

    Attributes:
        form_id: Form identifier
        form_data: Optional form data
        callback_url: Optional callback URL for form submission
    """

    form_id: str = Field(..., min_length=1, description="Form identifier")
    form_data: Optional[Dict[str, Any]] = Field(None, description="Form data")
    callback_url: Optional[str] = Field(
        None, description="Callback URL for form submission"
    )

    class Config:
        """Pydantic configuration."""

        str_strip_whitespace = True
