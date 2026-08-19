from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ModelConfigUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    provider: str = Field(min_length=1, max_length=50)
    model_name: str = Field(min_length=1, max_length=100)
    base_url: HttpUrl
    api_key: str | None = Field(default=None, min_length=1)
    is_active: bool = True
