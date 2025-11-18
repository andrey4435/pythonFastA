from pydantic import BaseModel
from typing import Optional

class Movietop(BaseModel):
    id: int
    name: str
    cost: int
    director: str
    is_available: bool
    cover_url: Optional[str] = None          # ссылка на обложку
    description_url: Optional[str] = None    # ссылка на описание

