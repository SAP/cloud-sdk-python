"""BDD step definitions for consent_creation.feature.

Covers the 12-step consent creation flow across 4 scenarios:
  Scenario 1 — Set up configuration entities (controller, app, jurisdiction, DST, third party)
  Scenario 2 — Set up consent purpose (create, add text, activate)
  Scenario 3 — Set up consent template (create, assign third party x2, activate)
  Scenario 4 — Create consent record from template

State flows through the module-scoped ConsentScenarioContext fixture defined in conftest.py.
"""

from __future__ import annotations

import pytest
from pytest_bdd import scenarios, given, when, then

from sap_cloud_sdk.core.dpi_ng.consent import ConsentClient, CreateConsentRequest

from tests.core.integration.dpi_ng.consent import data_bdd as data
from tests.core.integration.dpi_ng.consent.conftest import ConsentScenarioContext

pytestmark = pytest.mark.integration

scenarios("consent_creation.feature")


# ---------------------------------------------------------------------------
# Background / shared
# ---------------------------------------------------------------------------


@given("a configured consent client")
def configured_consent_client(
    context: ConsentScenarioContext, live_client: ConsentClient
) -> None:
    context.client = live_client
    print("[step 0] consent client configured")


# ---------------------------------------------------------------------------
# Scenario 1 — Configuration entities
# ---------------------------------------------------------------------------


@when("I create a controller")
def create_controller(
    context: ConsentScenarioContext, live_client: ConsentClient
) -> None:
    controller = live_client.configuration.create_controller(
        {
            "controller_name": data.CONTROLLER_NAME,
            "description": data.CONTROLLER_DESC,
        }
    )
    context.controller_id = controller.controller_id
    print(
        f"[step 1] controller created: id={controller.controller_id} name={controller.controller_name}"
    )


@then("the controller should have a valid id")
def controller_has_valid_id(context: ConsentScenarioContext) -> None:
    assert context.controller_id, "controller_id must be set after creation"


@when("I create an application")
def create_application(
    context: ConsentScenarioContext, live_client: ConsentClient
) -> None:
    app = live_client.configuration.create_application(
        {
            "application_name": data.APP_NAME,
            "description": data.APP_DESC,
        }
    )
    context.application_id = app.application_id
    print(
        f"[step 2] application created: id={app.application_id} name={app.application_name}"
    )


@then("the application should have a valid id")
def application_has_valid_id(context: ConsentScenarioContext) -> None:
    assert context.application_id, "application_id must be set after creation"


@when('I reuse or create a jurisdiction named "India"')
def reuse_or_create_jurisdiction(
    context: ConsentScenarioContext, live_client: ConsentClient
) -> None:
    existing = [
        j
        for j in live_client.configuration.list_jurisdictions()
        if j.jurisdiction_code == data.JURISDICTION_CODE
    ]
    if existing:
        jurisdiction = existing[0]
        print(
            f"[step 3a] jurisdiction reused: id={jurisdiction.jurisdiction_id} "
            f"code={jurisdiction.jurisdiction_code}"
        )
    else:
        jurisdiction = live_client.configuration.create_jurisdiction(
            {
                "jurisdiction_code": data.JURISDICTION_CODE,
            }
        )
        print(
            f"[step 3a] jurisdiction created: id={jurisdiction.jurisdiction_id} "
            f"code={jurisdiction.jurisdiction_code}"
        )

    context.jurisdiction_id = jurisdiction.jurisdiction_id

    try:
        j_text = live_client.configuration.create_jurisdiction_text(
            {
                "jurisdiction_id": jurisdiction.jurisdiction_id,
                "language_code": data.JURISDICTION_LANG,
                "description": data.JURISDICTION_TEXT,
            }
        )
        print(
            f"[step 3b] jurisdiction text added: lang={j_text.language_code} "
            f"text='{j_text.description}'"
        )
    except Exception as exc:
        print(
            f"[step 3b] jurisdiction text already present "
            f"(lang={data.JURISDICTION_LANG}) — {exc}"
        )


@then("the jurisdiction should have a valid id")
def jurisdiction_has_valid_id(context: ConsentScenarioContext) -> None:
    assert context.jurisdiction_id, "jurisdiction_id must be set"


@when("I create a data subject type")
def create_data_subject_type(
    context: ConsentScenarioContext, live_client: ConsentClient
) -> None:
    dst = live_client.configuration.create_data_subject_type(
        {
            "data_subject_type_name": data.DATA_SUBJECT_TYPE,
        }
    )
    context.data_subject_type_id = dst.data_subject_type_id
    print(
        f"[step 4] data subject type created: id={dst.data_subject_type_id} name={dst.data_subject_type_name}"
    )


@then("the data subject type should have a valid id")
def data_subject_type_has_valid_id(context: ConsentScenarioContext) -> None:
    assert context.data_subject_type_id, (
        "data_subject_type_id must be set after creation"
    )


@when("I create a third party")
def create_third_party(
    context: ConsentScenarioContext, live_client: ConsentClient
) -> None:
    tp = live_client.configuration.create_third_party(
        {
            "third_party_name": data.THIRD_PARTY_NAME,
            "formatted_description": data.THIRD_PARTY_DESC,
        }
    )
    context.third_party_id = tp.third_party_id
    print(
        f"[step 5] third party created: id={tp.third_party_id} name={tp.third_party_name}"
    )


@then("the third party should have a valid id")
def third_party_has_valid_id(context: ConsentScenarioContext) -> None:
    assert context.third_party_id, "third_party_id must be set after creation"


# ---------------------------------------------------------------------------
# Scenario 2 — Consent purpose
# ---------------------------------------------------------------------------


@when("I create a purpose")
def create_purpose(context: ConsentScenarioContext, live_client: ConsentClient) -> None:
    purpose = live_client.purposes.create_purpose(
        {
            "purpose_name": data.PURPOSE_NAME,
        }
    )
    context.purpose_id = purpose.purpose_id
    print(
        f"[step 6] purpose created: id={purpose.purpose_id} name={purpose.purpose_name}"
    )


@then("the purpose should have a valid id")
def purpose_has_valid_id(context: ConsentScenarioContext) -> None:
    assert context.purpose_id, "purpose_id must be set after creation"


@when("I add an English explanatory text to the purpose")
def add_purpose_text(
    context: ConsentScenarioContext, live_client: ConsentClient
) -> None:
    assert context.purpose_id, (
        "purpose_id must be set (scenario 2 depends on scenario 1 passing)"
    )
    p_text = live_client.purposes.create_purpose_text(
        {
            "purpose_id": context.purpose_id,
            "language_code": data.PURPOSE_TEXT_LANG,
            "type_code": data.PURPOSE_TEXT_TYPE_EXPLANATORY,
            "text": data.PURPOSE_EXPLANATORY_TEXT,
        }
    )
    context.result = p_text
    print(
        f"[step 7] purpose text added: purpose_id={p_text.purpose_id} "
        f"lang={p_text.language_code} type_code={p_text.type_code}"
    )


@then("the purpose text should be saved successfully")
def purpose_text_saved(context: ConsentScenarioContext) -> None:
    assert context.result is not None, "purpose text result must be set"
    assert context.result.purpose_id == context.purpose_id, (
        f"Expected purpose_id={context.purpose_id} but got {context.result.purpose_id}"
    )


@when("I activate the purpose")
def activate_purpose(
    context: ConsentScenarioContext, live_client: ConsentClient
) -> None:
    assert context.purpose_id, "purpose_id must be set before activation"
    activated = live_client.purposes.set_purpose_active(context.purpose_id)
    context.result = activated
    print(
        f"[step 8] purpose activated: id={activated.purpose_id} "
        f"status={activated.lifecycle_status_code}"
    )


@then('the purpose lifecycle status should be "active"')
def purpose_lifecycle_active(context: ConsentScenarioContext) -> None:
    assert context.result.lifecycle_status_code == data.LIFECYCLE_ACTIVE, (
        f"Expected lifecycle_status_code='{data.LIFECYCLE_ACTIVE}' (active) "
        f"but got '{context.result.lifecycle_status_code}'"
    )


# ---------------------------------------------------------------------------
# Scenario 3 — Consent template
# ---------------------------------------------------------------------------


@when("I create a consent template using the purpose, controller, and application")
def create_template(
    context: ConsentScenarioContext, live_client: ConsentClient
) -> None:
    assert context.purpose_id, "purpose_id required"
    assert context.controller_id, "controller_id required"
    assert context.application_id, "application_id required"
    template = live_client.templates.create_template(
        {
            "template_name": data.TEMPLATE_NAME,
            "jurisdiction_code": data.JURISDICTION_CODE,
            "consent_model_code": data.CONSENT_MODEL_OPT_IN,
            "purpose_id": context.purpose_id,
            "controller_id": context.controller_id,
            "application_id": context.application_id,
            "validity_period": data.TEMPLATE_VALIDITY_PERIOD,
        }
    )
    context.template_id = template.template_id
    print(
        f"[step 9] template created: id={template.template_id} "
        f"name={template.template_name} jurisdiction={template.jurisdiction_code}"
    )


@then("the template should have a valid id")
def template_has_valid_id(context: ConsentScenarioContext) -> None:
    assert context.template_id, "template_id must be set after creation"


@when('I assign the third party as a "RECIPIENT" to the template')
def assign_third_party_recipient(
    context: ConsentScenarioContext, live_client: ConsentClient
) -> None:
    assert context.template_id, "template_id required"
    assert context.third_party_id, "third_party_id required"
    tppd = live_client.templates.create_third_party_pers_data(
        {
            "template_id": context.template_id,
            "third_party_id": context.third_party_id,
            "third_party_function_code": data.THIRD_PARTY_FUNC_RECIPIENT,
        }
    )
    context.result = tppd
    print(
        f"[step 10a] third party RECIPIENT assigned: "
        f"third_party_id={tppd.third_party_id} functionCode={tppd.third_party_function_code}"
    )


@then("the third party recipient assignment should succeed")
def third_party_recipient_assigned(context: ConsentScenarioContext) -> None:
    assert context.result.template_id == context.template_id, (
        f"Expected template_id={context.template_id} but got {context.result.template_id}"
    )
    assert context.result.third_party_id == context.third_party_id, (
        f"Expected third_party_id={context.third_party_id} but got {context.result.third_party_id}"
    )


@when('I assign the third party as a "SOURCE" to the template')
def assign_third_party_source(
    context: ConsentScenarioContext, live_client: ConsentClient
) -> None:
    assert context.template_id, "template_id required"
    assert context.third_party_id, "third_party_id required"
    tppd = live_client.templates.create_third_party_pers_data(
        {
            "template_id": context.template_id,
            "third_party_id": context.third_party_id,
            "third_party_function_code": data.THIRD_PARTY_FUNC_SOURCE,
        }
    )
    context.result = tppd
    print(
        f"[step 10b] third party SOURCE assigned: "
        f"third_party_id={tppd.third_party_id} functionCode={tppd.third_party_function_code}"
    )


@then("the third party source assignment should succeed")
def third_party_source_assigned(context: ConsentScenarioContext) -> None:
    assert context.result.template_id == context.template_id, (
        f"Expected template_id={context.template_id} but got {context.result.template_id}"
    )
    assert context.result.third_party_id == context.third_party_id, (
        f"Expected third_party_id={context.third_party_id} but got {context.result.third_party_id}"
    )


@when("I activate the template")
def activate_template(
    context: ConsentScenarioContext, live_client: ConsentClient
) -> None:
    assert context.template_id, "template_id required before activation"
    activated = live_client.templates.set_template_active(context.template_id)
    context.result = activated
    print(
        f"[step 11] template activated: id={activated.template_id} "
        f"status={activated.lifecycle_status_code}"
    )


@then('the template lifecycle status should be "active"')
def template_lifecycle_active(context: ConsentScenarioContext) -> None:
    assert context.result.lifecycle_status_code == data.LIFECYCLE_ACTIVE, (
        f"Expected lifecycle_status_code='{data.LIFECYCLE_ACTIVE}' (active) "
        f"but got '{context.result.lifecycle_status_code}'"
    )


# ---------------------------------------------------------------------------
# Scenario 4 — Consent record
# ---------------------------------------------------------------------------


@when('I create a consent from the template for data subject "DS-IT-CREATION-001"')
def create_consent_record(
    context: ConsentScenarioContext, live_client: ConsentClient
) -> None:
    assert context.template_id, "template_id required — scenario 3 must pass first"
    request = CreateConsentRequest(
        data_subject_id=data.DATA_SUBJECT_ID,
        template_name=data.TEMPLATE_NAME,
        language_code=data.CONSENT_LANG,
        data_subject_type_name=data.DATA_SUBJECT_TYPE,
        jurisdiction_code=data.JURISDICTION_CODE,
    )
    consents = live_client.consents.create_consent_from_template(request)
    context.consent_ids = [c.consent_id for c in consents]
    print(
        f"[step 12] {len(consents)} consent record(s) returned: ids={context.consent_ids}"
    )


@then("at least one consent record should be returned")
def at_least_one_consent(context: ConsentScenarioContext) -> None:
    assert len(context.consent_ids) >= 1, (
        f"Expected at least one consent record but got {len(context.consent_ids)}"
    )
