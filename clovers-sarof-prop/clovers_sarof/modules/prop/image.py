import numpy as np
from clovers_sarof.core.linecard import card_template

curve_fit = {
    1: lambda x: 0.4051548792879075 * np.log(1.5220797359057374 * x) + -0.0020201103448929322 * x + -1.0258025707645715,
    2: lambda x: 0.2091504808791389 * np.log(1.101707968990964e-14 * x) + -0.0009065271163526587 * x + 6.81737635995572,
    3: lambda x: 0.13706213955909696 * np.log(739.4329972067283 * x) + -0.0007205797484775894 * x + -0.395220181962607,
    4: lambda x: -0.10977545924670605 * np.log(5.0664130329281946e-15 * x) + 0.0004868571908065122 * x + -1.8622074263416735,
    5: lambda x: -0.24869846144440189 * np.log(297.60014651115324 * x) + 0.0012632334635791975 * x + 3.8330390561576926,
    6: lambda x: -0.5086236385670387 * np.log(3.240687588979718e-13 * x) + 0.002785268129815752 * x + -10.987495694881874,
}


def report_card(
    nickname: str,
    prop_star: int,
    prop_n: int,
    air_star: int,
    air_n: int,
):
    N = prop_n + air_n
    pt = prop_star / N
    title = []

    if not prop_n:
        title.append("[center][font color=#003300]理 想 气 体")
    elif pt < curve_fit[1](N):
        title.append("[center][font color=#003300]很多空气")
    elif pt < curve_fit[2](N):
        title.append("[left][font color=#003333]☆[center]数据异常[right]☆")
    elif pt < curve_fit[3](N):
        title.append("[left][font color=#003366]☆ ☆[center]一枚硬币[right]☆ ☆")
    elif pt < curve_fit[4](N):
        title.append("[left][font color=#003399]☆ ☆ ☆[center]高斯分布[right]☆ ☆ ☆")
    elif pt < curve_fit[5](N):
        title.append("[left][font color=#0033CC]☆ ☆ ☆ ☆[center]对称破缺[right]☆ ☆ ☆ ☆")
    elif pt < curve_fit[6](N):
        title.append("[left][font color=#0033FF]☆ ☆ ☆ ☆ ☆[center]概率之子[right]☆ ☆ ☆ ☆ ☆")
    else:
        title.append("[center][font color=#FF0000]☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆")
    title.append(
        "----\n"
        f"抽卡次数 {N}[pixel 450]空气占比 {round(air_n*100/N,2)}%\n"
        f"获得☆ {prop_star}[pixel 450]获得☆ {air_star}\n"
        f"平均☆ {round(prop_star/(prop_n or 1),3)}[pixel 450]平均☆ {round(air_star/(air_n or 1),3)}\n"
        f"数据来源：{nickname}"
    )
    return card_template("\n".join(title), "抽卡报告")
