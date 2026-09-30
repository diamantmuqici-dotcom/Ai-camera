"""Create the Windows executable icon at packaging time (Pillow is build-only)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

size = 256
img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
draw.rounded_rectangle((5, 5, 250, 250), radius=52, fill="#17292B")
draw.ellipse((42, 42, 214, 214), fill="#B8F7C8")
draw.ellipse((77, 77, 179, 179), fill="#17292B")
try:
    font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 27)
except OSError:
    font = ImageFont.load_default()
draw.text((151, 190), "V2", fill="#B8F7C8", font=font)
path = Path(__file__).resolve().parents[1] / "assets" / "clarity.ico"
path.parent.mkdir(parents=True, exist_ok=True)
img.save(path, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(f"Created {path}")
