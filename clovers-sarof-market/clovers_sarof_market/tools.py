import numpy as np


def gini_coef(wealths: list[int]) -> float:
    """
    计算基尼系数
    """
    wealths.sort()
    wealths.insert(0, 0)
    wealths_cum = np.cumsum(wealths)
    wealths_sum = wealths_cum[-1]
    N = len(wealths_cum)
    S = np.trapezoid(wealths_cum / wealths_sum, np.array(range(N)) / (N - 1))
    return 1 - 2 * S


def integer_log(number, base) -> int:
    return int(np.log(number) / np.log(base))
