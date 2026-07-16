# Open Archives provider

AI Documentary OS exposes one **Open Archives** provider that aggregates:

- Wikimedia Commons
- Openverse
- Library of Congress
- The Metropolitan Museum of Art Open Access collection

The provider deliberately favors precision over result count.

## Rights gate

Candidates are admitted only when the source metadata supports reusable media:

- Openverse: CC0, Public Domain Mark, CC BY, or CC BY-SA, with the commercial-use API filter enabled
- Library of Congress: an explicit public-use statement such as “No known restrictions on publication” or “Public domain”
- The Met: `isPublicDomain=true` and a downloadable primary image
- Wikimedia Commons: public domain, CC0, CC BY, or CC BY-SA; noncommercial, no-derivatives, and all-rights-reserved records are rejected

Unknown rights are treated as unsafe and hidden.

## Technical gate

Candidates are rejected before ranking when they have:

- no HTTPS preview, download, or source URL
- known width below 1000 pixels
- known height below 600 pixels
- an extreme portrait ratio below 0.72
- a visible watermark flag from the provider

The Visual Director applies the separate must-show, must-avoid, landscape, duration, resolution, repetition, and evidence scoring rules after this gate.

## Deduplication

Open Archives normalizes candidates under one provider identity while preserving the original source page, creator, license, and attribution. Exact download URLs are deduplicated across collections before the shortlist is built.

## Product rule

> Zero defensible results are better than a grid filled with weak or legally ambiguous media.
