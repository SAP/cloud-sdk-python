"""Direct share configuration model."""

from typing import Optional, List
from pydantic import BaseModel, Field


class DirectShareConfiguration(BaseModel):
    """Direct share channel configuration.

    Attributes:
        user_ids: List of user IDs to share with
        group_ids: Optional list of group IDs to share with
        message: Optional message to include
        expiration_days: Optional number of days until expiration
    """

    user_ids: List[str] = Field(..., min_length=1, description="User IDs to share with")
    group_ids: Optional[List[str]] = Field(None, description="Group IDs to share with")
    message: Optional[str] = Field(None, description="Message to include")
    expiration_days: Optional[int] = Field(
        None, ge=1, description="Days until expiration"
    )

    class Config:
        """Pydantic configuration."""

        str_strip_whitespace = True
