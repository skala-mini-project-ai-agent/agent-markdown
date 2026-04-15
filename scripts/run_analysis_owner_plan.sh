#!/usr/bin/env bash

set -euo pipefail

echo "[Analysis Owner]"
echo "문서 기준: service-spec.md, directory.md, workflow.md, analyze-agent.md"
echo
echo "1. service-spec.md에서 canonical normalized evidence 계약 확인"
echo "2. directory.md에서 analysis 담당 소유 범위 확인"
echo "3. analysis_output_schema.py 고정"
echo "4. strategic_overlap.py와 thresholds.py 기준 정리"
echo "5. trl_analysis_agent.py 구현"
echo "6. threat_analysis_agent.py 구현"
echo "7. merge_node.py 및 priority matrix 생성 로직 구현"
echo "8. analysis_result_repository.py 연결"
echo "9. unit 테스트 작성"
echo "10. quality-passed evidence 입력 기준 analysis smoke test 수행"
echo
echo "[소유 범위]"
echo "- src/agents/analysis/trl_analysis_agent.py"
echo "- src/agents/analysis/threat_analysis_agent.py"
echo "- src/orchestration/merge_node.py"
echo "- src/schemas/analysis_output_schema.py"
echo "- src/storage/repositories/analysis_result_repository.py"
echo "- src/providers/llm/"
echo "- src/config/strategic_overlap.py"
echo "- src/prompts/analysis/trl_analysis_prompt.md"
echo "- src/prompts/analysis/threat_analysis_prompt.md"
echo
echo "[수정 금지]"
echo "- src/schemas/normalized_evidence_schema.py"
echo "- src/schemas/quality_report_schema.py"
echo "- src/agents/analysis/report_generation_agent.py"
echo "- src/schemas/report_output_schema.py"
