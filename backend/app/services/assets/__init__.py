from .nasa import SPEC as NASA
from .pexels import SPEC as PEXELS
from .pixabay import SPEC as PIXABAY
from .unsplash import SPEC as UNSPLASH
from .wikimedia import SPEC as WIKIMEDIA

PROVIDERS = {
    provider.name: provider
    for provider in (PIXABAY, UNSPLASH, WIKIMEDIA, NASA, PEXELS)
}

__all__ = ["PROVIDERS"]
