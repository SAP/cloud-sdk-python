Feature: Multi-provider object storage
  As a developer using the SDK
  I want one object storage interface across S3, Azure, and GCS
  So that the portable contract behaves identically on every backend

  Scenario Outline: Object lifecycle from bytes
    Given a live "<provider>" object storage client
    When I upload "hello world" as bytes to "lifecycle.txt"
    Then the object "lifecycle.txt" exists
    And downloading "lifecycle.txt" returns "hello world"
    And the metadata size of "lifecycle.txt" is 11
    And listing the test prefix includes "lifecycle.txt"
    When I delete "lifecycle.txt"
    Then the object "lifecycle.txt" does not exist

    Examples:
      | provider |
      | s3       |
      | azure    |
      | gcs      |

  Scenario Outline: Upload from a stream and from a file
    Given a live "<provider>" object storage client
    When I upload a 5-byte stream to "stream.bin"
    And I upload a temporary file to "file.txt"
    Then the object "stream.bin" exists
    And the object "file.txt" exists

    Examples:
      | provider |
      | s3       |
      | azure    |
      | gcs      |

  Scenario Outline: Missing object reports not found
    Given a live "<provider>" object storage client
    When I download the missing object "absent.txt"
    Then the operation fails with "ObjectNotFoundError"

    Examples:
      | provider |
      | s3       |
      | azure    |
      | gcs      |

  Scenario Outline: Deleting a missing object is idempotent
    Given a live "<provider>" object storage client
    When I delete "never-existed.txt"
    Then no error is raised

    Examples:
      | provider |
      | s3       |
      | azure    |
      | gcs      |

  Scenario Outline: Uploading a missing local file fails
    Given a live "<provider>" object storage client
    When I upload the missing file "/tmp/does-not-exist-xyz.txt" to "x.txt"
    Then the operation fails with "ObjectOperationError"

    Examples:
      | provider |
      | s3       |
      | azure    |
      | gcs      |

  Scenario Outline: Invalid object name is rejected before any I/O
    Given a live "<provider>" object storage client
    When I download an object with an empty name
    Then the operation fails with "ValueError"

    Examples:
      | provider |
      | s3       |
      | azure    |
      | gcs      |

  Scenario Outline: Operations against an unreachable endpoint fail cleanly
    Given an unreachable "<provider>" object storage client
    When I upload "data" as bytes to "unreachable.txt"
    Then the operation fails with "ObjectOperationError"
    When I upload a 5-byte stream to "unreachable-stream.bin"
    Then the operation fails with "ObjectOperationError"
    When I upload a temporary file to "unreachable-file.txt"
    Then the operation fails with "ObjectOperationError"
    When I download the missing object "unreachable.txt"
    Then the operation fails with "ObjectOperationError"
    When I fetch metadata for "unreachable.txt"
    Then the operation fails with "ObjectOperationError"
    When I check whether "unreachable.txt" exists
    Then the operation fails with "ObjectOperationError"
    When I delete "unreachable.txt"
    Then the operation fails with "ObjectOperationError"
    When I list the test prefix
    Then the operation fails with "ListObjectsError"

    Examples:
      | provider |
      | s3       |
      | azure    |
