"""Data models for SAP Print Service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class PrintQueue:
    """Represents a print queue.

    Attributes:
        qname: Queue name (A-Z, a-z, 0-9, underscore, hyphen; max 32 chars).
        qdescription: Human-readable queue description.
        qformat: Print format identifier (e.g., acrobat6.xdc).
        qformat_descript: Format description (e.g., PDF).
        cleanup_prd: Document retention period in days (1-7).
        tech_user_name: Technical user assigned to the queue.
        location_id: Physical location identifier.
        location_id_type: Location type identifier.
        creator: Email of the queue creator.
    """

    qname: str
    qdescription: str = ""
    qformat: str = ""
    qformat_descript: str = ""
    cleanup_prd: int = 1
    tech_user_name: str = ""
    location_id: str = ""
    location_id_type: str = ""
    creator: str = ""

    def to_dict(self) -> dict:
        return {
            "qname": self.qname,
            "qdescription": self.qdescription,
            "qformat": self.qformat,
            "qformatDescript": self.qformat_descript,
            "cleanupPrd": self.cleanup_prd,
            "techUserName": self.tech_user_name,
            "locationId": self.location_id,
            "locationIdType": self.location_id_type,
            "creator": self.creator,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PrintQueue":
        return cls(
            qname=data.get("qname", ""),
            qdescription=data.get("qdescription", ""),
            qformat=data.get("qformat", ""),
            qformat_descript=data.get("qformatDescript", ""),
            cleanup_prd=data.get("cleanupPrd", 1),
            tech_user_name=data.get("techUserName", ""),
            location_id=data.get("locationId", ""),
            location_id_type=data.get("locationIdType", ""),
            creator=data.get("creator", ""),
        )


@dataclass
class PrintProfile:
    """Represents a print profile for a queue.

    Attributes:
        queue_name: Name of the associated print queue.
        profile_name: Profile identifier used when creating print tasks.
        profile_params: Reserved for future profile parameter details (currently empty).
        profile_status: Profile status (e.g., OK).
    """

    queue_name: str
    profile_name: str
    profile_params: Optional[str] = None
    profile_status: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "PrintProfile":
        return cls(
            queue_name=data.get("queueName", ""),
            profile_name=data.get("profileName", ""),
            profile_params=data.get("profileParams"),
            profile_status=data.get("profileStatus", ""),
        )


@dataclass
class PrintContent:
    """A single document included in a print task.

    Attributes:
        object_key: Document ID returned by upload_document().
        document_name: Display name for the document. Attachments must include
            the file extension (e.g., attachment.pdf).
    """

    object_key: str
    document_name: str

    def to_dict(self) -> dict:
        return {
            "objectKey": self.object_key,
            "documentName": self.document_name,
        }


@dataclass
class PrintTaskMetadata:
    """Optional metadata to attach to a print task.

    Attributes:
        version: Metadata schema version (required when metadata is provided).
        business_user: Business user identifier.
        object_node_type: Object node type identifier.
    """

    version: float
    business_user: str = ""
    object_node_type: str = ""

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "business_metadata": {
                "business_user": self.business_user,
                "object_node_type": self.object_node_type,
            },
        }


@dataclass
class PrintTask:
    """Describes a print task to be sent to a queue.

    The first item in print_contents whose object_key matches item_id is treated
    as the main document; all others are attachments.

    Attributes:
        item_id: The object_key of the main document (must match one entry in print_contents).
        qname: Target print queue name.
        print_contents: List of documents (main + attachments).
        number_of_copies: Number of copies to print.
        username: Name of the user initiating the print.
        profile_name: Optional profile name from get_print_profiles().
        metadata: Optional structured metadata.
    """

    item_id: str
    qname: str
    print_contents: list[PrintContent]
    number_of_copies: int = 1
    username: str = ""
    profile_name: Optional[str] = None
    metadata: Optional[PrintTaskMetadata] = None

    def to_body(self) -> dict:
        body: dict = {
            "numberOfCopies": self.number_of_copies,
            "username": self.username,
            "qname": self.qname,
            "printContents": [c.to_dict() for c in self.print_contents],
        }
        if self.profile_name is not None:
            body["profileName"] = self.profile_name
        if self.metadata is not None:
            body["metadata"] = self.metadata.to_dict()
        return body
