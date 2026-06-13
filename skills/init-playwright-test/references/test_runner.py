#!/usr/bin/env python
"""
测试执行和分析工具
为 Healer agent 提供结构化 JSON 输出
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


class TestRunner:
    """测试执行器，封装 pytest 调用并生成结构化输出"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.report_dir = project_root / "report"
        self.history_dir = project_root / ".test_history"
        self.screenshots_dir = self.report_dir / "screenshots"

        # 确保目录存在
        self.report_dir.mkdir(exist_ok=True)
        self.history_dir.mkdir(exist_ok=True)
        self.screenshots_dir.mkdir(exist_ok=True)

    def run_tests(
        self,
        module: Optional[str] = None,
        tag: Optional[str] = None,
        failed_only: bool = False,
        debug: bool = False,
        output_format: str = "json"
    ) -> Dict[str, Any]:
        """
        执行测试并返回结构化结果

        Args:
            module: 按模块筛选 (如 tests/login/)
            tag: 按 pytest marker 筛选
            failed_only: 只运行上次失败的测试
            debug: 启用调试模式
            output_format: 输出格式 (json/text)

        Returns:
            结构化的测试结果字典
        """
        start_time = time.time()
        json_report_file = self.report_dir / "pytest_report.json"
        coverage_file = self.report_dir / "coverage.json"

        # 删除旧的报告文件，避免读取到过期数据
        json_report_file.unlink(missing_ok=True)
        coverage_file.unlink(missing_ok=True)

        pytest_args = [
            sys.executable, "-m", "pytest",
            "-v",
            "--tb=short",
            f"--json-report",
            f"--json-report-file={json_report_file}",
            f"--html={self.report_dir / 'report.html'}",
            "--self-contained-html",
            # 如需覆盖率，手动添加: --cov=<your_app_module>
        ]

        if module:
            pytest_args.append(str(self.project_root / module))
        else:
            pytest_args.append(str(self.project_root / "tests"))

        if tag:
            pytest_args.extend(["-m", tag])

        if failed_only:
            pytest_args.append("--lf")

        if debug:
            pytest_args.append("-s")

        result = subprocess.run(
            pytest_args,
            cwd=str(self.project_root),
            capture_output=True,
            text=True
        )

        duration = time.time() - start_time

        test_results = self._parse_json_report(json_report_file, duration)

        history = self._load_history()
        test_results["history"] = self._build_history_info(
            test_results["summary"], history
        )
        self._save_history(test_results["summary"])

        test_results["returncode"] = result.returncode

        return test_results

    def _parse_json_report(
        self, report_file: Path, duration: float
    ) -> Dict[str, Any]:
        """解析 pytest-json-report 生成的 JSON 报告"""
        pytest_report: Dict[str, Any] = {}
        if report_file.exists():
            try:
                with open(report_file, "r", encoding="utf-8") as f:
                    pytest_report = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        summary = self._build_summary(pytest_report, duration)
        failures = self._extract_failures(pytest_report)
        coverage = self._extract_coverage()
        performance = self._extract_performance(pytest_report)

        return {
            "summary": summary,
            "failures": failures,
            "coverage": coverage,
            "performance": performance,
        }

    def _build_summary(
        self, pytest_report: Dict[str, Any], duration: float
    ) -> Dict[str, int]:
        """从 pytest-json-report 构建摘要"""
        summary_data = pytest_report.get("summary", {})
        return {
            "total": summary_data.get("total", 0),
            "passed": summary_data.get("passed", 0),
            "failed": summary_data.get("failed", 0),
            "skipped": summary_data.get("skipped", 0),
            "error": summary_data.get("error", 0),
            "duration": round(duration, 2)
        }

    def _extract_failures(
        self, pytest_report: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """从 pytest-json-report 提取失败测试详情"""
        failures = []
        tests = pytest_report.get("tests", [])

        for test in tests:
            if test.get("outcome") not in ["failed", "error"]:
                continue

            test_id = test.get("nodeid", "")
            call_info = test.get("call", {})
            crash_info = call_info.get("crash", {})

            failure = {
                "test_id": test_id,
                "error_type": crash_info.get("type", "Error"),
                "error_message": crash_info.get("message", ""),
                "traceback": call_info.get("longrepr", ""),
                "screenshot": self._find_screenshot(test_id),
                "line_number": self._extract_line_number(call_info),
                "context": ""
            }
            failures.append(failure)

        return failures

    def _extract_line_number(self, call_info: Dict[str, Any]) -> Optional[int]:
        """从调用信息中提取行号"""
        longrepr = call_info.get("longrepr", "")
        if isinstance(longrepr, str):
            import re
            match = re.search(r":(\d+):", longrepr)
            if match:
                return int(match.group(1))
        return None

    def _extract_coverage(self) -> Dict[str, Any]:
        """从 coverage.json 提取覆盖率信息"""
        coverage_file = self.report_dir / "coverage.json"
        coverage = {"total": 0.0, "by_module": {}}

        if not coverage_file.exists():
            return coverage

        try:
            with open(coverage_file, "r", encoding="utf-8") as f:
                cov_data = json.load(f)

            totals = cov_data.get("totals", {})
            coverage["total"] = totals.get("percent_covered", 0.0)

            files = cov_data.get("files", {})
            for file_path, file_data in files.items():
                summary = file_data.get("summary", {})
                coverage["by_module"][file_path] = summary.get("percent_covered", 0.0)

        except (json.JSONDecodeError, IOError, KeyError):
            pass

        return coverage

    def _extract_performance(self, pytest_report: Dict[str, Any]) -> Dict[str, Any]:
        """从 pytest-json-report 提取测试耗时信息"""
        slowest_tests = []
        tests = pytest_report.get("tests", [])

        for test in tests:
            call_info = test.get("call", {})
            duration = call_info.get("duration")
            if duration is None:
                continue

            slowest_tests.append({
                "test_id": test.get("nodeid", ""),
                "duration": duration
            })

        return {
            "slowest_tests": sorted(
                slowest_tests, key=lambda x: x["duration"], reverse=True
            )[:10]
        }

    def _find_screenshot(self, test_id: str) -> Optional[str]:
        """查找与测试关联的截图"""
        # 将 test_id 转换为文件名
        safe_name = test_id.replace("/", "_").replace("\\", "_").replace("::", "_")
        patterns = [
            self.screenshots_dir / f"{safe_name}_failure.png",
            self.screenshots_dir / f"{safe_name}.png",
        ]
        for path in patterns:
            if path.exists():
                return str(path)
        return None

    def _load_history(self) -> List[Dict[str, Any]]:
        """加载历史运行记录"""
        history_file = self.history_dir / "runs.json"
        if history_file.exists():
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def _save_history(self, summary: Dict[str, Any]) -> None:
        """保存当前运行结果到历史记录"""
        history = self._load_history()
        entry = {
            "timestamp": datetime.now().isoformat(),
            "passed": summary.get("passed", 0),
            "failed": summary.get("failed", 0),
            "skipped": summary.get("skipped", 0),
            "total": summary.get("total", 0),
            "duration": summary.get("duration", 0)
        }
        history.append(entry)
        # 只保留最近 50 条记录
        history = history[-50:]
        history_file = self.history_dir / "runs.json"
        # 确保目录存在
        history_file.parent.mkdir(parents=True, exist_ok=True)
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def _build_history_info(
        self,
        current: Dict[str, Any],
        history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """构建历史对比信息"""
        if not history:
            return {"previous_run": None, "trend": "new"}

        previous = history[-1]
        prev_failed = previous.get("failed", 0)
        curr_failed = current.get("failed", 0)

        if curr_failed < prev_failed:
            trend = "improving"
        elif curr_failed > prev_failed:
            trend = "degrading"
        else:
            trend = "stable"

        return {
            "previous_run": {
                "passed": previous.get("passed", 0),
                "failed": previous.get("failed", 0),
                "timestamp": previous.get("timestamp", "")
            },
            "trend": trend
        }


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="测试执行和分析工具 - 为 Healer agent 提供结构化 JSON 输出"
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # run 子命令
    run_parser = subparsers.add_parser("run", help="运行测试")
    run_parser.add_argument(
        "--module",
        type=str,
        help="按模块筛选 (如 tests/login/)"
    )
    run_parser.add_argument(
        "--tag",
        type=str,
        help="按 pytest marker 筛选"
    )
    run_parser.add_argument(
        "--failed-only",
        action="store_true",
        help="只运行上次失败的测试"
    )
    run_parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式"
    )
    run_parser.add_argument(
        "--output",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式 (json/text)"
    )

    args = parser.parse_args()

    if args.command != "run":
        parser.print_help()
        return 1

    # 获取项目根目录
    project_root = Path(__file__).parent.parent

    # 创建测试运行器
    runner = TestRunner(project_root)

    # 运行测试
    results = runner.run_tests(
        module=args.module,
        tag=args.tag,
        failed_only=args.failed_only,
        debug=args.debug,
        output_format=args.output
    )

    # 输出结果
    if args.output == "json":
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        # 文本格式输出
        summary = results["summary"]
        print(f"\n{'='*60}")
        print(f"测试摘要")
        print(f"{'='*60}")
        print(f"总计: {summary['total']}")
        print(f"通过: {summary['passed']}")
        print(f"失败: {summary['failed']}")
        print(f"跳过: {summary['skipped']}")
        print(f"错误: {summary.get('error', 0)}")
        print(f"耗时: {summary['duration']}s")

        if results["failures"]:
            print(f"\n{'='*60}")
            print(f"失败详情 ({len(results['failures'])} 个)")
            print(f"{'='*60}")
            for i, failure in enumerate(results["failures"], 1):
                print(f"\n{i}. {failure['test_id']}")
                print(f"   错误类型: {failure['error_type']}")
                print(f"   错误消息: {failure['error_message']}")
                if failure.get("line_number"):
                    print(f"   行号: {failure['line_number']}")
                if failure.get("screenshot"):
                    print(f"   截图: {failure['screenshot']}")

        coverage = results["coverage"]
        if coverage["total"] > 0:
            print(f"\n{'='*60}")
            print(f"覆盖率")
            print(f"{'='*60}")
            print(f"总计: {coverage['total']:.1f}%")

        history = results.get("history", {})
        if history.get("previous_run"):
            print(f"\n{'='*60}")
            print(f"历史对比")
            print(f"{'='*60}")
            prev = history["previous_run"]
            print(f"上次运行: 通过 {prev['passed']}, 失败 {prev['failed']}")
            print(f"趋势: {history['trend']}")

    # 返回退出码
    return 0 if results["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
