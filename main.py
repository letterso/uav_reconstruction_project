from __future__ import annotations

import logging
from pathlib import Path

import click

from video_sampler.config import load_config
from video_sampler.extract_frames import sample_video


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--video", required=True, type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--config",
    default="config/video_sampler.yaml",
    show_default=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Path to YAML config",
)
@click.option(
    "--output",
    default=None,
    type=click.Path(file_okay=False),
    help="Override output directory (default: from config)",
)
@click.option(
    "--start-time",
    default=None,
    type=float,
    help="Start time in seconds (default: from config)",
)
@click.option(
    "--end-time",
    default=None,
    type=float,
    help="End time in seconds (default: from config)",
)
@click.option(
    "--log-level",
    default="INFO",
    show_default=True,
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    help="Logging level",
)
def main(
    video: str,
    config: str,
    output: str | None,
    start_time: float | None,
    end_time: float | None,
    log_level: str,
) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="[%(levelname)s] %(message)s",
    )

    config_data = load_config(config)
    if start_time is not None:
        config_data["sampling"]["start_time"] = start_time
    if end_time is not None:
        config_data["sampling"]["end_time"] = end_time

    output_dir = output or config_data["sampling"]["output_dir"]

    stats, output_path = sample_video(
        video_path=Path(video),
        output_dir=output_dir,
        config=config_data,
    )

    logging.info("Done. Output: %s", output_path)
    logging.info("Stats: %s", stats.summary())


if __name__ == "__main__":
    main()
