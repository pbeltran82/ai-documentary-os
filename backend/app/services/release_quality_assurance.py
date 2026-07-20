from __future__ import annotations

"""Single authoritative release-QA facade.

Import order matters because each historical QA layer extends the previous one.
This module deliberately loads rendered semantic QA first, then the corrected
technical v2 detector.  The resulting chain is:

base media checks -> semantic plan checks -> rendered-frame checks -> corrected
black/opening detection.

Public API routes import this module so a later compatibility import cannot remove
output-based checks.
"""

from . import media_quality_assurance as base
from . import rendered_semantic_quality_assurance as rendered
from . import media_quality_assurance_v2 as technical

# media_quality_assurance_v2 captured the installed rendered evaluator when it was
# imported above, so its function is the final composed evaluator.
evaluate_quality = technical.evaluate_quality
base.evaluate_quality = evaluate_quality
rendered.evaluate_quality = evaluate_quality

analyze_timeline_render = base.analyze_timeline_render
load_qa_report = base.load_qa_report
qa_report_path = base.qa_report_path
