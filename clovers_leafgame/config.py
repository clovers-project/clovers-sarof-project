from pydantic import BaseModel


class Config(BaseModel):
    # 主路径
    main_path: str = "./LeafGames"
    # 默认显示字体
    fontname: str = "simsun"
    # 默认备用字体
    fallback_fonts: list[str] = [
        "arial",
        "tahoma",
        "msyh",
        "seguiemj",
    ]
