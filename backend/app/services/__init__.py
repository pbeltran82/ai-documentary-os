"""Application service modules."""

# Register the expanded Tech & Behavior template family before suggestion,
# preview, batch rendering, or timeline assembly asks for a composition.
from . import documentary_variety_expansion as _documentary_variety_expansion  # noqa: F401,E402
from . import documentary_variety_guard as _documentary_variety_guard  # noqa: F401,E402

# Finance and character-led 16:9 scenes use the shared expressive rig rather
# than the Tech-only landscape figure. Install its neutral stance correction at
# service import time so previews, web renders, and exports all match.
from . import character_stance_patch as _character_stance_patch  # noqa: F401,E402

# Broad documentary scenes use the beat-aware cartoon illustration engine while
# algorithm-specific scenes retain the existing Tech & Behavior compositions.
from . import cartoon_documentary_patch as _cartoon_documentary_patch  # noqa: F401,E402
from . import cartoon_documentary_polish as _cartoon_documentary_polish  # noqa: F401,E402
from . import cartoon_shorts_polish as _cartoon_shorts_polish  # noqa: F401,E402
