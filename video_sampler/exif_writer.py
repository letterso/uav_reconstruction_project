"""Write GPS and altitude metadata to image EXIF."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import piexif
import cv2
import numpy as np

from .srt_parser import SRTFrameMetadata


logger = logging.getLogger(__name__)


def _decimal_to_dms(decimal: float) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
    """Convert decimal degrees to DMS (Degrees, Minutes, Seconds) format for EXIF.
    
    Returns tuple of (degrees, minutes, seconds) where each is (numerator, denominator).
    """
    is_negative = decimal < 0
    decimal = abs(decimal)
    
    degrees = int(decimal)
    minutes_decimal = (decimal - degrees) * 60
    minutes = int(minutes_decimal)
    seconds = (minutes_decimal - minutes) * 60
    
    # EXIF rational format: (numerator, denominator)
    # Use high precision for seconds (multiply by 10000)
    seconds_rational = (int(seconds * 10000), 10000)
    
    return ((degrees, 1), (minutes, 1), seconds_rational)


def _altitude_to_rational(altitude: float) -> tuple[int, int]:
    """Convert altitude to EXIF rational format.
    
    Returns (numerator, denominator) tuple.
    """
    # Use 3 decimal places precision
    return (int(abs(altitude) * 1000), 1000)


def write_image_with_exif(
    frame: np.ndarray,
    output_path: str | Path,
    metadata: Optional[SRTFrameMetadata] = None,
) -> None:
    """Write image with GPS EXIF data if metadata is provided.
    
    Args:
        frame: Image frame (BGR format from cv2)
        output_path: Path to save the image (will be saved as JPEG if metadata is provided)
        metadata: Optional SRT metadata containing GPS and altitude
    """
    output_path = Path(output_path)
    
    # If no metadata, write as-is
    if metadata is None:
        cv2.imwrite(str(output_path), frame)
        return
    
    # For EXIF support, we need JPEG format
    # Change extension to .jpg if metadata is provided
    if output_path.suffix.lower() in ['.png', '.bmp']:
        output_path = output_path.with_suffix('.jpg')
    
    try:
        # Build GPS IFD
        gps_ifd = {}
        
        # GPS version
        gps_ifd[piexif.GPSIFD.GPSVersionID] = (2, 3, 0, 0)
        
        # Latitude
        lat_dms = _decimal_to_dms(metadata.latitude)
        gps_ifd[piexif.GPSIFD.GPSLatitude] = lat_dms
        gps_ifd[piexif.GPSIFD.GPSLatitudeRef] = b'N' if metadata.latitude >= 0 else b'S'
        
        # Longitude
        lon_dms = _decimal_to_dms(metadata.longitude)
        gps_ifd[piexif.GPSIFD.GPSLongitude] = lon_dms
        gps_ifd[piexif.GPSIFD.GPSLongitudeRef] = b'E' if metadata.longitude >= 0 else b'W'
        
        # Altitude (relative altitude is more accurate for drone footage)
        altitude_rational = _altitude_to_rational(metadata.rel_alt)
        gps_ifd[piexif.GPSIFD.GPSAltitude] = altitude_rational
        gps_ifd[piexif.GPSIFD.GPSAltitudeRef] = 0 if metadata.rel_alt >= 0 else 1
        
        # Create EXIF dict
        exif_dict = {"0th": {}, "Exif": {}, "GPS": gps_ifd, "1st": {}, "thumbnail": None}
        
        # Optional: Add camera settings to EXIF if available
        if metadata.iso is not None:
            exif_dict["Exif"][piexif.ExifIFD.ISOSpeedRatings] = metadata.iso
        
        # Serialize EXIF
        exif_bytes = piexif.dump(exif_dict)
        
        # Write image first without EXIF
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 95]  # High quality JPEG
        cv2.imwrite(str(output_path), frame, encode_param)
        
        # Insert EXIF into the saved file
        piexif.insert(exif_bytes, str(output_path))
        
        logger.debug(
            "Wrote EXIF to %s: GPS=(%.6f, %.6f), Alt=%.2fm",
            output_path.name,
            metadata.latitude,
            metadata.longitude,
            metadata.rel_alt,
        )
        
    except Exception as e:
        logger.warning("Failed to write EXIF data to %s: %s", output_path, e)
        # Fallback: write without EXIF
        cv2.imwrite(str(output_path), frame)
