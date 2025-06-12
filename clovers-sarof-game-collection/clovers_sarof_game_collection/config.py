from pydantic import BaseModel


class Config(BaseModel):
    # 超时时间
    timeout: int = 60
    # 默认赌注
    default_bet: int = 200
