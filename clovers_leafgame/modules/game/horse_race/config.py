from pydantic import BaseModel


class Config(BaseModel):
    # 玩家人数范围
    range_of_player_numbers: tuple[int, int] = (2, 8)
    # 跑道长度
    setting_track_length: int = 30
    # 随机位置事件，能够随机到的跑道范围
    random_move_range: tuple[float, float] = (0, 0.8)
    # 每回合基础移动范围
    base_move_range: tuple[int, int] = (1, 3)
    # 事件概率
    event_randvalue: int = 450
