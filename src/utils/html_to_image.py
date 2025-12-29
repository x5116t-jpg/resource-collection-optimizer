"""HTML to image conversion utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Optional


def convert_html_to_png(
    html_path: str,
    output_path: str,
    width: int = 1200,
    height: int = 900,
    wait_time: int = 2000
) -> None:
    """
    Convert HTML file to PNG image using Playwright.

    Args:
        html_path: Path to input HTML file
        output_path: Path to output PNG file
        width: Image width in pixels
        height: Image height in pixels
        wait_time: Wait time for rendering in milliseconds

    Raises:
        ImportError: If playwright is not installed
        FileNotFoundError: If html_path does not exist
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise ImportError(
            "playwright is required for HTML to image conversion.\n"
            "Install with: pip install playwright && playwright install chromium"
        )

    html_path_obj = Path(html_path).resolve()
    if not html_path_obj.exists():
        raise FileNotFoundError(f"HTML file not found: {html_path}")

    output_path_obj = Path(output_path).resolve()
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": height})

        # Load HTML file
        page.goto(f"file://{html_path_obj}")

        # Wait for map rendering to complete
        page.wait_for_timeout(wait_time)

        # Take screenshot
        page.screenshot(path=str(output_path_obj), full_page=False)

        browser.close()


def convert_html_to_pdf(
    html_path: str,
    output_path: str,
    width: int = 1200,
    height: int = 900,
    wait_time: int = 2000
) -> None:
    """
    Convert HTML file to PDF using Playwright.

    Args:
        html_path: Path to input HTML file
        output_path: Path to output PDF file
        width: Page width in pixels
        height: Page height in pixels
        wait_time: Wait time for rendering in milliseconds

    Raises:
        ImportError: If playwright is not installed
        FileNotFoundError: If html_path does not exist
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise ImportError(
            "playwright is required for HTML to PDF conversion.\n"
            "Install with: pip install playwright && playwright install chromium"
        )

    html_path_obj = Path(html_path).resolve()
    if not html_path_obj.exists():
        raise FileNotFoundError(f"HTML file not found: {html_path}")

    output_path_obj = Path(output_path).resolve()
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": height})

        # Load HTML file
        page.goto(f"file://{html_path_obj}")

        # Wait for map rendering to complete
        page.wait_for_timeout(wait_time)

        # Generate PDF
        page.pdf(
            path=str(output_path_obj),
            width=f"{width}px",
            height=f"{height}px",
            print_background=True
        )

        browser.close()
