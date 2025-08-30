#!/usr/bin/env python3

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Test Report Viewer
Displays test results in a readable format with statistics and recommendations.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import argparse


class Colors:
    """Terminal color codes"""

    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    PURPLE = "\033[0;35m"
    CYAN = "\033[0;36m"
    WHITE = "\033[1;37m"
    NC = "\033[0m"  # No Color


def format_timestamp(iso_timestamp: str) -> str:
    """Format ISO timestamp to readable format"""
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return iso_timestamp


def print_header(title: str, color: str = Colors.GREEN):
    """Print a formatted header"""
    print(f"\n{color}{'=' * 60}{Colors.NC}")
    print(f"{color}{title.center(60)}{Colors.NC}")
    print(f"{color}{'=' * 60}{Colors.NC}\n")


def print_section(title: str, color: str = Colors.CYAN):
    """Print a section header"""
    print(f"\n{color}{title}{Colors.NC}")
    print(f"{color}{'-' * len(title)}{Colors.NC}")


def load_reports(report_dir: Path) -> List[Dict[str, Any]]:
    """Load all JSON reports from the report directory"""
    reports = []

    if not report_dir.exists():
        print(f"{Colors.RED}Report directory not found: {report_dir}{Colors.NC}")
        return reports

    for file in sorted(report_dir.glob("*.json")):
        try:
            with open(file, "r") as f:
                data = json.load(f)
                data["_filename"] = file.name
                reports.append(data)
        except json.JSONDecodeError:
            print(f"{Colors.YELLOW}Warning: Could not parse {file.name}{Colors.NC}")
        except Exception as e:
            print(f"{Colors.YELLOW}Warning: Error reading {file.name}: {e}{Colors.NC}")

    return reports


def analyze_reports(reports: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze reports and generate statistics"""
    analysis = {
        "total_reports": len(reports),
        "total_errors": 0,
        "total_warnings": 0,
        "error_by_view": {},
        "warning_by_view": {},
        "error_types": {},
        "test_summaries": {},
        "latest_run": None,
        "recommendations": [],
    }

    for report in reports:
        # Update latest run
        if report.get("timestamp"):
            if (
                not analysis["latest_run"]
                or report["timestamp"] > analysis["latest_run"]
            ):
                analysis["latest_run"] = report["timestamp"]

        # Count errors
        for error in report.get("errors", []):
            analysis["total_errors"] += 1
            view = error.get("view", "unknown")
            analysis["error_by_view"][view] = analysis["error_by_view"].get(view, 0) + 1

            error_type = error.get("exception_type", "Unknown")
            analysis["error_types"][error_type] = (
                analysis["error_types"].get(error_type, 0) + 1
            )

        # Count warnings
        for warning in report.get("warnings", []):
            analysis["total_warnings"] += 1
            view = warning.get("view", "unknown")
            analysis["warning_by_view"][view] = (
                analysis["warning_by_view"].get(view, 0) + 1
            )

        # Collect test summaries
        for test, result in report.get("summary", {}).items():
            if test not in analysis["test_summaries"]:
                analysis["test_summaries"][test] = {"PASS": 0, "FAIL": 0}
            analysis["test_summaries"][test][result] = (
                analysis["test_summaries"][test].get(result, 0) + 1
            )

    # Generate recommendations
    if analysis["total_errors"] > 0:
        analysis["recommendations"].append(
            f"Fix {analysis['total_errors']} errors found in views"
        )

    if analysis["total_warnings"] > 0:
        analysis["recommendations"].append(
            f"Review {analysis['total_warnings']} warnings for potential issues"
        )

    # Most problematic views
    if analysis["error_by_view"]:
        worst_view = max(analysis["error_by_view"].items(), key=lambda x: x[1])
        analysis["recommendations"].append(
            f"Priority: Fix '{worst_view[0]}' view ({worst_view[1]} errors)"
        )

    return analysis


def display_report_details(report: Dict[str, Any], verbose: bool = False):
    """Display details of a single report"""
    print(f"\n{Colors.BLUE}Report: {report.get('_filename', 'Unknown')}{Colors.NC}")
    print(f"Timestamp: {format_timestamp(report.get('timestamp', 'N/A'))}")
    print(f"Test Class: {report.get('test_class', 'N/A')}")

    # Show errors
    errors = report.get("errors", [])
    if errors:
        print(f"\n{Colors.RED}Errors ({len(errors)}):{Colors.NC}")
        for i, error in enumerate(errors[: 5 if not verbose else None], 1):
            print(f"  {i}. View: {error.get('view', 'unknown')}")
            print(f"     Message: {error.get('message', 'No message')}")
            if verbose and "exception_type" in error:
                print(f"     Type: {error['exception_type']}")
        if not verbose and len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more errors")

    # Show warnings
    warnings = report.get("warnings", [])
    if warnings:
        print(f"\n{Colors.YELLOW}Warnings ({len(warnings)}):{Colors.NC}")
        for i, warning in enumerate(warnings[: 5 if not verbose else None], 1):
            print(f"  {i}. View: {warning.get('view', 'unknown')}")
            print(f"     Message: {warning.get('message', 'No message')}")
        if not verbose and len(warnings) > 5:
            print(f"  ... and {len(warnings) - 5} more warnings")

    # Show summary
    summary = report.get("summary", {})
    if summary:
        print(f"\n{Colors.CYAN}Test Summary:{Colors.NC}")
        passed = sum(1 for v in summary.values() if v == "PASS")
        failed = sum(1 for v in summary.values() if v == "FAIL")
        print(f"  ✓ Passed: {passed}")
        print(f"  ✗ Failed: {failed}")


def display_analysis(analysis: Dict[str, Any]):
    """Display the analysis results"""
    print_header("Test Analysis Summary")

    # Overview
    print(f"Total Reports Analyzed: {analysis['total_reports']}")
    print(
        f"Latest Test Run: {format_timestamp(analysis['latest_run']) if analysis['latest_run'] else 'N/A'}"
    )
    print(f"\nTotal Errors: {Colors.RED}{analysis['total_errors']}{Colors.NC}")
    print(f"Total Warnings: {Colors.YELLOW}{analysis['total_warnings']}{Colors.NC}")

    # Test results
    if analysis["test_summaries"]:
        print_section("Test Results")
        for test, results in sorted(analysis["test_summaries"].items()):
            total = sum(results.values())
            pass_rate = (results.get("PASS", 0) / total * 100) if total > 0 else 0
            color = (
                Colors.GREEN
                if pass_rate == 100
                else Colors.YELLOW
                if pass_rate >= 50
                else Colors.RED
            )
            print(
                f"  {test}: {color}{pass_rate:.1f}% pass rate{Colors.NC} "
                f"({results.get('PASS', 0)} passed, {results.get('FAIL', 0)} failed)"
            )

    # Error distribution
    if analysis["error_by_view"]:
        print_section("Views with Errors")
        for view, count in sorted(
            analysis["error_by_view"].items(), key=lambda x: x[1], reverse=True
        ):
            print(
                f"  {Colors.RED}●{Colors.NC} {view}: {count} error{'s' if count > 1 else ''}"
            )

    # Warning distribution
    if analysis["warning_by_view"]:
        print_section("Views with Warnings")
        for view, count in sorted(
            analysis["warning_by_view"].items(), key=lambda x: x[1], reverse=True
        ):
            print(
                f"  {Colors.YELLOW}●{Colors.NC} {view}: {count} warning{'s' if count > 1 else ''}"
            )

    # Error types
    if analysis["error_types"]:
        print_section("Error Types")
        for error_type, count in sorted(
            analysis["error_types"].items(), key=lambda x: x[1], reverse=True
        ):
            print(f"  {error_type}: {count}")

    # Recommendations
    if analysis["recommendations"]:
        print_section("Recommendations", Colors.PURPLE)
        for i, rec in enumerate(analysis["recommendations"], 1):
            print(f"  {i}. {rec}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="View Thoth test reports")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed information"
    )
    parser.add_argument(
        "--latest", "-l", action="store_true", help="Show only the latest report"
    )
    parser.add_argument(
        "--report-dir", "-d", default="tests/reports", help="Report directory path"
    )
    parser.add_argument(
        "--json", "-j", action="store_true", help="Output analysis as JSON"
    )

    args = parser.parse_args()

    # Load reports
    report_dir = Path(args.report_dir)
    reports = load_reports(report_dir)

    if not reports:
        print(f"{Colors.RED}No reports found in {report_dir}{Colors.NC}")
        print(
            f"\nTip: Run tests first with: {Colors.CYAN}./scripts/run-tests-local.sh{Colors.NC}"
        )
        sys.exit(1)

    if args.latest:
        # Show only the latest report
        latest_report = max(reports, key=lambda r: r.get("timestamp", ""))
        print_header("Latest Test Report")
        display_report_details(latest_report, verbose=args.verbose)
    elif args.json:
        # Output analysis as JSON
        analysis = analyze_reports(reports)
        print(json.dumps(analysis, indent=2))
    else:
        # Show full analysis
        analysis = analyze_reports(reports)
        display_analysis(analysis)

        # Optionally show individual reports
        if args.verbose:
            print_header("Individual Reports", Colors.BLUE)
            for report in reports:
                display_report_details(report, verbose=True)
                print("\n" + "-" * 60)

    # Exit with error code if there are failures
    analysis = analyze_reports(reports)
    if analysis["total_errors"] > 0:
        sys.exit(1)
    else:
        print(f"\n{Colors.GREEN}✓ All tests completed successfully!{Colors.NC}")
        sys.exit(0)


if __name__ == "__main__":
    main()
