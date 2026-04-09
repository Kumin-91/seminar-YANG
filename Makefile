# 기본 변수
YANGLINT = yanglint
PYTHON = python3
ANSIBLE = ansible-playbook
YANG = 01-schema
JSON = 02-inventory
DISPATCHER = 04-provisioning/dispatcher.sh
REMOVER = 04-provisioning/purge_march.sh
RESOLVER = 05-ansible-bootstrap/inventory/resolver.py
ANSIBLE_CFG = 05-ansible-bootstrap/ansible.cfg
SITE_YAML = 05-ansible-bootstrap/site.yml


.DEFAULT_GOAL := help
.PHONY: help all keygen lint provision bootstrap aws-purge

# 도움말 출력
help:
	@echo "Usage: make [target]"
	@echo "Targets:"
	@echo "  help            - 이 도움말 메시지를 출력합니다."
	@echo "  all             - 모든 과정을 실행합니다."
	@echo "  keygen          - [Phase 0] SSH 키 페어를 생성합니다."
	@echo "  lint            - [Phase 2] YANG 모델 검사 및 JSON 검증을 실행합니다."
	@echo "  lint-test       - [Phase 2] 에러가 있는 JSON 파일로 YANG 모델 검사를 테스트합니다."
	@echo "  provision       - [Phase 4] AWS/On-premises 인프라 프로비저닝을 실행합니다."
	@echo "  bootstrap       - [Phase 5] Ansible playbook을 실행하여 bootstrap을 수행합니다."
	@echo "  aws-purge       - [Phase 4] AWS infrastructure를 제거합니다."

# 모든 과정 실행
all:
	@echo "모든 과정을 실행합니다..."
	$(MAKE) keygen
	@sleep 5
	$(MAKE) lint
	@sleep 5
	$(MAKE) provision
	@sleep 5
	$(MAKE) bootstrap
	@sleep 5
	@echo "모든 과정이 완료되었습니다."

# SSH 키 페어 생성 (이미 존재하면 건너뜀)
keygen:
	@if [ -f ./00-key/hybrid-cloud ]; then \
		echo "✅ ./00-key/hybrid-cloud 키가 이미 존재합니다. 생성을 건너뜁니다."; \
	else \
		echo "🚀 SSH 키 페어를 새로 생성합니다..."; \
		mkdir -p ./00-key; \
		ssh-keygen -t ed25519 -f ./00-key/hybrid-cloud -N ""; \
	fi
	@echo "🔑 현재 사용 중인 공개 키 (./00-key/hybrid-cloud.pub):"
	@cat ./00-key/hybrid-cloud.pub

# YANG 모델 검사 및 JSON 검증
lint:
	@yanglint -f tree 01-schema/nodes/hybrid-cloud.yang
	@for f in 02-inventory/nodes/*.json; do \
		yanglint -p 01-schema/nodes 01-schema/nodes/hybrid-cloud.yang "$$f" && \
		echo "✅ YANG Lint Pass: $$f" || { echo "❌ YANG Lint Fail: $$f" && exit 1; }; \
	done
	@yanglint -f tree 01-schema/providers/aws-provider.yang
	@for f in 02-inventory/providers/*.json; do \
		yanglint -p 01-schema/providers 01-schema/providers/aws-provider.yang "$$f" && \
		echo "✅ YANG Lint Pass: $$f" || { echo "❌ YANG Lint Fail: $$f" && exit 1; }; \
	done

# 에러가 있는 JSON 파일로 YANG 모델 검사 테스트
lint-test:
	@for f in 02-inventory/error/*.json; do \
		yanglint -p 01-schema/nodes 01-schema/nodes/hybrid-cloud.yang "$$f" && \
		echo "✅ YANG Lint Pass: $$f" || echo "❌ YANG Lint Fail: $$f"; \
	done

# 인프라 프로비저닝
provision:
	@echo "[Phase 4] AWS/On-premises 인프라 프로비저닝을 시작합니다..."
	@chmod +x $(DISPATCHER)
	@bash $(DISPATCHER)

# Ansible 부트스트랩 실행
bootstrap:
	@echo "[Phase 5] Ansible 부트스트랩을 실행합니다..."
	@ANSIBLE_CONFIG=$(ANSIBLE_CFG) $(ANSIBLE) -i $(RESOLVER) $(SITE_YAML)

# AWS 인프라 제거
aws-purge:
	@echo "[Phase 4] AWS 인프라를 제거합니다..."
	@chmod +x $(REMOVER)
	@bash $(REMOVER)