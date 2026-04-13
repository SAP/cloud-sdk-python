# Proto code generation for SAP Cloud SDK for Python
# Requires: buf CLI (https://buf.build/docs/installation)

AUDITLOG_NG_DIR := src/sap_cloud_sdk/core/auditlog_ng
GEN_DIR         := $(AUDITLOG_NG_DIR)/gen
BUF_DIR         := src/buf

.PHONY: proto

proto:
	cd $(AUDITLOG_NG_DIR) && buf dep update && buf generate --include-imports
	find $(GEN_DIR) -type d -exec touch {}/__init__.py \;
	rm -rf $(BUF_DIR)
	mv $(GEN_DIR)/buf $(BUF_DIR)
	rm -rf $(GEN_DIR)/buf
