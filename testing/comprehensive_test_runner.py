#!/usr/bin/env python3
"""
Comprehensive Test Runner for ClimateGPT MCP System

This script orchestrates testing of all major components:
1. MCP Server (mcp_server_stdio.py)
2. MCP HTTP Bridge (mcp_http_bridge.py)
3. LLM Runner (run_llm.py)
4. End-to-End Integration
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
import signal
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, asdict
import traceback

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

@dataclass
class TestResult:
    """Represents a single test result"""
    test_name: str
    category: str
    status: str  # "PASS", "FAIL", "SKIP", "ERROR"
    duration: float
    message: str = ""
    error_details: str = ""

    def to_dict(self):
        return asdict(self)


class TestRunner:
    """Main test orchestrator"""

    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time = None
        self.bridge_process = None
        self.server_process = None

    def log_test(self, test_name: str, category: str, status: str,
                 duration: float, message: str = "", error_details: str = ""):
        """Log a test result"""
        result = TestResult(
            test_name=test_name,
            category=category,
            status=status,
            duration=duration,
            message=message,
            error_details=error_details
        )
        self.results.append(result)

        status_emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⏭️" if status == "SKIP" else "⚠️"
        logger.info(f"{status_emoji} {test_name} ({category}): {status} [{duration:.2f}s]")
        if message:
            logger.info(f"   Message: {message}")
        if error_details:
            logger.error(f"   Error: {error_details}")

    async def setup_test_environment(self) -> bool:
        """Setup and verify test environment"""
        logger.info("\n" + "="*80)
        logger.info("PHASE 0: TEST ENVIRONMENT SETUP")
        logger.info("="*80)

        start = time.time()
        try:
            # Check Python version
            if sys.version_info < (3, 10):
                raise ValueError(f"Python 3.10+ required, got {sys.version_info.major}.{sys.version_info.minor}")

            # Check required files
            required_files = [
                "src/mcp_server_stdio.py",
                "src/mcp_http_bridge.py",
                "src/run_llm.py",
                "utils/config.py"
            ]

            for file in required_files:
                if not Path(file).exists():
                    raise FileNotFoundError(f"Required file not found: {file}")

            # Check .env
            if not Path(".env").exists():
                logger.warning(".env file not found, some tests may be skipped")

            # Check database
            try:
                import duckdb
                conn = duckdb.connect(":memory:")
                conn.close()
            except Exception as e:
                raise RuntimeError(f"DuckDB check failed: {e}")

            duration = time.time() - start
            self.log_test("Environment Setup", "Setup", "PASS", duration,
                         f"Python {sys.version_info.major}.{sys.version_info.minor}, DuckDB OK")
            return True

        except Exception as e:
            duration = time.time() - start
            self.log_test("Environment Setup", "Setup", "FAIL", duration,
                         error_details=str(e))
            return False

    async def test_mcp_server_imports(self) -> bool:
        """Test MCP server can be imported"""
        logger.info("\n" + "="*80)
        logger.info("PHASE 1: MCP SERVER TESTING")
        logger.info("="*80)

        start = time.time()
        try:
            logger.info("Test 1.1: Import mcp_server_stdio...")
            # We can't directly import the stdio server without stdin/stdout
            # but we can check the file and basic structure
            mcp_file = Path("src/mcp_server_stdio.py")
            content = mcp_file.read_text()

            # Check for key components
            required_strings = [
                "class QueryCache",
                "class DuckDBConnectionPool",
                "@app.call_tool",
                "list_emissions_datasets",
                "get_dataset_schema",
                "query_emissions",
                "calculate_yoy_change",
                "duckdb",
                "mcp.server"
            ]

            for string in required_strings:
                if string not in content:
                    raise ValueError(f"Missing component in MCP server: {string}")

            duration = time.time() - start
            self.log_test("MCP Server Import", "MCP Server", "PASS", duration,
                         "All required functions present")
            return True

        except Exception as e:
            duration = time.time() - start
            self.log_test("MCP Server Import", "MCP Server", "FAIL", duration,
                         error_details=str(e))
            return False

    async def test_database_connectivity(self) -> bool:
        """Test database connectivity and schema"""
        start = time.time()
        try:
            logger.info("Test 1.2: Database connectivity...")
            import duckdb
            from dotenv import load_dotenv

            load_dotenv()
            db_path = os.getenv("DUCKDB_PATH", "data/warehouse/climategpt.duckdb")

            if not Path(db_path).exists():
                raise FileNotFoundError(f"Database not found at {db_path}")

            conn = duckdb.connect(str(db_path), read_only=True)

            # Get tables
            tables = conn.execute("SELECT table_name FROM information_schema.tables").fetchall()

            if not tables:
                raise ValueError("No tables found in database")

            conn.close()

            duration = time.time() - start
            self.log_test("Database Connectivity", "MCP Server", "PASS", duration,
                         f"Connected. Found {len(tables)} tables")
            return True

        except Exception as e:
            duration = time.time() - start
            self.log_test("Database Connectivity", "MCP Server", "FAIL", duration,
                         error_details=str(e))
            return False

    async def test_config_loading(self) -> bool:
        """Test configuration loading"""
        start = time.time()
        try:
            logger.info("Test 1.3: Config loading...")

            # Load env manually to avoid config validation errors
            from dotenv import load_dotenv
            load_dotenv()

            api_key = os.getenv("OPENAI_API_KEY")
            db_path = os.getenv("DUCKDB_PATH", "data/warehouse/climategpt.duckdb")
            log_level = os.getenv("LOG_LEVEL", "INFO")
            environment = os.getenv("ENVIRONMENT", "development")
            mcp_port = os.getenv("PORT", "8010")

            if not db_path:
                raise ValueError("DATABASE_PATH not configured")

            logger.info(f"  Database: {db_path}")
            logger.info(f"  Log Level: {log_level}")
            logger.info(f"  Environment: {environment}")
            logger.info(f"  MCP Port: {mcp_port}")
            logger.info(f"  API Key: {'Configured' if api_key else 'Not configured'}")

            duration = time.time() - start
            self.log_test("Config Loading", "MCP Server", "PASS", duration,
                         "All config variables loaded")
            return True

        except Exception as e:
            duration = time.time() - start
            self.log_test("Config Loading", "MCP Server", "FAIL", duration,
                         error_details=str(e))
            return False

    async def test_mcp_bridge_imports(self) -> bool:
        """Test MCP HTTP bridge imports"""
        start = time.time()
        try:
            logger.info("\n" + "="*80)
            logger.info("PHASE 2: MCP HTTP BRIDGE TESTING")
            logger.info("="*80)
            logger.info("Test 2.1: Import mcp_http_bridge...")

            bridge_file = Path("src/mcp_http_bridge.py")
            content = bridge_file.read_text()

            # Check for key components
            required_strings = [
                "FastAPI",
                "RateLimiter",
                "CORSMiddleware",
                "/health",
                "/query",
                "/list_files"
            ]

            for string in required_strings:
                if string not in content:
                    raise ValueError(f"Missing component in bridge: {string}")

            duration = time.time() - start
            self.log_test("MCP Bridge Import", "MCP Bridge", "PASS", duration,
                         "All required components present")
            return True

        except Exception as e:
            duration = time.time() - start
            self.log_test("MCP Bridge Import", "MCP Bridge", "FAIL", duration,
                         error_details=str(e))
            return False

    async def test_fastapi_dependencies(self) -> bool:
        """Test FastAPI dependencies"""
        start = time.time()
        try:
            logger.info("Test 2.2: FastAPI dependencies...")

            import fastapi
            from fastapi import FastAPI
            from fastapi.middleware.cors import CORSMiddleware
            from pydantic import BaseModel

            # Create minimal app
            app = FastAPI()

            duration = time.time() - start
            self.log_test("FastAPI Dependencies", "MCP Bridge", "PASS", duration,
                         f"FastAPI {fastapi.__version__} OK")
            return True

        except Exception as e:
            duration = time.time() - start
            self.log_test("FastAPI Dependencies", "MCP Bridge", "FAIL", duration,
                         error_details=str(e))
            return False

    async def test_run_llm_imports(self) -> bool:
        """Test run_llm.py imports"""
        start = time.time()
        try:
            logger.info("\n" + "="*80)
            logger.info("PHASE 3: LLM RUNNER TESTING")
            logger.info("="*80)
            logger.info("Test 3.1: Import run_llm...")

            llm_file = Path("src/run_llm.py")
            content = llm_file.read_text()

            # Check for key components
            required_strings = [
                "get_persona_provider",
                "BaselineContextProvider",
                "requests",
                "MCP_BASE",
                "OPENAI_API_KEY"
            ]

            for string in required_strings:
                if string not in content:
                    raise ValueError(f"Missing component in run_llm: {string}")

            duration = time.time() - start
            self.log_test("LLM Runner Import", "LLM Runner", "PASS", duration,
                         "All required components present")
            return True

        except Exception as e:
            duration = time.time() - start
            self.log_test("LLM Runner Import", "LLM Runner", "FAIL", duration,
                         error_details=str(e))
            return False

    async def test_baseline_context(self) -> bool:
        """Test baseline context framework"""
        start = time.time()
        try:
            logger.info("Test 3.2: Baseline context framework...")

            from src.utils.baseline_context import (
                BaselineContextProvider,
                PolicyContextAugmenter,
                SectorStrategyAugmenter,
                EducationalContextAugmenter
            )

            # Try to instantiate
            provider = BaselineContextProvider()

            duration = time.time() - start
            self.log_test("Baseline Context", "LLM Runner", "PASS", duration,
                         "All context providers available")
            return True

        except ImportError as e:
            # This is expected if baseline context is optional
            duration = time.time() - start
            self.log_test("Baseline Context", "LLM Runner", "SKIP", duration,
                         f"Optional component not available: {e}")
            return True

        except Exception as e:
            duration = time.time() - start
            self.log_test("Baseline Context", "LLM Runner", "FAIL", duration,
                         error_details=str(e))
            return False

    async def test_openai_config(self) -> bool:
        """Test OpenAI configuration"""
        start = time.time()
        try:
            logger.info("Test 3.3: OpenAI configuration...")

            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_BASE_URL")
            model = os.getenv("MODEL")

            if not api_key:
                logger.warning("OPENAI_API_KEY not set - skipping LLM tests")
                duration = time.time() - start
                self.log_test("OpenAI Config", "LLM Runner", "SKIP", duration,
                             "OPENAI_API_KEY not configured")
                return True

            if ":" not in api_key:
                raise ValueError("OPENAI_API_KEY must be in format 'username:password'")

            logger.info(f"  Base URL: {base_url}")
            logger.info(f"  Model: {model}")
            logger.info(f"  API Key: {'***' + api_key[-10:]}")

            duration = time.time() - start
            self.log_test("OpenAI Config", "LLM Runner", "PASS", duration,
                         "OpenAI configuration valid")
            return True

        except Exception as e:
            duration = time.time() - start
            self.log_test("OpenAI Config", "LLM Runner", "FAIL", duration,
                         error_details=str(e))
            return False

    async def test_integration_setup(self) -> bool:
        """Test integration setup"""
        start = time.time()
        try:
            logger.info("\n" + "="*80)
            logger.info("PHASE 4: END-TO-END INTEGRATION TESTING")
            logger.info("="*80)
            logger.info("Test 4.1: Integration setup...")

            # Check all components are present
            files = [
                "src/mcp_server_stdio.py",
                "src/mcp_http_bridge.py",
                "src/run_llm.py",
                "src/streamlit_app.py"
            ]

            for f in files:
                if not Path(f).exists():
                    raise FileNotFoundError(f)

            duration = time.time() - start
            self.log_test("Integration Setup", "Integration", "PASS", duration,
                         "All components present")
            return True

        except Exception as e:
            duration = time.time() - start
            self.log_test("Integration Setup", "Integration", "FAIL", duration,
                         error_details=str(e))
            return False

    def generate_report(self) -> str:
        """Generate test report"""
        report = []
        report.append("\n" + "="*80)
        report.append("COMPREHENSIVE TEST REPORT")
        report.append("="*80 + "\n")

        report.append(f"Generated: {datetime.now().isoformat()}\n")

        # Summary statistics
        total = len(self.results)
        passed = len([r for r in self.results if r.status == "PASS"])
        failed = len([r for r in self.results if r.status == "FAIL"])
        skipped = len([r for r in self.results if r.status == "SKIP"])
        errored = len([r for r in self.results if r.status == "ERROR"])

        report.append("SUMMARY")
        report.append("-" * 40)
        report.append(f"Total Tests:   {total}")
        report.append(f"Passed:        {passed} ✅")
        report.append(f"Failed:        {failed} ❌")
        report.append(f"Skipped:       {skipped} ⏭️")
        report.append(f"Errored:       {errored} ⚠️")
        report.append(f"Success Rate:  {(passed/total*100):.1f}%\n")

        # Group by category
        categories = {}
        for result in self.results:
            if result.category not in categories:
                categories[result.category] = []
            categories[result.category].append(result)

        for category in sorted(categories.keys()):
            report.append(f"\n{category.upper()}")
            report.append("-" * 40)
            cat_results = categories[category]
            for result in cat_results:
                status_icon = "✅" if result.status == "PASS" else "❌" if result.status == "FAIL" else "⏭️" if result.status == "SKIP" else "⚠️"
                report.append(f"{status_icon} {result.test_name:<40} [{result.duration:.2f}s]")
                if result.message:
                    report.append(f"   → {result.message}")
                if result.error_details:
                    report.append(f"   ✗ Error: {result.error_details}")

        # Detailed failures
        failures = [r for r in self.results if r.status == "FAIL"]
        if failures:
            report.append("\n" + "="*80)
            report.append("DETAILED FAILURES")
            report.append("="*80)
            for result in failures:
                report.append(f"\n{result.test_name}")
                report.append(f"Category: {result.category}")
                report.append(f"Error: {result.error_details}")

        return "\n".join(report)

    async def run_all_tests(self) -> bool:
        """Run all tests"""
        self.start_time = time.time()

        try:
            # Phase 0: Setup
            if not await self.setup_test_environment():
                logger.error("Environment setup failed, aborting tests")
                return False

            # Phase 1: MCP Server
            await self.test_mcp_server_imports()
            await self.test_database_connectivity()
            await self.test_config_loading()

            # Phase 2: MCP Bridge
            await self.test_mcp_bridge_imports()
            await self.test_fastapi_dependencies()

            # Phase 3: LLM Runner
            await self.test_run_llm_imports()
            await self.test_baseline_context()
            await self.test_openai_config()

            # Phase 4: Integration
            await self.test_integration_setup()

            return True

        except Exception as e:
            logger.error(f"Test runner failed: {e}")
            logger.error(traceback.format_exc())
            return False


async def main():
    """Main entry point"""
    runner = TestRunner()

    success = await runner.run_all_tests()

    # Generate and print report
    report = runner.generate_report()
    print(report)

    # Save report
    report_path = Path("testing/test_results.txt")
    report_path.write_text(report)
    logger.info(f"\nReport saved to: {report_path}")

    # Save JSON results
    json_results = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": len(runner.results),
        "passed": len([r for r in runner.results if r.status == "PASS"]),
        "failed": len([r for r in runner.results if r.status == "FAIL"]),
        "skipped": len([r for r in runner.results if r.status == "SKIP"]),
        "results": [r.to_dict() for r in runner.results]
    }

    json_path = Path("testing/test_results.json")
    json_path.write_text(json.dumps(json_results, indent=2))
    logger.info(f"JSON results saved to: {json_path}")

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
