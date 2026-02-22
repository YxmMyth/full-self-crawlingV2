"""
Capability Test Package - Recon Agent 能力检测测试包

检测 Recon Agent 当期能力边界，验证10个不同类型的数据采集需求。
"""

from .test_cases import (
    TestCase,
    TEST_CASES,
    get_test_cases_by_phase,
    get_test_case_by_id,
    get_all_test_cases_sorted,
    CAPABILITY_MATRIX,
    TEST_CONFIG,
)
from .runner import TestResult, CapabilityTestRunner
from .result_analyzer import (
    ResultAnalyzer,
    CapabilityReport,
    PhaseReport,
    IssueAnalysis,
    analyze_results,
)

__all__ = [
    # Test Cases
    "TestCase",
    "TEST_CASES",
    "get_test_cases_by_phase",
    "get_test_case_by_id",
    "get_all_test_cases_sorted",
    "CAPABILITY_MATRIX",
    "TEST_CONFIG",
    # Runner
    "TestResult",
    "CapabilityTestRunner",
    # Analyzer
    "ResultAnalyzer",
    "CapabilityReport",
    "PhaseReport",
    "IssueAnalysis",
    "analyze_results",
]
