#!/usr/bin/env python3
"""Test script to list available destinations."""

import os
from pathlib import Path
from dotenv import load_dotenv
from sap_cloud_sdk.destination import create_client
from sap_cloud_sdk.destination.config import DestinationConfig

# Load environment
env_file = Path(__file__).parent / ".env_integration_tests"
if env_file.exists():
    load_dotenv(env_file)
    print(f"Loaded {env_file}")

# Print what we loaded
print(
    f"\nClient ID: {os.getenv('CLOUD_SDK_CFG_DESTINATION_DEFAULT_CLIENTID', 'NOT SET')[:50]}..."
)
print(f"URL: {os.getenv('CLOUD_SDK_CFG_DESTINATION_DEFAULT_URL', 'NOT SET')}")
print(f"URI: {os.getenv('CLOUD_SDK_CFG_DESTINATION_DEFAULT_URI', 'NOT SET')}")

try:
    # Create destination client explicitly with config
    config = DestinationConfig(
        url=os.getenv("CLOUD_SDK_CFG_DESTINATION_DEFAULT_URI"),
        token_url=os.getenv("CLOUD_SDK_CFG_DESTINATION_DEFAULT_URL"),
        client_id=os.getenv("CLOUD_SDK_CFG_DESTINATION_DEFAULT_CLIENTID"),
        client_secret=os.getenv("CLOUD_SDK_CFG_DESTINATION_DEFAULT_CLIENTSECRET"),
        identityzone=os.getenv("CLOUD_SDK_CFG_DESTINATION_DEFAULT_IDENTITYZONE"),
    )

    client = create_client(config=config)
    print("\nDestination client created successfully with explicit config!")

    # Try to list all destinations
    print("\nAttempting to retrieve destination 'om-destination-eu10'...")

    # Try instance level first
    try:
        dest = client.get_instance_destination(name="om-destination-eu10")
        if dest:
            print("Found at INSTANCE level!")
            if hasattr(dest, "url"):
                print(f"URL: {dest.url}")
        else:
            print("Not found at INSTANCE level")
    except Exception as e:
        print(f"INSTANCE level error: {e}")

    # Try subaccount level with PROVIDER_ONLY
    from sap_cloud_sdk.destination import AccessStrategy

    try:
        dest = client.get_subaccount_destination(
            name="om-destination-eu10", access_strategy=AccessStrategy.PROVIDER_ONLY
        )
        if dest:
            print("Found at SUBACCOUNT level (PROVIDER_ONLY)!")
            if hasattr(dest, "url"):
                print(f"   URL: {dest.url}")
        else:
            print("Not found at SUBACCOUNT level (PROVIDER_ONLY)")
    except Exception as e:
        print(f"SUBACCOUNT level (PROVIDER_ONLY) error: {e}")

    print("\nIf not found:")
    print("   1. Check BTP Cockpit → Connectivity → Destinations")
    print("   2. Verify destination name is exactly 'om-destination-eu10'")
    print("   3. Check if it's at subaccount or instance level")

except Exception as e:
    print(f"\nFailed to create destination client: {e}")
    import traceback

    traceback.print_exc()
    print("\nCheck your credentials in .env_integration_tests")
