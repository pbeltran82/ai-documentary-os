"""Ensure v5 object primitives are used by v4 scenes that call v3 directly."""

from . import cartoon_art_polish_v3 as v3
from . import cartoon_art_polish_v5 as v5

# The v4 transport renderer calls v3._spacecraft directly. Redirect it to the
# cleaned capsule so the stray blue triangle is removed everywhere, not only on
# route-map scenes.
v3._spacecraft = v5._spacecraft
