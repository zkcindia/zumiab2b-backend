from io import BytesIO

from PIL import Image as PILImage
from django.core.files.base import ContentFile


def compress_image(image_file):
    img = PILImage.open(image_file)

    # Handle transparency correctly
    if img.mode in ("RGBA", "LA", "P"):
        background = PILImage.new("RGB", img.size, "white")

        if img.mode == "P":
            img = img.convert("RGBA")

        if img.mode == "RGBA":
            background.paste(
                img,
                mask=img.getchannel("A")
            )
        else:
            background.paste(img)

        img = background

    else:
        img = img.convert("RGB")

    # Don't allow extremely large images
    max_width = 1600
    max_height = 1600

    img.thumbnail(
        (max_width, max_height),
        PILImage.Resampling.LANCZOS
    )

    output = BytesIO()

    img.save(
        output,
        format="WEBP",
        quality=82,
        method=6
    )

    output.seek(0)

    original_name = image_file.name

    filename = (
        original_name.rsplit(".", 1)[0]
        + ".webp"
    )

    return ContentFile(
        output.read(),
        name=filename
    )