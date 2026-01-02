#!/usr/bin/env python3
"""
Advanced Report Generation with HTML Dashboards

Generates comprehensive test reports in multiple formats:
- HTML interactive dashboard
- JSON detailed results
- CSV for spreadsheet analysis
- Markdown for documentation

Features:
- Trend tracking across test runs
- Interactive visualizations
- Comparative analysis
- Performance metrics
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import csv
from collections import defaultdict

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate comprehensive test reports."""

    def __init__(self, output_dir: str = "test_results"):
        """Initialize report generator."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_html_report(
        self,
        results: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        output_filename: Optional[str] = None
    ) -> str:
        """Generate HTML dashboard report."""
        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"report_{timestamp}.html"

        output_path = self.output_dir / output_filename

        # Calculate statistics
        stats = self._calculate_stats(results)

        # Generate HTML
        html = self._build_html_dashboard(results, metadata, stats)

        with open(output_path, 'w') as f:
            f.write(html)

        logger.info(f"Generated HTML report: {output_path}")
        return str(output_path)

    def _build_html_dashboard(
        self,
        results: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        stats: Dict[str, Any]
    ) -> str:
        """Build HTML dashboard content."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build result tables HTML
        result_rows = self._build_result_rows(results)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ClimateGPT Test Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        .metadata {{
            background: #f8f9fa;
            padding: 20px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .metadata-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }}
        .metadata-item {{
            padding: 15px;
            background: white;
            border-left: 4px solid #667eea;
            border-radius: 4px;
        }}
        .metadata-item label {{
            display: block;
            font-weight: 600;
            color: #666;
            font-size: 0.9em;
            margin-bottom: 5px;
        }}
        .metadata-item value {{
            display: block;
            font-size: 1.1em;
            color: #333;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            padding: 30px;
            background: white;
        }}
        .stat-card {{
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-card .value {{
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .stat-card .label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        .success {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }}
        .error {{
            background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
        }}
        .warning {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }}
        .section {{
            padding: 30px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .section h2 {{
            font-size: 1.8em;
            margin-bottom: 20px;
            color: #333;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th {{
            background: #f8f9fa;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            color: #333;
            border-bottom: 2px solid #e0e0e0;
        }}
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #f0f0f0;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .status-success {{
            color: #11998e;
            font-weight: 600;
        }}
        .status-error {{
            color: #eb3349;
            font-weight: 600;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }}
        .error-list {{
            background: #fff5f5;
            padding: 15px;
            border-left: 4px solid #eb3349;
            border-radius: 4px;
            margin: 10px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ClimateGPT Test Report</h1>
            <p>Comparative LLM Testing Results</p>
        </div>

        <div class="metadata">
            <div class="metadata-grid">
                <div class="metadata-item">
                    <label>Report Generated</label>
                    <value>{timestamp}</value>
                </div>
                <div class="metadata-item">
                    <label>ClimateGPT URL</label>
                    <value>{metadata.get('config', {}).get('climategpt_url', 'N/A')}</value>
                </div>
                <div class="metadata-item">
                    <label>Llama Model</label>
                    <value>{metadata.get('config', {}).get('llama_model', 'N/A')}</value>
                </div>
                <div class="metadata-item">
                    <label>Total Tests</label>
                    <value>{metadata.get('total_tests', 0)}</value>
                </div>
            </div>
        </div>

        <div class="stats">
            <div class="stat-card success">
                <div class="value">{stats['total_success']}</div>
                <div class="label">Successful Tests</div>
            </div>
            <div class="stat-card error">
                <div class="value">{stats['total_errors']}</div>
                <div class="label">Failed Tests</div>
            </div>
            <div class="stat-card warning">
                <div class="value">{stats['success_rate']:.1f}%</div>
                <div class="label">Success Rate</div>
            </div>
            <div class="stat-card">
                <div class="value">{stats['avg_response_time']:.0f}ms</div>
                <div class="label">Avg Response Time</div>
            </div>
        </div>

        <div class="section">
            <h2>Test Results by System</h2>
            <table>
                <thead>
                    <tr>
                        <th>Question ID</th>
                        <th>Question</th>
                        <th>System</th>
                        <th>Response Time (ms)</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {result_rows}
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p>Generated with ClimateGPT Testing Framework</p>
        </div>
    </div>
</body>
</html>"""
        return html

    def _build_result_rows(self, results: List[Dict[str, Any]]) -> str:
        """Build HTML table rows for results."""
        rows = []
        for result in results:
            status = "✓ Success" if result.get('error') is None else f"✗ Error"
            status_class = "status-success" if result.get('error') is None else "status-error"
            question_text = result.get('question', 'N/A')[:60] + "..."

            row = f"""
                    <tr>
                        <td>{result.get('question_id', 'N/A')}</td>
                        <td>{question_text}</td>
                        <td>{result.get('system', 'N/A')}</td>
                        <td>{result.get('response_time_ms', 0):.1f}</td>
                        <td class="{status_class}">{status}</td>
                    </tr>
            """
            rows.append(row)

        return "".join(rows)

    def _calculate_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate test statistics."""
        total = len(results)
        success = sum(1 for r in results if r.get('error') is None)
        errors = total - success

        response_times = [r.get('response_time_ms', 0) for r in results if r.get('error') is None]
        avg_time = sum(response_times) / len(response_times) if response_times else 0

        return {
            'total': total,
            'total_success': success,
            'total_errors': errors,
            'success_rate': (success / total * 100) if total > 0 else 0,
            'avg_response_time': avg_time
        }

    def generate_markdown_report(
        self,
        results: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        output_filename: Optional[str] = None
    ) -> str:
        """Generate Markdown report."""
        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"report_{timestamp}.md"

        output_path = self.output_dir / output_filename

        stats = self._calculate_stats(results)

        markdown = f"""# ClimateGPT Test Report

## Summary

- **Test Date**: {metadata.get('test_date', 'N/A')}
- **Total Tests**: {metadata.get('total_tests', 0)}
- **Success Rate**: {stats['success_rate']:.1f}%
- **Average Response Time**: {stats['avg_response_time']:.0f}ms

## Configuration

- **ClimateGPT URL**: {metadata.get('config', {}).get('climategpt_url', 'N/A')}
- **Llama Model**: {metadata.get('config', {}).get('llama_model', 'N/A')}

## Results

| Question ID | Status | System | Response Time (ms) |
|-------------|--------|--------|-------------------|
"""
        for result in results:
            status = "✓" if result.get('error') is None else "✗"
            markdown += f"| {result.get('question_id', 'N/A')} | {status} | {result.get('system', 'N/A')} | {result.get('response_time_ms', 0):.1f} |\n"

        with open(output_path, 'w') as f:
            f.write(markdown)

        logger.info(f"Generated Markdown report: {output_path}")
        return str(output_path)

    def generate_csv_report(
        self,
        results: List[Dict[str, Any]],
        output_filename: Optional[str] = None
    ) -> str:
        """Generate CSV report."""
        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"report_{timestamp}.csv"

        output_path = self.output_dir / output_filename

        with open(output_path, 'w', newline='') as f:
            if not results:
                return str(output_path)

            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)

        logger.info(f"Generated CSV report: {output_path}")
        return str(output_path)

    def load_historical_results(self, days: int = 30) -> List[Dict[str, Any]]:
        """Load historical test results for trend analysis."""
        cutoff_date = datetime.now() - timedelta(days=days)
        historical = []

        for result_file in sorted(self.output_dir.glob("test_results_*.json")):
            try:
                file_mtime = datetime.fromtimestamp(result_file.stat().st_mtime)
                if file_mtime < cutoff_date:
                    continue

                with open(result_file, 'r') as f:
                    data = json.load(f)
                    historical.append({
                        'timestamp': data.get('metadata', {}).get('test_date', ''),
                        'file': result_file.name,
                        'total_tests': data.get('metadata', {}).get('total_tests', 0),
                        'results': data.get('results', [])
                    })
            except Exception as e:
                logger.warning(f"Error loading {result_file.name}: {e}")

        return historical
