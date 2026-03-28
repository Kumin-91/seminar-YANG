# 기본 변수
YANGLINT = yanglint
PYTHON = python3
ANSIBLE = ansible-playbook
YANG = 01-schema
JSON = 02-inventory
PROVISIONER = 04-provisioning/provisioner.py
REMOVER = 04-provisioning/provisioner_tf_remove.py
RESOLVER = 05-ansible-bootstrap/inventory/resolver.py
SITE_YAML = 05-ansible-bootstrap/site.yml


.DEFAULT_GOAL := help
.PHONY: help all lint provision bootstrap-test bootstrap destroy-aws clean

# 도움말 출력
help:
	@echo "Usage: make [target]"
	@echo "Targets:"
	@echo "  help            - 이 도움말 메시지를 출력합니다."
	@echo "  all             - 모든 과정을 실행합니다."
	@echo "  lint            - [Phase 2] YANG 모델 검사 및 JSON 검증을 실행합니다."
	@echo "  provision       - [Phase 4] AWS/On-premises 인프라 프로비저닝을 실행합니다."
	@echo "  bootstrap-test  - [Phase 5] Ansible connectivity를 테스트합니다."
	@echo "  bootstrap       - [Phase 5] Ansible playbook을 실행하여 bootstrap을 수행합니다."
	@echo "  destroy-aws     - [Phase 4] AWS infrastructure를 제거합니다."
	@echo "  clean           - [Phase 4] 생성된 파일 및 캐시를 정리합니다."

# 모든 과정 실행
all:
	@echo "모든 과정을 실행합니다..."
	$(MAKE) lint
	@sleep 5
	$(MAKE) provision
	@sleep 5
	$(MAKE) bootstrap-test
	@sleep 5
	$(MAKE) bootstrap
	@sleep 5
	@echo "모든 과정이 완료되었습니다."

# YANG 모델 검사 및 JSON 검증
lint:
	@echo "[Phase 2] YANG 모델 검사 및 JSON 검증을 실행합니다..."
	$(YANGLINT) -f tree $(YANG)/hybrid-cloud.yang
	@for f in $(JSON)/*.json; do \
		$(YANGLINT) -p $(YANG) -t data $(YANG)/hybrid-cloud.yang "$$f" > /dev/null 2>&1 && \
		echo "YANG Lint Pass: $$f" || \
		(echo "YANG Lint Fail: $$f" && exit 1); \
	done
# 인프라 프로비저닝
provision:
	@echo "[Phase 4] AWS/On-premises 인프라 프로비저닝을 시작합니다..."
	$(PYTHON) $(PROVISIONER)

# Ansible 부트스트랩 테스트
bootstrap-test:
	@echo "[Phase 5] Ansible 부트스트랩 테스트를 실행합니다..."
	ansible -i $(RESOLVER) -m ping all

# Ansible 부트스트랩 실행
bootstrap:
	@echo "[Phase 5] Ansible 부트스트랩을 실행합니다..."
	$(ANSIBLE) -i $(RESOLVER) $(SITE_YAML)

# AWS 인프라 제거
destroy-aws:
	@echo "[Phase 4] AWS 인프라를 제거합니다..."
	$(PYTHON) $(REMOVER)

# 생성된 파일 및 캐시 정리
clean:
	@echo "[Phase 4] 생성된 파일 및 캐시를 정리합니다..."
	@echo "이 명령어는 destroy-aws가 먼저 실행된 후에 사용되어야 합니다."; read _
	find . -name "*.tfstate*" -type f -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +