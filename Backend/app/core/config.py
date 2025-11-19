from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """
    Application Configuration Settings.
    This class defines the configuration variables used throughout the application.
    Values are loaded from environment variables or a .env file.
    """

    # The root directory where media files will be stored on the server.
    # Defaults to "./my_media_files" relative to the backend execution path.
    MEDIA_ROOT_PATH: Path = Path("./my_media_files")

    # The URL of the frontend application.
    # This is used to configure CORS (Cross-Origin Resource Sharing) to allow requests from the browser.
    FRONTEND_ORIGIN: str = "http://localhost:8000"

    # API Key for The Movie Database (TMDB).
    # Required for the smart upload feature to fetch movie/TV show metadata.
    TMDB_API_KEY: str = ""

    class Config:
        """
        Pydantic configuration class.
        """
        # Instruct Pydantic to load settings from a file named ".env"
        env_file = ".env"


# Create a globally accessible settings instance
settings = Settings()