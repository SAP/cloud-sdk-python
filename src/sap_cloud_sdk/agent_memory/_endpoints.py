"""Agent Memory API endpoint path constants.

All endpoint paths are centralised here so that migrating to a new API version
requires changes in only this one file.

Current API version: v1
  - Memories CRUD + search: /v1/memories
  - Messages CRUD:          /v1/messages
  - Admin (retention):      /v1/admin/retentionConfig
"""

from __future__ import annotations

# ── Base path ──────────────────────────────────────────────────────────────────

BASE_PATH = "/v1"

# ── Memory endpoints ──────────────────────────────────────────────────────────

MEMORIES = f"{BASE_PATH}/memories"
# POST   MEMORIES                → create memory
# GET    MEMORIES                → list memories (with OData $filter / $top / $skip)
# GET    MEMORIES({id})          → get memory
# PATCH  MEMORIES({id})          → update memory
# DELETE MEMORIES({id})          → delete memory

MEMORY_SEARCH = f"{MEMORIES}/search"
# POST   MEMORY_SEARCH           → semantic similarity search

# ── Message endpoints ─────────────────────────────────────────────────────────

MESSAGES = f"{BASE_PATH}/messages"
# POST   MESSAGES                → create message
# GET    MESSAGES                → list messages (with OData $filter / $top / $skip)
# GET    MESSAGES({id})          → get message
# DELETE MESSAGES({id})          → delete message (not updatable)

# ── Admin endpoints ───────────────────────────────────────────────────────────

ADMIN_BASE_PATH = "/v1/admin"

RETENTION_CONFIG = f"{ADMIN_BASE_PATH}/retentionConfig"
# GET    RETENTION_CONFIG        → get singleton retention config
# PATCH  RETENTION_CONFIG        → update retention policy
