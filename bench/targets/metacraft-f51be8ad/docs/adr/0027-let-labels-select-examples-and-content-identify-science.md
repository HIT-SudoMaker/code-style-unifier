# 0027 - Let labels select examples and content identify science

Status: accepted

MetaCraft keeps paper-anchored names only on external benchmark cases, where a
human or harness needs a stable catalogue selector. A Brief and its resolved
Design are instead identified by their complete canonical scientific content;
neither copies a case label or carries a decorative display name. Methods keep
physical method names, PublishedReference keeps the exact selected paper
device, and typed Result restoration alone determines the benchmark Result
measure variant, so a case stores neither a duplicate selected device nor a
Result-family discriminator. This separates navigation from scientific
identity and lets a future paper-inspired achromatic case reuse the same Brief
language without making the paper name part of compilation. The cutover is
strict: documents carrying the retired Brief, Design, or case shadow fields
are rejected rather than translated, and retained application roots remain
immutable historical evidence.
