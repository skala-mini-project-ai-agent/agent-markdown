#!/usr/bin/env bash

set -euo pipefail

echo "[Parallel Work Order]"
echo
echo "0. 공통 기준 먼저 고정"
echo "- AGENTS.md"
echo "- service-spec.md"
echo "- directory.md"
echo "- workflow.md"
echo
echo "1. Search Owner 시작"
echo "- canonical normalized evidence / quality report schema 먼저 확정"
echo "- search -> normalization -> quality 결과를 analysis가 읽을 수 있게 유지"
echo
echo "2. Analysis Owner 병행 시작"
echo "- search schema는 수정하지 않고 소비만 함"
echo "- analysis_output_schema.py, merge_node.py 중심으로 구현"
echo
echo "3. Report Owner 병행 시작"
echo "- analysis output을 소비만 함"
echo "- report_output_schema.py, report_generation_agent.py 중심으로 구현"
echo
echo "4. Supervisor Owner 마지막 통합"
echo "- stage gate, retry, approval 연결"
echo "- final approval 기록 주체는 Supervisor"
echo "- 실행: bash scripts/run_supervisor_owner_plan.sh"
echo
echo "5. 통합 순서"
echo "- Search 결과 연결"
echo "- Analysis 결과 연결"
echo "- Report 결과 연결"
echo "- Supervisor end-to-end smoke test"
