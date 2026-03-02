# Contributing

## Code of Conduct

All members of the project community must abide by the [Contributor Covenant, version 2.1](CODE_OF_CONDUCT.md).
Only by respecting each other can we develop a productive, collaborative community.
Instances of abusive, harassing, or otherwise unacceptable behavior may be reported by contacting [a project maintainer](mailto:).

## Engaging in Our Project

We use GitHub to manage reviews of pull requests.

* If you are a new contributor, see: [Steps to Contribute](#steps-to-contribute)

* Before implementing your change, create an issue that describes the problem you would like to solve or the code that should be enhanced. Please note that you are willing to work on that issue.

* The team will review the issue and decide whether it should be implemented as a pull request. In that case, they will assign the issue to you. If the team decides against picking up the issue, the team will post a comment with an explanation.

## Contributing with AI-generated code

As artificial intelligence evolves, AI-generated code is becoming valuable for many software projects, including open-source initiatives. While we recognize the potential benefits of incorporating AI-generated content into our open-source projects there are certain requirements that need to be reflected and adhered to when making contributions.

Please see our [guideline for AI-generated code contributions to SAP Open Source Software Projects](https://github.com/SAP/.github/blob/main/CONTRIBUTING_USING_GENAI.md) for these requirements.

## Steps to Contribute

Should you wish to work on an issue, please claim it first by commenting on the GitHub issue that you want to work on. This is to prevent duplicated efforts from other contributors on the same issue.

When your contribution is ready, please open a [pull request](https://github.com/SAP/cloud-sdk-python/compare).

If you have questions about one of the issues, please comment on them, and one of the maintainers will clarify.

## Contributing Code or Documentation

You are welcome to contribute code in order to fix a bug or to implement a new feature that is logged as an issue.

The following rule governs code contributions:

* Contributions must be licensed under the [Apache 2.0 License](./LICENSE)
* Due to legal reasons, contributors will be asked to accept a Developer Certificate of Origin (DCO) when they create the first pull request to this project. This happens in an automated fashion during the submission process. SAP uses [the standard DCO text of the Linux Foundation](https://developercertificate.org/).

## Issues and Planning

We use GitHub issues to track bugs, feature requests, and questions. When creating an issue, please use the appropriate template:

### Issue Types

1. **Bug Report** - For reporting issues with released features
   - Use the [Bug Report template](https://github.com/SAP/cloud-sdk-python/issues/new?template=bug-report.yml)
   - Provide version information, reproduction steps, and expected behavior
   
2. **Feature Request** - For proposing new features or enhancements
   - Use the [Feature Request template](https://github.com/SAP/cloud-sdk-python/issues/new?template=feature-request.yml)
   - Describe the problem, proposed solution, and impact
   
3. **Question** - For asking questions about the SDK
   - Use the [Question template](https://github.com/SAP/cloud-sdk-python/issues/new?template=question.yml)
   - Provide clear and concise questions

Please provide as much context as possible when you open an issue. The information you provide must be comprehensive enough to understand and address the issue effectively.

## Contributing Bug Fixes and Features

For contributing bug fixes or implementing approved features:

### 1. Check existing code and guidelines

Before starting your contribution:
- **Examine existing modules** in the `src/cloud_sdk_python/` directory (e.g., `auditlog`, `objectstore`, `destination`) to understand implementation patterns
- **Read [Code Guidelines](./GUIDELINES.md)** to understand our development standards and conventions
- **Review existing user guides** to understand the expected documentation format and API patterns

### 2. Create or claim an issue

1. Go to our repository's [GitHub Issues page](https://github.com/SAP/cloud-sdk-python/issues)
2. For bugs: Create a [Bug Report](https://github.com/SAP/cloud-sdk-python/issues/new?template=bug-report.yml)
3. For new features: Create a [Feature Request](https://github.com/SAP/cloud-sdk-python/issues/new?template=feature-request.yml)
4. **Claim the issue** by commenting that you want to work on it
5. Wait for maintainer approval and assignment

### 3. Review and approval process

The team will review your issue and:
- **Assign the issue** to you if approved
- **Add appropriate labels** (e.g., `bug`, `feature request`, `in review`)
- **Request clarifications** if needed
- **Provide feedback** within a reasonable timeframe
- **Approve or provide guidance** on the implementation approach

### 4. Fork and implement

Once your proposal receives the `approved` label, you can begin implementation:

**Getting Started:**
1. **Fork the repository** to your GitHub account
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/cloud-sdk-python.git
   cd cloud-sdk-python
   ```
3. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-capability-name
   ```

**Implementation Requirements:**

Follow our [Code Guidelines](./GUIDELINES.md) when implementing your changes. For bug fixes:
- Identify the root cause of the issue
- Implement the fix with minimal changes
- Add or update tests to prevent regression
- Update documentation if behavior changes

For new features or capabilities:
- Follow existing patterns in similar modules (e.g., `auditlog`, `objectstore`, `destination`)
- **Module Structure**: If creating a new module, use the standard Python package structure:
  ```
  src/cloud_sdk_python/[module-name]/
  ├── __init__.py
  ├── client.py
  ├── config.py
  ├── exceptions.py
  ├── models.py
  ├── py.typed
  └── user-guide.md
  ```
- **Core Components**: Implement client, configuration, validators, models, and exceptions as needed
- **Testing**: Write comprehensive unit tests and BDD integration tests (see `tests/auditlog/` for examples):
  ```
  tests/[module-name]/
  ├── __init__.py
  ├── unit/
  │   ├── test_client.py
  │   ├── test_config.py
  │   └── ...
  └── integration/
      ├── conftest.py
      ├── [module-name].feature
      └── test_[module-name]_bdd.py
  ```
- **Documentation**: Include a `user-guide.md` in your module's directory with:
  - Overview and quick start guide
  - Configuration examples
  - API usage examples
  - Common scenarios and troubleshooting
- **Type Hints**: Add complete type annotations and include a `py.typed` marker file

**Opening a Pull Request:**

1. **Commit your changes** with clear, descriptive messages following [Conventional Commits](https://www.conventionalcommits.org/)
2. **Push your branch** to your fork:
   ```bash
   git push origin feature/your-capability-name
   ```
3. **Open a Pull Request** against the `main` branch
4. **Link the PR to the original issue** (use "Closes #issue-number" in the PR description)
5. **Mark the PR as "Ready for Review"**

### 5. Code review and finalization

Our team will review your implementation for:
- **Code quality**: Adherence to guidelines and Python best practices
- **Test coverage**: Comprehensive unit and integration tests
- **Documentation**: Complete user guide with examples
- **API consistency**: Alignment with existing SDK patterns

After approval:
- **PR is merged** into the main branch
- **Release planning**: We'll coordinate next steps for version release and user documentation updates

## Ensure Compatibility

The SDK has to support a wide range of technologies and Python versions. Therefore, please adhere to the following guidelines:

- Ensure compatibility with Python 3.11 and above (as specified in `pyproject.toml`)
- Follow PEP 8 style guidelines
- Use type hints for all public APIs
- Ensure thread-safety where applicable

## Ensure Consistent Technologies/Dependencies

Avoid creating a "zoo of technologies" which tends to introduce more technical debt. This should not mean stagnation, but every change must be based on a factual argument of benefits over the existing technology in question.
In particular:

- Only introduce new libraries or frameworks for good reasons
- Ideally, investigate upfront if there are known vulnerabilities to any new dependencies you plan to introduce
- Keep dependencies minimal and well-justified

## Consult Documentation

Please consult our [documentation](../docs) to understand the project structure and conventions.

## Current Maintainers

- TODO: to be defined