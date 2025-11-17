#!/usr/bin/env python3
"""
Master EDGAR Data Processing Script

This script provides a complete pipeline for processing all EDGAR v2024 sectors:
- Transport
- Power Industry
- Agriculture
- Waste
- Buildings
- Fuel Exploitation
- Industrial Combustion
- Industrial Processes

Usage:
    # Process all sectors
    python process_edgar_complete.py

    # Process specific sectors
    python process_edgar_complete.py --sectors transport power-industry

    # Process by priority (high priority sectors first)
    python process_edgar_complete.py --by-priority

    # Dry run (check configuration without processing)
    python process_edgar_complete.py --dry-run
"""

import sys
from pathlib import Path
import argparse
import logging
from datetime import datetime

# Add scripts/preprocessing to path
sys.path.insert(0, str(Path(__file__).parent / "scripts" / "preprocessing"))

from sector_config import SECTORS
from process_all_sectors import process_sector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_banner():
    """Print welcome banner."""
    print("\n" + "="*80)
    print(" "*20 + "EDGAR v2024 Complete Data Processing Pipeline")
    print("="*80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Sectors Available: {len(SECTORS)}")
    print("="*80 + "\n")


def list_sectors():
    """List all available sectors with details."""
    print("\n" + "="*80)
    print("AVAILABLE SECTORS")
    print("="*80 + "\n")

    # Group by priority
    by_priority = {}
    for sector_id, config in SECTORS.items():
        priority = config.get('priority', 3)
        if priority not in by_priority:
            by_priority[priority] = []
        by_priority[priority].append((sector_id, config))

    for priority in sorted(by_priority.keys()):
        priority_name = {1: "HIGH", 2: "MEDIUM", 3: "LOW"}[priority]
        print(f"\n{priority_name} PRIORITY:")
        print("-" * 80)

        for sector_id, config in sorted(by_priority[priority]):
            print(f"\n  {sector_id}")
            print(f"    Name: {config['name']}")
            print(f"    Code: {config['edgar_code']}")
            print(f"    Description: {config['description']}")
            print(f"    Time Range: {config['time_range'][0]}-{config['time_range'][1]}")
            if config['subsectors']:
                print(f"    Subsectors: {', '.join(config['subsectors'])}")

    print("\n" + "="*80 + "\n")


def dry_run(sectors_to_process, raw_data_dir, output_dir):
    """Perform dry run - check configuration without processing."""
    print("\n" + "="*80)
    print("DRY RUN - Configuration Check")
    print("="*80 + "\n")

    print(f"Raw Data Directory: {raw_data_dir}")
    print(f"Output Directory: {output_dir}")
    print(f"Sectors to Process: {len(sectors_to_process)}\n")

    issues = []

    for sector in sectors_to_process:
        print(f"Checking {sector}...")

        sector_raw_path = raw_data_dir / sector
        if not sector_raw_path.exists():
            issues.append(f"  ✗ Raw data not found: {sector_raw_path}")
            print(f"  ✗ Raw data directory missing")
        else:
            # Count NetCDF files
            nc_files = list(sector_raw_path.glob("*.nc"))
            print(f"  ✓ Raw data found ({len(nc_files)} NetCDF files)")

    if issues:
        print("\n" + "="*80)
        print("ISSUES FOUND:")
        print("="*80)
        for issue in issues:
            print(issue)
        print("\nFix these issues before running the actual processing.")
        return False
    else:
        print("\n" + "="*80)
        print("✓ All checks passed! Ready to process.")
        print("="*80)
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="EDGAR v2024 Complete Data Processing Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all sectors
  python process_edgar_complete.py

  # Process specific sectors
  python process_edgar_complete.py --sectors transport agriculture

  # Process high priority sectors only
  python process_edgar_complete.py --by-priority --max-priority 1

  # Dry run to check configuration
  python process_edgar_complete.py --dry-run

  # List all available sectors
  python process_edgar_complete.py --list
        """
    )

    parser.add_argument(
        '--raw-data-dir',
        type=Path,
        default=Path('data/raw'),
        help='Base directory containing raw sector data (default: data/raw)'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('data/curated-2'),
        help='Output directory for processed files (default: data/curated-2)'
    )
    parser.add_argument(
        '--sectors',
        nargs='+',
        choices=list(SECTORS.keys()),
        help='Specific sectors to process (default: all)'
    )
    parser.add_argument(
        '--by-priority',
        action='store_true',
        help='Process sectors in priority order (high to low)'
    )
    parser.add_argument(
        '--max-priority',
        type=int,
        choices=[1, 2, 3],
        help='Only process sectors up to this priority level'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available sectors and exit'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Check configuration without actually processing'
    )

    args = parser.parse_args()

    # List sectors and exit
    if args.list:
        list_sectors()
        return

    print_banner()

    # Determine which sectors to process
    if args.sectors:
        sectors_to_process = args.sectors
    else:
        sectors_to_process = list(SECTORS.keys())

    # Filter by priority if requested
    if args.max_priority:
        sectors_to_process = [
            s for s in sectors_to_process
            if SECTORS[s].get('priority', 3) <= args.max_priority
        ]

    # Sort by priority if requested
    if args.by_priority:
        sectors_to_process = sorted(
            sectors_to_process,
            key=lambda s: SECTORS[s].get('priority', 3)
        )

    logger.info(f"Sectors to process: {', '.join(sectors_to_process)}")

    # Dry run
    if args.dry_run:
        if dry_run(sectors_to_process, args.raw_data_dir, args.output_dir):
            print("\nTo run actual processing, remove the --dry-run flag.")
        return

    # Process each sector
    print("\n" + "="*80)
    print("STARTING PROCESSING")
    print("="*80 + "\n")

    results = {}
    for i, sector in enumerate(sectors_to_process, 1):
        print(f"\n[{i}/{len(sectors_to_process)}] Processing {sector}...")
        result = process_sector(sector, args.raw_data_dir, args.output_dir)
        if result:
            results[sector] = result

    # Final summary
    print("\n" + "="*80)
    print("PROCESSING COMPLETE")
    print("="*80)
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nSuccessfully processed: {len(results)}/{len(sectors_to_process)} sectors\n")

    for sector, files in results.items():
        priority = SECTORS[sector].get('priority', 3)
        priority_icon = {1: "🔴", 2: "🟡", 3: "🟢"}[priority]
        print(f"{priority_icon} {sector}: {len(files)} output files")

    if len(results) < len(sectors_to_process):
        failed = set(sectors_to_process) - set(results.keys())
        print(f"\n⚠️  Failed sectors: {', '.join(failed)}")
        print("Check logs above for error details.")

    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
