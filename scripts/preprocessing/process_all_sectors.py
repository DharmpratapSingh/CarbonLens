#!/usr/bin/env python3
"""
Process all EDGAR sectors.

Runs the preprocessing pipeline for all configured sectors.
"""

import logging
from pathlib import Path
import argparse
from typing import List

from sector_config import SECTORS, get_raw_data_path
from process_transport_sector import TransportProcessor
from process_power_sector import PowerProcessor
from process_agriculture_sector import AgricultureProcessor
from process_waste_sector import WasteProcessor
from process_buildings_sector import BuildingsProcessor
from process_fuel_exploitation_sector import FuelExploitationProcessor
from process_industrial_combustion_sector import IndustrialCombustionProcessor
from process_industrial_processes_sector import IndustrialProcessesProcessor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Processor mapping - All 8 EDGAR sectors
PROCESSORS = {
    "transport": TransportProcessor,
    "power-industry": PowerProcessor,
    "agriculture": AgricultureProcessor,
    "waste": WasteProcessor,
    "buildings": BuildingsProcessor,
    "fuel-exploitation": FuelExploitationProcessor,
    "industrial-combustion": IndustrialCombustionProcessor,
    "industrial-processes": IndustrialProcessesProcessor,
}


def process_sector(sector: str, raw_data_dir: Path, output_dir: Path):
    """Process a single sector."""
    if sector not in PROCESSORS:
        logger.warning(f"No processor available for sector: {sector}")
        return None

    logger.info(f"\n{'#'*70}")
    logger.info(f"# Processing Sector: {sector.upper()}")
    logger.info(f"{'#'*70}\n")

    processor_class = PROCESSORS[sector]
    processor = processor_class() if sector != "transport" else processor_class(sector=sector)

    sector_raw_path = raw_data_dir / sector
    if not sector_raw_path.exists():
        logger.error(f"Raw data directory not found: {sector_raw_path}")
        return None

    try:
        output_files = processor.process(sector_raw_path, output_dir)
        logger.info(f"✓ Successfully processed {sector}")
        return output_files
    except Exception as e:
        logger.error(f"✗ Failed to process {sector}: {e}", exc_info=True)
        return None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Process all EDGAR sectors")
    parser.add_argument(
        '--raw-data-dir',
        type=Path,
        default=Path('data/raw'),
        help='Base directory containing raw sector data'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('data/curated-2'),
        help='Output directory for processed files'
    )
    parser.add_argument(
        '--sectors',
        nargs='+',
        choices=list(SECTORS.keys()),
        help='Specific sectors to process (default: all)'
    )

    args = parser.parse_args()

    # Determine which sectors to process
    sectors_to_process = args.sectors if args.sectors else list(PROCESSORS.keys())

    logger.info(f"Processing {len(sectors_to_process)} sectors: {sectors_to_process}")

    # Process each sector
    results = {}
    for sector in sectors_to_process:
        result = process_sector(sector, args.raw_data_dir, args.output_dir)
        if result:
            results[sector] = result

    # Summary
    print("\n" + "="*70)
    print("PROCESSING SUMMARY")
    print("="*70)
    print(f"\nSuccessfully processed: {len(results)}/{len(sectors_to_process)} sectors")

    for sector, files in results.items():
        print(f"\n{sector}:")
        for key in files:
            print(f"  ✓ {key}")

    if len(results) < len(sectors_to_process):
        failed = set(sectors_to_process) - set(results.keys())
        print(f"\nFailed sectors: {failed}")


if __name__ == "__main__":
    main()
