"""DJI SRT file parser for extracting GPS and altitude metadata."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


logger = logging.getLogger(__name__)


@dataclass
class SRTFrameMetadata:
    """Metadata for a single video frame from SRT."""

    frame_number: int
    timestamp_ms: int  # Timestamp in milliseconds
    latitude: float
    longitude: float
    rel_alt: float  # Relative altitude in meters
    abs_alt: float  # Absolute altitude in meters
    iso: Optional[int] = None
    shutter: Optional[str] = None


class SRTParser:
    """Parser for DJI SRT subtitle files."""

    def __init__(self, srt_path: str | Path):
        self.srt_path = Path(srt_path)
        self.metadata: Dict[int, SRTFrameMetadata] = {}
        self._parse()

    def _parse(self) -> None:
        """Parse the SRT file and extract metadata."""
        if not self.srt_path.exists():
            logger.warning("SRT file not found: %s", self.srt_path)
            return

        logger.info("Parsing SRT file: %s", self.srt_path)

        with open(self.srt_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Split by subtitle blocks (separated by double newline)
        blocks = re.split(r"\n\n+", content.strip())

        for block in blocks:
            metadata = self._parse_block(block)
            if metadata:
                self.metadata[metadata.frame_number] = metadata

        logger.info("Parsed %d frame metadata entries from SRT", len(self.metadata))

    def _parse_block(self, block: str) -> Optional[SRTFrameMetadata]:
        """Parse a single SRT subtitle block."""
        lines = block.strip().split("\n")
        if len(lines) < 3:
            return None

        try:
            # Line 1: Subtitle number
            subtitle_num = int(lines[0].strip())

            # Line 2: Timestamp
            timestamp_line = lines[1].strip()
            timestamp_ms = self._parse_timestamp(timestamp_line)

            # Line 3+: Metadata
            metadata_text = " ".join(lines[2:])

            # Extract frame count
            frame_match = re.search(r"FrameCnt:\s*(\d+)", metadata_text)
            if not frame_match:
                return None
            frame_number = int(frame_match.group(1))

            # Extract GPS coordinates
            lat_match = re.search(r"latitude:\s*([\d.-]+)", metadata_text)
            lon_match = re.search(r"longitude:\s*([\d.-]+)", metadata_text)

            if not lat_match or not lon_match:
                return None

            latitude = float(lat_match.group(1))
            longitude = float(lon_match.group(1))

            # Extract altitude
            rel_alt_match = re.search(r"rel_alt:\s*([\d.-]+)", metadata_text)
            abs_alt_match = re.search(r"abs_alt:\s*([\d.-]+)", metadata_text)

            rel_alt = float(rel_alt_match.group(1)) if rel_alt_match else 0.0
            abs_alt = float(abs_alt_match.group(1)) if abs_alt_match else 0.0

            # Extract camera settings (optional)
            iso_match = re.search(r"iso:\s*(\d+)", metadata_text)
            shutter_match = re.search(r"shutter:\s*([\d./]+)", metadata_text)

            iso = int(iso_match.group(1)) if iso_match else None
            shutter = shutter_match.group(1) if shutter_match else None

            return SRTFrameMetadata(
                frame_number=frame_number,
                timestamp_ms=timestamp_ms,
                latitude=latitude,
                longitude=longitude,
                rel_alt=rel_alt,
                abs_alt=abs_alt,
                iso=iso,
                shutter=shutter,
            )

        except (ValueError, IndexError, AttributeError) as e:
            logger.debug("Failed to parse SRT block: %s", e)
            return None

    def _parse_timestamp(self, timestamp_line: str) -> int:
        """Parse SRT timestamp and return start time in milliseconds."""
        # Format: "00:00:00,000 --> 00:00:00,016"
        start_time = timestamp_line.split("-->")[0].strip()
        # Parse HH:MM:SS,mmm
        time_match = re.match(r"(\d+):(\d+):(\d+)[,.](\d+)", start_time)
        if not time_match:
            return 0

        hours, minutes, seconds, milliseconds = map(int, time_match.groups())
        total_ms = (hours * 3600 + minutes * 60 + seconds) * 1000 + milliseconds
        return total_ms

    def get_metadata_by_frame(self, frame_number: int) -> Optional[SRTFrameMetadata]:
        """Get metadata for a specific frame number."""
        return self.metadata.get(frame_number)

    def get_metadata_by_timestamp(self, timestamp_sec: float) -> Optional[SRTFrameMetadata]:
        """Get metadata for the closest frame to a given timestamp (in seconds)."""
        timestamp_ms = int(timestamp_sec * 1000)

        # Find closest frame by timestamp
        closest_metadata = None
        min_diff = float("inf")

        for metadata in self.metadata.values():
            diff = abs(metadata.timestamp_ms - timestamp_ms)
            if diff < min_diff:
                min_diff = diff
                closest_metadata = metadata

        return closest_metadata

    def has_metadata(self) -> bool:
        """Check if any metadata was parsed."""
        return len(self.metadata) > 0


def find_srt_file(video_path: str | Path) -> Optional[Path]:
    """Find SRT file with the same name as the video file."""
    video_path = Path(video_path)
    srt_path = video_path.with_suffix(".SRT")

    # Try uppercase extension first
    if srt_path.exists():
        return srt_path

    # Try lowercase extension
    srt_path = video_path.with_suffix(".srt")
    if srt_path.exists():
        return srt_path

    return None
