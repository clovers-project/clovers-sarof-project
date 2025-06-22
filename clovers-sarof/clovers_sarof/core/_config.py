from pydantic import BaseModel


class Config(BaseModel):
    # 主路径
    path: str = "./data/LeafGames"
    # 默认显示字体
    fontname: str = "simsun"
    # 默认备用字体
    fallback_fonts: list[str] = [
        "arial",
        "tahoma",
        "msyh",
        "seguiemj",
    ]


from clovers.config import Config as CloversConfig


config_data = CloversConfig.environ().setdefault(__package__, {})
__config__ = Config.model_validate(config_data)
"""主配置类"""
config_data.update(__config__.model_dump())
