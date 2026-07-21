"""Application service modules."""

# Register the expanded Tech & Behavior template family before suggestion,
# preview, batch rendering, or timeline assembly asks for a composition.
from . import documentary_variety_expansion as _documentary_variety_expansion  # noqa: F401,E402
from . import documentary_variety_guard as _documentary_variety_guard  # noqa: F401,E402
from . import cinematic_visual_quality as _cinematic_visual_quality  # noqa: F401,E402
from . import cinematic_composition_upgrade as _cinematic_composition_upgrade  # noqa: F401,E402
from . import cinematic_anti_slide_pass as _cinematic_anti_slide_pass  # noqa: F401,E402

# Finance and character-led 16:9 scenes use the shared expressive rig rather
# than the Tech-only landscape figure. Install its neutral stance correction at
# service import time so previews, web renders, and exports all match.
from . import character_stance_patch as _character_stance_patch  # noqa: F401,E402
