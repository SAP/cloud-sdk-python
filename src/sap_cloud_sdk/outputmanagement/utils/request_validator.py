"""Request validation utilities.

This module provides comprehensive validation for Output Management requests including:
- CloudEvents specification compliance
- Business document validation
- Output management configuration validation
- Channel-specific validation

Author: SAP SE
Version: 1.0.0
Since: 1.0.0
"""

from typing import Optional, List
from ..models.output_request import OutputRequest
from ..models.email_configuration import EmailConfiguration
from ..models.direct_share_configuration import DirectShareConfiguration
from ..constants import Channel


class RequestValidator:
    """
    Validator utility class for Output Management requests.

    This class provides comprehensive validation for OutputRequest objects including:
    - CloudEvents specification compliance
    - Business document validation
    - Output management configuration validation
    - Channel-specific validation (delegates to specific validators)
    """

    def __init__(self):
        """Private constructor to prevent instantiation."""
        raise TypeError("This is a utility class and cannot be instantiated")

    @staticmethod
    def validate(output_request: OutputRequest) -> Optional[str]:
        """
        Validates an OutputRequest according to CloudEvents specification and business requirements.

        This method performs comprehensive validation including:
        - CloudEvents specification compliance (source, id, type format)
        - Required business document information
        - Output management metadata validation
        - Channel configuration validation (delegates to channel-specific validators)

        Args:
            output_request: The request to validate

        Returns:
            Optional error message if validation fails, None if valid
        """
        # CloudEvents spec: validate source
        source = output_request.source
        if not source or not source.strip():
            return "'source' cannot be null or empty"

        # CloudEvents spec: source format should be /region/application/tenant (3 parts separated by /)
        source_parts = [part for part in source.split("/") if part]
        if len(source_parts) != 3:
            return "'source' does not conform to cloud event spec. Expected format: /region/application/tenant"

        # CloudEvents spec: validate id
        if not output_request.id or not output_request.id.strip():
            return "'id' cannot be null or empty"

        # CloudEvents spec: validate type
        event_type = output_request.type
        if not event_type or not event_type.strip():
            return "'type' cannot be null or empty"

        # CloudEvents spec: type format should have at least 4 parts separated by dots
        # Example: sap.nexus.px.purchaseorder.PurchaseOrder.Created.v1
        type_parts = event_type.split(".")
        if len(type_parts) < 4:
            return "'type' does not conform to cloud event spec. Expected format: domain.application.module.event"

        # Validate data payload
        data = output_request.data
        if data is None:
            return "Request data cannot be null"

        # Validate business document
        business_document = data.business_document
        if business_document is None or not business_document:
            return "Business document cannot be null"

        # Validate output management info
        output_management = data.output_management
        if output_management is None:
            return "Output management related parameters not specified"

        # Validate business document ID
        business_document_id = output_management.business_document_id
        if not business_document_id or not business_document_id.strip():
            return "Business document id cannot be null or empty"

        # Validate business document type. It is required unless DIRECT_SHARE channel is used
        business_document_type = output_management.business_document_type
        channels = output_management.channels

        if (
            (not business_document_type or not business_document_type.strip())
            and channels
            and len(channels) > 0
            and Channel.DIRECT_SHARE not in channels
        ):
            return "Business document type cannot be null or empty"

        # Validate channels if present
        if channels is not None and len(channels) > 0:
            channel_error = RequestValidator._validate_channels(channels)
            if channel_error is not None:
                return channel_error

            # Validate direct share configuration if DIRECT_SHARE channel is present
            has_direct_share = Channel.DIRECT_SHARE in channels

            if has_direct_share:
                direct_share_config = output_management.direct_share_configuration
                direct_share_error = DirectShareConfigValidator.validate(
                    direct_share_config
                )
                if direct_share_error is not None:
                    return direct_share_error

            # Validate internal email configuration if EMAIL or INTERNAL_EMAIL channel is present
            has_email = Channel.EMAIL in channels or Channel.INTERNAL_EMAIL in channels

            if has_email:
                email_config = output_management.email_configuration
                email_error = InternalEmailConfigValidator.validate(email_config)
                if email_error is not None:
                    return email_error

        return None

    @staticmethod
    def _validate_channels(channels: List[Channel]) -> Optional[str]:
        """
        Validates channel configuration.

        Args:
            channels: The list of channels to validate

        Returns:
            Optional error message if validation fails, None if valid
        """
        if channels is None or len(channels) == 0:
            return "At least one channel must be specified"

        for channel in channels:
            if channel is None:
                return "Channel cannot be null"

        return None

    @staticmethod
    def validate_email_parameters(
        notification_template_key: str,
        to: List[str],
        business_document: dict,
        template_language: str,
        cc: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Validates email-specific parameters for EmailClient.

        Args:
            notification_template_key: ANS template identifier
            to: List of recipient email addresses
            business_document: The business document dictionary
            template_language: ISO language code for email template
            cc: Optional list of CC email addresses

        Returns:
            Optional error message if validation fails, None if valid
        """
        # Validate notification_template_key
        if not notification_template_key or not notification_template_key.strip():
            return "notification_template_key cannot be null or empty"

        # Validate recipients list
        if not to or len(to) == 0:
            return "At least one recipient is required in email configuration"

        # Validate email addresses in recipients list
        for recipient in to:
            if not recipient or not recipient.strip():
                return "Email recipient cannot be null or empty"

        # Validate CC recipients if present
        if cc:
            for recipient in cc:
                if not recipient or not recipient.strip():
                    return "Email CC recipient cannot be null or empty"

        # Validate business_document
        if not business_document or len(business_document) == 0:
            return "Business document cannot be null"

        # Validate template_language
        if not template_language or not template_language.strip():
            return "email_template_language cannot be null or empty"

        return None


class DirectShareConfigValidator:
    """
    Validator for Direct Share configuration.

    This class provides validation for DirectShareConfiguration objects.
    """

    def __init__(self):
        """Private constructor to prevent instantiation."""
        raise TypeError("This is a utility class and cannot be instantiated")

    @staticmethod
    def validate(config: Optional[DirectShareConfiguration]) -> Optional[str]:
        """
        Validates a DirectShareConfiguration.

        Args:
            config: The configuration to validate

        Returns:
            Optional error message if validation fails, None if valid
        """
        if config is None:
            return "Direct share configuration cannot be null when DIRECT_SHARE channel is specified"

        # Add additional direct share specific validations here as needed
        # For now, the basic structure validation is done by Pydantic models

        return None


class InternalEmailConfigValidator:
    """
    Validator for Internal Email configuration.

    This class provides validation for EmailConfiguration objects.
    """

    def __init__(self):
        """Private constructor to prevent instantiation."""
        raise TypeError("This is a utility class and cannot be instantiated")

    @staticmethod
    def validate(config: Optional[EmailConfiguration]) -> Optional[str]:
        """
        Validates an EmailConfiguration.

        Args:
            config: The configuration to validate

        Returns:
            Optional error message if validation fails, None if valid
        """
        if config is None:
            return "Email configuration cannot be null when EMAIL channel is specified"

        # Validate recipients
        if not config.to or len(config.to) == 0:
            return "At least one recipient is required in email configuration"

        # Validate email addresses in recipients list
        for recipient in config.to:
            if not recipient or not recipient.strip():
                return "Email recipient cannot be null or empty"

        # Validate CC recipients if present
        if config.cc:
            for recipient in config.cc:
                if not recipient or not recipient.strip():
                    return "Email CC recipient cannot be null or empty"

        # Validate BCC recipients if present
        if config.bcc:
            for recipient in config.bcc:
                if not recipient or not recipient.strip():
                    return "Email BCC recipient cannot be null or empty"

        return None
