#!/usr/bin/env python3
"""
Buildings Sector Preprocessing Pipeline

Processes EDGAR v2024 Buildings sector emissions data:
- Residential and commercial building emissions
- Uses the same spatial aggregation pipeline as Transport
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from process_transport_sector import TransportProcessor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BuildingsProcessor(TransportProcessor):
    """Process Buildings sector emissions data."""

    def __init__(self):
        super().__init__(sector="buildings")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Process Buildings sector emissions")
    parser.add_argument(
        '--raw-data',
        type=Path,
        required=True,
        help='Path to raw NetCDF files'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('data/curated-2'),
        help='Output directory for processed files'
    )

    args = parser.parse_args()

    processor = BuildingsProcessor()
    output_files = processor.process(args.raw_data, args.output)

    print("\nOutput files:")
    for key, path in output_files.items():
        print(f"  {key}: {path}")


if __name__ == "__main__":
    main()
