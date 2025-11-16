from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # 定义你的配置变量及其默认值
    MEDIA_ROOT_PATH: Path = Path("./my_media_files")
    FRONTEND_ORIGIN: str = "http://localhost:8000"

    class Config:
        # 告诉 Pydantic 从 .env 文件加载
        env_file = ".env"


# 创建一个全局可用的 settings 实例
settings = Settings()
