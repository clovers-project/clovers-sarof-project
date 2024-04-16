import time


def remove_tag(buff_list: list[str], tag: str):
    n = 0
    old_buff_list = buff_list.copy()
    buff_list.clear()
    for x in old_buff_list:
        if x == tag:
            n += 1
        else:
            buff_list.append(x)
    return n
