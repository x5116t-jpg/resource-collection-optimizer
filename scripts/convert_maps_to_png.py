"""Manual script to convert route map HTML files to PNG."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def convert_all_maps():
    """Convert all HTML maps to PNG."""
    from utils.html_to_image import convert_html_to_png

    maps_dir = Path("claudedocs/report_export/maps")

    if not maps_dir.exists():
        print(f"Error: {maps_dir} not found")
        return

    # Find all HTML files
    html_files = list(maps_dir.glob("*.html"))

    if not html_files:
        print(f"No HTML files found in {maps_dir}")
        return

    print(f"Found {len(html_files)} HTML files to convert\n")

    for html_file in html_files:
        if "test" in html_file.name:
            print(f"Skipping test file: {html_file.name}")
            continue

        png_file = html_file.with_suffix(".png")

        print(f"Converting: {html_file.name}")
        print(f"  -> {png_file.name}")

        try:
            convert_html_to_png(
                str(html_file),
                str(png_file),
                width=1200,
                height=900,
                wait_time=3000  # 3 seconds for complex route maps
            )
            file_size = png_file.stat().st_size
            print(f"  OK: {file_size:,} bytes\n")

        except Exception as e:
            print(f"  ERROR: {e}\n")
            import traceback
            traceback.print_exc()

    print("\nConversion complete!")
    print(f"\nGenerated PNG files:")
    for png_file in sorted(maps_dir.glob("*.png")):
        if "test" not in png_file.name:
            size_kb = png_file.stat().st_size / 1024
            print(f"  - {png_file.name} ({size_kb:.1f} KB)")

if __name__ == "__main__":
    convert_all_maps()
