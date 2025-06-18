from io import BytesIO
from PIL import Image, ImageDraw
from clovers_sarof.core.linecard import FONT_DEFAULT, CIRCLE_60_MASK
from clovers_sarof.core.tools import format_number


def draw_rank(data: list[tuple[bytes | None, str, int]], fill="#00000066"):
    """
    排名信息
    """
    first = data[0][-1]
    canvas = Image.new("RGBA", (880, 80 * len(data) + 20))
    draw = ImageDraw.Draw(canvas)
    y = 20
    for i, (avatar, nickname, v) in enumerate(data, start=1):
        if avatar:
            canvas.paste(Image.open(BytesIO(avatar)).resize((60, 60)), (5, y), CIRCLE_60_MASK)
        draw.rectangle(((70, y + 10), (70 + int(v / first * 790), y + 50)), fill=fill)
        draw.text((80, y + 10), f"{i}.{nickname} {format_number(v)}", fill=(255, 255, 255), font=FONT_DEFAULT)
        y += 80
    return canvas
