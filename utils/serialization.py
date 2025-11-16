"""
Optimized serialization utilities for large datasets.
"""
import json
import gzip
from typing import Any, Iterator
import logging

logger = logging.getLogger(__name__)

# Threshold for using streaming serialization (number of rows)
STREAMING_THRESHOLD = 1000


def serialize_large_response(
    data: list[dict[str, Any]],
    compress: bool = False
) -> str | bytes:
    """
    Efficiently serialize large responses.

    For datasets >1000 rows, uses streaming JSON serialization.
    Optionally compresses result with gzip.

    Args:
        data: List of data dictionaries
        compress: Whether to gzip compress the result

    Returns:
        JSON string or compressed bytes
    """
    if len(data) < STREAMING_THRESHOLD:
        # Small dataset: use standard json.dumps
        json_str = json.dumps(data, separators=(',', ':'))  # Compact format
    else:
        # Large dataset: use streaming
        logger.info(f"Using streaming serialization for {len(data)} rows")
        json_str = stream_json_array(data)

    if compress:
        # Compress with gzip (typically 70-90% size reduction)
        compressed = gzip.compress(json_str.encode('utf-8'))
        compression_ratio = len(compressed) / len(json_str) * 100
        logger.info(f"Compressed {len(json_str)} bytes to {len(compressed)} bytes ({compression_ratio:.1f}%)")
        return compressed

    return json_str


def stream_json_array(items: list[dict[str, Any]]) -> str:
    """
    Stream-serialize JSON array without loading all in memory.

    More memory-efficient for large arrays.

    Args:
        items: List of items to serialize

    Returns:
        JSON string
    """
    parts = ['[']

    for i, item in enumerate(items):
        if i > 0:
            parts.append(',')
        parts.append(json.dumps(item, separators=(',', ':')))

    parts.append(']')
    return ''.join(parts)


def chunk_large_response(
    data: list[dict[str, Any]],
    chunk_size: int = 1000
) -> Iterator[list[dict[str, Any]]]:
    """
    Split large response into chunks for pagination.

    Args:
        data: Full dataset
        chunk_size: Rows per chunk

    Yields:
        Chunks of data
    """
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]


def create_paginated_response(
    data: list[dict[str, Any]],
    page: int = 1,
    page_size: int = 1000
) -> dict[str, Any]:
    """
    Create paginated response from large dataset.

    Args:
        data: Full dataset
        page: Page number (1-indexed)
        page_size: Rows per page

    Returns:
        Paginated response with metadata
    """
    total_rows = len(data)
    total_pages = (total_rows + page_size - 1) // page_size  # Ceiling division

    # Validate page number
    if page < 1:
        page = 1
    if page > total_pages and total_pages > 0:
        page = total_pages

    # Calculate slice indices
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total_rows)

    # Extract page data
    page_data = data[start_idx:end_idx]

    return {
        "data": page_data,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_rows": total_rows,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }


def estimate_response_size(data: list[dict[str, Any]]) -> int:
    """
    Estimate size of response in bytes (without actually serializing).

    Uses sampling for large datasets.

    Args:
        data: Dataset to estimate

    Returns:
        Estimated size in bytes
    """
    if not data:
        return 0

    # Sample first few rows to estimate average row size
    sample_size = min(10, len(data))
    sample = data[:sample_size]

    # Serialize sample
    sample_json = json.dumps(sample, separators=(',', ':'))
    sample_bytes = len(sample_json.encode('utf-8'))

    # Estimate total size
    avg_row_size = sample_bytes / sample_size
    estimated_total = int(avg_row_size * len(data))

    return estimated_total


def should_compress_response(data: list[dict[str, Any]], threshold_mb: float = 1.0) -> bool:
    """
    Determine if response should be compressed based on size.

    Args:
        data: Dataset
        threshold_mb: Size threshold in megabytes

    Returns:
        True if response should be compressed
    """
    estimated_size = estimate_response_size(data)
    threshold_bytes = threshold_mb * 1024 * 1024

    return estimated_size > threshold_bytes
