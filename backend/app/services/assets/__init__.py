from .library_of_congress import SPEC as LIBRARY_OF_CONGRESS
from .met import SPEC as MET
from .nasa import SPEC as NASA
from .openverse import SPEC as OPENVERSE
from .pexels import SPEC as PEXELS
from .pixabay import SPEC as PIXABAY
from .unsplash import SPEC as UNSPLASH
from .wikimedia import SPEC as WIKIMEDIA

PROVIDERS = {
    provider.name: provider
    for provider in (
        PIXABAY,
        UNSPLASH,
        OPENVERSE,
        WIKIMEDIA,
        LIBRARY_OF_CONGRESS,
        MET,
        NASA,
        PEXELS,
    )
}

__all__ = ["PROVIDERS"]
