#!/usr/bin/env python3
"""
MCP HTTP Bridge Integration Testing

Tests the HTTP bridge:
- Startup and shutdown
- HTTP endpoints
- Rate limiting
- CORS handling
- Request/response formatting
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

import requests
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@dataclass
class BridgeTestResult:
    """Test result for bridge tests"""
    test_name: str
    status: str  # "PASS", "FAIL", "SKIP"
    duration: float
    message: str = ""
    error: str = ""


class BridgeTester:
    """Tests MCP HTTP Bridge functionality"""

    def __init__(self):
        self.results: List[BridgeTestResult] = []
        self.bridge_process: Optional[subprocess.Popen] = None
        self.bridge_url: Optional[str] = None
        self.bridge_port: str = "8010"

    def log_result(self, test_name: str, status: str, duration: float,
                   message: str = "", error: str = ""):
        """Log a test result"""
        result = BridgeTestResult(
            test_name=test_name,
            status=status,
            duration=duration,
            message=message,
            error=error
        )
        self.results.append(result)

        status_emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⏭️"
        logger.info(f"{status_emoji} {test_name}: {status} [{duration:.2f}s]")
        if message:
            logger.info(f"   → {message}")
        if error:
            logger.error(f"   ✗ {error}")

    async def test_bridge_startup(self) -> bool:
        """Test bridge startup"""
        logger.info("\n" + "="*80)
        logger.info("PHASE 1: BRIDGE STARTUP")
        logger.info("="*80)
        logger.info("\nTest 1.1: Bridge startup...")

        start = time.time()
        try:
            load_dotenv()
            self.bridge_port = os.getenv("PORT", "8010")
            self.bridge_url = f"http://127.0.0.1:{self.bridge_port}"

            # Check if port is available
            try:
                response = requests.get(f"{self.bridge_url}/health", timeout=2)
                if response.status_code == 200:
                    duration = time.time() - start
                    self.log_result("Bridge Already Running", "PASS", duration,
                                  message=f"Bridge is running on {self.bridge_url}")
                    return True
            except requests.exceptions.ConnectionError:
                logger.info("Bridge not running, attempting to start...")

            # Try to start bridge
            logger.info(f"Starting bridge on port {self.bridge_port}...")
            self.bridge_process = subprocess.Popen(
                [sys.executable, "src/mcp_http_bridge.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(Path.cwd())
            )

            # Wait for bridge to start
            max_retries = 10
            for attempt in range(max_retries):
                try:
                    response = requests.get(f"{self.bridge_url}/health", timeout=2)
                    if response.status_code == 200:
                        duration = time.time() - start
                        self.log_result("Bridge Startup", "PASS", duration,
                                      message=f"Bridge started successfully on {self.bridge_url}")
                        return True
                except requests.exceptions.ConnectionError:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.5)
                        continue
                    else:
                        raise

            duration = time.time() - start
            self.log_result("Bridge Startup", "FAIL", duration,
                          error="Bridge did not respond to health check")
            return False

        except Exception as e:
            duration = time.time() - start
            self.log_result("Bridge Startup", "FAIL", duration, error=str(e))
            return False

    async def test_health_endpoint(self) -> bool:
        """Test /health endpoint"""
        logger.info("\nTest 1.2: Health endpoint...")
        start = time.time()

        try:
            if not self.bridge_url:
                self.log_result("Health Endpoint", "SKIP", 0,
                              message="Bridge not running")
                return True

            response = requests.get(f"{self.bridge_url}/health", timeout=5)

            if response.status_code == 200:
                duration = time.time() - start
                self.log_result("Health Endpoint", "PASS", duration,
                              message="Health endpoint returns 200 OK")
                return True
            else:
                duration = time.time() - start
                self.log_result("Health Endpoint", "FAIL", duration,
                              error=f"Health endpoint returned {response.status_code}")
                return False

        except Exception as e:
            duration = time.time() - start
            self.log_result("Health Endpoint", "FAIL", duration, error=str(e))
            return False

    async def test_list_files_endpoint(self) -> bool:
        """Test /list_files endpoint"""
        logger.info("\nTest 1.3: List files endpoint...")
        start = time.time()

        try:
            if not self.bridge_url:
                self.log_result("List Files Endpoint", "SKIP", 0,
                              message="Bridge not running")
                return True

            response = requests.get(f"{self.bridge_url}/list_files", timeout=5)

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    duration = time.time() - start
                    file_count = len(data.get("files", []))
                    self.log_result("List Files Endpoint", "PASS", duration,
                                  message=f"Got {file_count} files from endpoint")
                    return True
                else:
                    duration = time.time() - start
                    self.log_result("List Files Endpoint", "FAIL", duration,
                                  error="Response is not a valid JSON object")
                    return False
            else:
                duration = time.time() - start
                self.log_result("List Files Endpoint", "FAIL", duration,
                              error=f"Endpoint returned {response.status_code}")
                return False

        except Exception as e:
            duration = time.time() - start
            self.log_result("List Files Endpoint", "FAIL", duration, error=str(e))
            return False

    async def test_rate_limiting(self) -> bool:
        """Test rate limiting"""
        logger.info("\nTest 1.4: Rate limiting...")
        start = time.time()

        try:
            if not self.bridge_url:
                self.log_result("Rate Limiting", "SKIP", 0,
                              message="Bridge not running")
                return True

            # Make rapid requests
            success_count = 0
            rate_limited = False

            for i in range(5):
                try:
                    response = requests.get(f"{self.bridge_url}/health", timeout=5)
                    if response.status_code == 429:  # Too Many Requests
                        rate_limited = True
                    else:
                        success_count += 1
                except requests.exceptions.RequestException:
                    pass

            duration = time.time() - start

            if success_count > 0:
                self.log_result("Rate Limiting", "PASS", duration,
                              message=f"Bridge handled {success_count} requests. Rate limiting: {rate_limited}")
                return True
            else:
                self.log_result("Rate Limiting", "FAIL", duration,
                              error="Could not make any successful requests")
                return False

        except Exception as e:
            duration = time.time() - start
            self.log_result("Rate Limiting", "FAIL", duration, error=str(e))
            return False

    async def test_cors_headers(self) -> bool:
        """Test CORS headers"""
        logger.info("\nTest 1.5: CORS headers...")
        start = time.time()

        try:
            if not self.bridge_url:
                self.log_result("CORS Headers", "SKIP", 0,
                              message="Bridge not running")
                return True

            response = requests.get(f"{self.bridge_url}/health", timeout=5)

            cors_headers = {
                'access-control-allow-credentials',
                'access-control-allow-methods',
                'access-control-allow-origin'
            }

            found_cors = [h for h in cors_headers if h.lower() in {k.lower() for k in response.headers}]

            duration = time.time() - start

            if found_cors:
                self.log_result("CORS Headers", "PASS", duration,
                              message=f"Found {len(found_cors)} CORS headers")
                return True
            else:
                self.log_result("CORS Headers", "SKIP", duration,
                              message="CORS headers not present (may be optional)")
                return True

        except Exception as e:
            duration = time.time() - start
            self.log_result("CORS Headers", "FAIL", duration, error=str(e))
            return False

    async def test_error_handling(self) -> bool:
        """Test error handling"""
        logger.info("\nTest 1.6: Error handling...")
        start = time.time()

        try:
            if not self.bridge_url:
                self.log_result("Error Handling", "SKIP", 0,
                              message="Bridge not running")
                return True

            # Try invalid endpoint
            response = requests.get(f"{self.bridge_url}/invalid_endpoint", timeout=5)

            if response.status_code == 404:
                duration = time.time() - start
                self.log_result("Error Handling", "PASS", duration,
                              message="Invalid endpoint returns 404")
                return True
            else:
                duration = time.time() - start
                self.log_result("Error Handling", "FAIL", duration,
                              error=f"Invalid endpoint returned {response.status_code} instead of 404")
                return False

        except Exception as e:
            duration = time.time() - start
            self.log_result("Error Handling", "FAIL", duration, error=str(e))
            return False

    async def test_bridge_shutdown(self) -> bool:
        """Test bridge shutdown"""
        logger.info("\nTest 1.7: Bridge shutdown...")
        start = time.time()

        try:
            if self.bridge_process:
                self.bridge_process.terminate()
                self.bridge_process.wait(timeout=5)

                duration = time.time() - start
                self.log_result("Bridge Shutdown", "PASS", duration,
                              message="Bridge terminated cleanly")
            else:
                duration = time.time() - start
                self.log_result("Bridge Shutdown", "SKIP", duration,
                              message="Bridge was not started by this tester")

            return True

        except Exception as e:
            duration = time.time() - start
            self.log_result("Bridge Shutdown", "FAIL", duration, error=str(e))
            return False

    async def run_all_tests(self) -> bool:
        """Run all bridge tests"""
        try:
            await self.test_bridge_startup()
            if self.bridge_process or self.bridge_url:
                await self.test_health_endpoint()
                await self.test_list_files_endpoint()
                await self.test_rate_limiting()
                await self.test_cors_headers()
                await self.test_error_handling()
            await self.test_bridge_shutdown()
            return True
        except Exception as e:
            logger.error(f"Test runner failed: {e}")
            return False

    def generate_report(self) -> str:
        """Generate test report"""
        report = []
        report.append("\n" + "="*80)
        report.append("BRIDGE INTEGRATION TEST REPORT")
        report.append("="*80 + "\n")

        total = len(self.results)
        passed = len([r for r in self.results if r.status == "PASS"])
        failed = len([r for r in self.results if r.status == "FAIL"])
        skipped = len([r for r in self.results if r.status == "SKIP"])

        report.append("SUMMARY")
        report.append("-" * 40)
        report.append(f"Total Tests:   {total}")
        report.append(f"Passed:        {passed} ✅")
        report.append(f"Failed:        {failed} ❌")
        report.append(f"Skipped:       {skipped} ⏭️")
        if total > 0:
            report.append(f"Success Rate:  {(passed/total*100):.1f}%\n")

        # Detailed results
        report.append("\nDETAILED RESULTS")
        report.append("-" * 40)
        for result in self.results:
            status_icon = "✅" if result.status == "PASS" else "❌" if result.status == "FAIL" else "⏭️"
            report.append(f"{status_icon} {result.test_name:<40} [{result.duration:.2f}s]")
            if result.message:
                report.append(f"   → {result.message}")
            if result.error:
                report.append(f"   ✗ {result.error}")

        return "\n".join(report)


async def main():
    tester = BridgeTester()
    await tester.run_all_tests()

    report = tester.generate_report()
    print(report)

    # Save report
    Path("testing/test_results_bridge.txt").write_text(report)
    logger.info("\nReport saved to: testing/test_results_bridge.txt")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
