from collections.abc import Iterable
from datetime import datetime
from io import BytesIO
from PIL import Image, ImageDraw
from linecard import Linecard, ImageList
from matplotlib.font_manager import FontProperties
import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd
import numpy as np
from .tools import format_number
from .account import Stock, Item
from ._config import __config__

linecard = Linecard(__config__.fontname, __config__.fallback_fonts, (30, 40, 60))
plt.rcParams["font.family"] = FontProperties(fname=linecard.font_path).get_name()
plt.rcParams["font.sans-serif"] = [FontProperties(fname=path).get_name() for path in linecard.fallback_paths]

_ = linecard.get_font(linecard.font_path, 40)
assert _ is not None
FONT_DEFAULT, _ = _


def text_to_image(text: str, font_size=40, width=880, **kwargs):
    return linecard(text, font_size=font_size, width=width, **kwargs)


def card_template(text: str, tip: str, font_size=40, width=880, **kwargs):
    return linecard(f"{text}\n----\n[right][font color=grey,size=30]{tip}", font_size=font_size, width=width, **kwargs)


def item_info(data: list[tuple[Item, int]]):
    data.sort(key=lambda x: x[0].rare)

    def result(item: Item, n: int):
        quant = "个" if item.timeliness == 1 else "天"
        return (
            f"[font size=60,color={item.color}]【{item.name}】[right]{format_number(n)}{quant}\n"
            f"----\n{item.intro.replace('\n','[passport]\n')}"
            f"\n[right]{item.tip.replace('\n','[passport]\n')}"
        ).rstrip("\n")

    return [linecard(result(*args), 30, width=880, autowrap=True) for args in data]


def item_card(data: list[tuple[Item, int]]):
    data.sort(key=lambda x: x[0].rare)

    def result(item: Item, n: int):
        quant = "个" if item.timeliness == 1 else "天"
        return f"[font color={item.color}]{item.name}[pixel 350]{item.rare*'☆'}[right]{format_number(n)}{quant}"

    return "\n".join(result(*args) for args in data)


def stock_card(data: list[tuple[Stock, int]]):
    def result(stock: Stock, n: int):
        buy = format_number(stock.price)
        sell = format_number(stock.value / stock.issuance) if stock.issuance else "--"
        return (
            f"[pixel 20]{stock.name}\n"
            f"[pixel 20][font color=black]数量 [font color={'green' if n else 'red'}]{n}"
            f"[pixel 280][font color=black]购买 [font color={'red' if buy > sell else 'green'}]{buy}"
            f"[pixel 580][font color=black]结算 [font color=green]{sell}"
        )

    return "\n".join(result(*args) for args in data)


CIRCLE_260_MASK = Image.new("RGBA", (260, 260), (255, 255, 255, 0))
ImageDraw.Draw(CIRCLE_260_MASK).ellipse(((0, 0), (260, 260)), fill="black")


def avatar_card(avatar: bytes | None, nickname: str, lines: list[str] | None = None):
    # assert len(lines) <= 3
    canvas = Image.new("RGBA", (880, 300))
    if avatar:
        canvas.paste(Image.open(BytesIO(avatar)).resize((260, 260)), (20, 20), CIRCLE_260_MASK)
    draw = ImageDraw.Draw(canvas)
    canvas.paste(linecard(nickname, 40, width=580, padding=(0, 10)), (300, 40))
    draw.line(((300, 120), (860, 120)), fill="gray", width=4)
    if lines is None:
        return canvas
    for n, line in enumerate(lines):
        draw.text((300, 140 + n * 50), "•", fill="gray", font=FONT_DEFAULT)
        draw.text((840, 140 + n * 50), "•", fill="gray", font=FONT_DEFAULT)
        x = 340
        for char in line:
            draw.text((x, 140 + n * 50), char, fill="gray", font=FONT_DEFAULT)
            x += 40
    return canvas


def candlestick(figsize: tuple[float, float], length: int, history: list[tuple[float, float]]):
    """
    生成股价K线图
        figsize:图片尺寸
        length:OHLC采样长度
        history:历史数据
    """
    t, price = zip(*history)
    l = len(t)
    t = [t[i : i + length] for i in range(0, l, length)]
    price = [price[i : i + length] for i in range(0, l, length)]
    D, O, H, L, C = [], [], [], [], []
    for i in range(len(price)):
        D.append(datetime.fromtimestamp(t[i][0]))
        O.append(price[i][0])
        H.append(max(price[i]))
        L.append(min(price[i]))
        C.append(price[i][-1])
    data = pd.DataFrame({"date": D, "open": O, "high": H, "low": L, "close": C})
    data = data.set_index("date")
    style = mpf.make_mpf_style(
        base_mpf_style="charles",
        marketcolors=mpf.make_marketcolors(up="#33CC66", down="#CC3366", edge="none"),
        y_on_right=False,
        facecolor="#FFFFFFAA",
        figcolor="none",
    )
    output = BytesIO()
    mpf.plot(
        data,
        type="candlestick",
        xlabel="",
        ylabel="",
        datetime_format="%H:%M",
        tight_layout=True,
        style=style,
        figsize=figsize,
        savefig=output,
    )
    return Image.open(output)


def dist_card(
    dist: list[tuple[int, str]],
    colors=[
        "#351c75",
        "#0b5394",
        "#1155cc",
        "#134f5c",
        "#38761d",
        "#bf9000",
        "#b45f06",
        "#990000",
        "#741b47",
    ],
):
    dist.sort(key=lambda x: x[0], reverse=True)
    labels = []
    x = []
    sum_value = sum(d[0] for d in dist)
    limit = 0.01 * sum_value
    for n, (value, name) in enumerate(dist):
        if n < 8 and value > limit:
            x.append(value)
            labels.append(name)
        else:
            labels.append("其他")
            x.append(sum(seg[0] for seg in dist[n:]))
            break
    n += 1
    output = BytesIO()

    plt.figure(figsize=(6.6, 3.4))
    plt.pie(
        np.array(x),
        labels=[""] * n,
        autopct=lambda pct: "" if pct < 1 else f"{pct:.1f}%",
        colors=colors[0:n],
        wedgeprops={"edgecolor": "none"},
        textprops={"fontsize": 15},
        pctdistance=1.2,
        explode=[0, 0.1, 0.19, 0.27, 0.34, 0.40, 0.45, 0.49, 0.52][0:n],
    )
    plt.legend(labels, loc=(-0.6, 0), frameon=False)
    plt.axis("equal")
    plt.subplots_adjust(top=0.95, bottom=0.05, left=0.4, hspace=0, wspace=0)
    plt.savefig(output, format="png", dpi=100, transparent=True)
    plt.close()
    canvas = Image.new("RGBA", (880, 340))
    canvas.paste(Image.open(output), (220, 0))
    return canvas


CIRCLE_60_MASK = Image.new("RGBA", (60, 60), (255, 255, 255, 0))
ImageDraw.Draw(CIRCLE_60_MASK).ellipse(((0, 0), (60, 60)), fill="black")


def avatar_list(data: Iterable[tuple[bytes | None, str]]) -> ImageList:
    image_list = []
    for avatar, text in data:
        canvas = linecard(f"[pixel 70]{text}", 40, width=880, height=70, padding=(0, 15))
        if avatar:
            canvas.paste(Image.open(BytesIO(avatar)).resize((60, 60)), (5, 5), CIRCLE_60_MASK)
        image_list.append(canvas)
    return image_list
