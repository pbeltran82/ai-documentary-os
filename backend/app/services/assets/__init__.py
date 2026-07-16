from .archive_hub import SPEC as OPEN_ARCHIVES
from .nasa import SPEC as NASA
from .pexels import SPEC as PEXELS
from .pixabay import SPEC as PIXABAY
from .unsplash import SPEC as UNSPLASH

PROVIDERS = {
    provider.name: provider
    for provider in (PIXABAY, UNSPLASH, OPEN_ARCHIVES, NASA, PEXELS)
}

__all__ = ["PROVIDERS"]
