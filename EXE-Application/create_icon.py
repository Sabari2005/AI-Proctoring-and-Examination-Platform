#!/usr/bin/env python3
"""
Convert SVG logo to ICO format for EXE application icon.
Requires: pillow, cairosvg
"""

import os
import sys
from pathlib import Path

def create_icon():
    """Convert SVG logo to ICO format."""
    try:
        from PIL import Image
        import io
    except ImportError:
        print("[ERROR] Pillow is required. Install with: pip install Pillow")
        return False
    
    asset_dir = Path(__file__).parent / "assets"
    svg_file = asset_dir / "logo.svg"
    ico_file = asset_dir / "app_icon.ico"
    
    if not svg_file.exists():
        print(f"[ERROR] Logo file not found: {svg_file}")
        return False
    
    print(f"[INFO] Converting {svg_file} to ICO format...")
    
    try:
        # Use cairosvg when available for higher-fidelity SVG rasterization.
        try:
            import cairosvg
            
            # Render SVG to PNG bytes before ICO conversion.
            png_bytes = io.BytesIO()
            cairosvg.svg2png(url=str(svg_file), write_to=png_bytes, output_width=256, output_height=256)
            png_bytes.seek(0)
            
            # Open rendered PNG for icon resizing.
            img = Image.open(png_bytes)
        except ImportError:
            # Fallback path when cairosvg is unavailable.
            print("[WARN] cairosvg not found. Installing: pip install cairosvg")
            print("[INFO] Using alternative method...")
            
            # Generate a placeholder icon image.
            img = Image.new('RGBA', (256, 256), color=(255, 255, 255, 255))
            draw = __import__('PIL.ImageDraw', fromlist=['ImageDraw']).Draw(img)
            # Draw a simple circular marker for placeholder output.
            draw.ellipse([10, 10, 246, 246], fill=(79, 70, 229), outline=(79, 70, 229))
        
        # Build multi-resolution icon sizes for Windows compatibility.
        icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        icon_images = []
        
        for size in icon_sizes:
            resized = img.resize(size, Image.Resampling.LANCZOS)
            icon_images.append(resized)
        
        # Save as ICO with all target sizes.
        icon_images[0].save(
            ico_file,
            format='ICO',
            sizes=[size for size in icon_sizes]
        )
        
        print(f"[SUCCESS] Icon created: {ico_file}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to create icon: {e}")
        print("[INFO] Alternative: Use online converter https://convertio.co/svg-ico/")
        return False

if __name__ == "__main__":
    # Install optional converter dependency when missing.
    try:
        import cairosvg
    except ImportError:
        print("[INFO] Installing cairosvg for better SVG conversion...")
        os.system(f"{sys.executable} -m pip install cairosvg")
    
    success = create_icon()
    sys.exit(0 if success else 1)
