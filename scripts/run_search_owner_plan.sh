#!/usr/bin/env bash

set -euo pipefail

echo "[Search Owner]"
echo "문서 기준: service-spec.md, directory.md, workflow.md, parallel-search-implementation-plan.md"
echo
echo "1. service-spec.md에서 canonical normalized evidence/quality report 계약 확인"
echo "2. directory.md에서 search 담당 소유 범위 확인"
echo "3. raw_result_schema.py, normalized_evidence_schema.py, quality_report_schema.py 고정"
echo "4. base_search_agent.py 및 6개 search agent 인터페이스 구현"
echo "5. parallel_search_runner.py 구현"
echo "6. normalization/evidence_normalizer.py, evidence_loader.py, tagging.py, keypoint_extractor.py 구현"
echo "7. quality/ 하위 rule 모듈과 quality_gate.py 구현"
echo "8. repository/provider 연결"
echo "9. unit 테스트 작성"
echo "10. search -> normalization -> quality smoke test 수행"
echo
echo "[소유 범위]"
echo "- src/agents/base/"
echo "- src/agents/search/"
echo "- src/orchestration/parallel_search_runner.py"
echo "- src/normalization/"
echo "- src/quality/"
echo "- src/schemas/raw_result_schema.py"
echo "- src/schemas/normalized_evidence_schema.py"
echo "- src/schemas/quality_report_schema.py"
echo "- src/storage/repositories/raw_finding_repository.py"
echo "- src/storage/repositories/normalized_evidence_repository.py"
echo "- src/storage/repositories/quality_report_repository.py"
echo "- src/providers/search/"
echo
echo "[수정 금지]"
echo "- src/schemas/analysis_output_schema.py"
echo "- src/schemas/report_output_schema.py"
echo "- src/agents/analysis/"
echo "- src/orchestration/merge_node.py"
