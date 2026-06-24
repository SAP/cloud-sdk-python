"""Canonical test data for consent integration tests."""

from __future__ import annotations

import secrets

# 6-char hex, unique per pytest session
_RUN_SUFFIX = secrets.token_hex(3)  

# Domain / lifecycle codes

LIFECYCLE_INITIAL  = "1"
LIFECYCLE_ACTIVE   = "2"
LIFECYCLE_INACTIVE = "3"

CONSENT_MODEL_OPT_IN  = "1"
CONSENT_MODEL_OPT_OUT = "2"

THIRD_PARTY_FUNC_RECIPIENT = "1"
THIRD_PARTY_FUNC_SOURCE    = "2"

PURPOSE_TEXT_TYPE_EXPLANATORY = "01"
PURPOSE_TEXT_TYPE_DESCRIPTION = "02"

# Integration test scenario — AB Corp / marketing-lead-india

CONTROLLER_NAME = f"abcorp-india_{_RUN_SUFFIX}"
CONTROLLER_DESC = "AB Corp India Pvt Ltd"

APP_NAME = f"order-mgmt-{_RUN_SUFFIX}"
APP_DESC = "Order Management"

JURISDICTION_CODE = "IND"
JURISDICTION_TEXT = "India"
JURISDICTION_LANG = "en"

DATA_SUBJECT_TYPE = f"order-partner_{_RUN_SUFFIX}"

THIRD_PARTY_NAME = f"absuppliers-india_{_RUN_SUFFIX}"
THIRD_PARTY_DESC = "AB Suppliers India Pvt Ltd"

PURPOSE_NAME             = f"marketing-lead-purpose_{_RUN_SUFFIX}"
PURPOSE_TEXT_LANG        = "en"
PURPOSE_EXPLANATORY_TEXT = (
    "AB Corp processes your personal data for marketing purposes. "
    "You can withdraw your consent at any time."
)

TEMPLATE_NAME            = f"marketing-lead-india_{_RUN_SUFFIX}"
TEMPLATE_VALIDITY_PERIOD = 100

TEMPLATE_THIRD_PARTY_FUNCS = (
    THIRD_PARTY_FUNC_RECIPIENT,
    THIRD_PARTY_FUNC_SOURCE,
)

DATA_SUBJECT_ID = "I12345"
CONSENT_LANG    = "en"
