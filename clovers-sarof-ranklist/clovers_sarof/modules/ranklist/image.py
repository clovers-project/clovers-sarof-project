from io import BytesIO
from PIL import Image, ImageDraw
from clovers_sarof.core.linecard import FONT_DEFAULT, CIRCLE_60_MASK
from clovers_sarof.core.tools import format_number


def draw_rank(data: list[tuple[bytes | None, str, int]], fill="#FFFFFFAA"):
    """
    排名信息
    """
    first = data[0][-1]
    canvas = Image.new("RGBA", (880, 80 * len(data) + 20))
    draw = ImageDraw.Draw(canvas)
    y = 20
    for i, (avatar, nickname, v) in enumerate(data, start=1):
        if avatar:
            (avatar_image := Image.open(BytesIO(avatar)).resize((60, 60))).putalpha(CIRCLE_60_MASK)
            canvas.paste(avatar_image, (5, y))
        draw.rectangle(((70, y + 10), (70 + int(v / first * 790), y + 50)), fill=fill)
        draw.text((80, y + 10), f"{i}.{nickname} {format_number(v)}", fill=(0, 0, 0), font=FONT_DEFAULT)
        y += 80
    return canvas
