#!/usr/bin/env bash

set -euo pipefail

echo "[Report Owner]"
echo "문서 기준: service-spec.md, directory.md, workflow.md, report-agent.md"
echo
echo "1. service-spec.md에서 report output 계약과 입력 참조 규칙 확인"
echo "2. directory.md에서 report 담당 소유 범위 확인"
echo "3. report_output_schema.py 고정"
echo "4. report_sections.py, report_warnings.py 정리"
echo "5. report_generation_agent.py 구현"
echo "6. reference trace 로직 구현"
echo "7. Markdown/HTML 렌더링 구현"
echo "8. PDF adapter 또는 placeholder 구현"
echo "9. report_repository.py 연결"
echo "10. unit/integration 테스트 작성"
echo
echo "[소유 범위]"
echo "- src/agents/analysis/report_generation_agent.py"
echo "- src/schemas/report_output_schema.py"
echo "- src/storage/repositories/report_repository.py"
echo "- src/prompts/analysis/report_generation_prompt.md"
echo "- src/config/report_sections.py"
echo "- src/config/report_warnings.py"
echo
echo "[수정 금지]"
echo "- src/schemas/normalized_evidence_schema.py"
echo "- src/schemas/analysis_output_schema.py"
echo "- src/orchestration/merge_node.py"
echo "- src/supervisor/"
