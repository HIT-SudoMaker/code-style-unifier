from __future__ import annotations

from collections.abc import Mapping
import hashlib
from typing import Any

from ..canonical import encode_bytes
from .protocol import Reference


def reference_for(
    body: bytes,
    *,
    media_type: str = "application/json",
    descriptive_metadata: Mapping[str, Any] | None = None,
) -> Reference:
    """
    Name exact bytes under the authority object identity contract.
    """

    metadata = (
        {} if descriptive_metadata is None else descriptive_metadata
    )
    content_hash = _hash(body)
    metadata_body = encode_bytes(
        {
            "content_hash": content_hash,
            "descriptive_metadata": metadata,
            "media_type": media_type,
            "size_bytes": len(body),
        }
    )
    return Reference(
        content_hash=content_hash,
        media_type=media_type,
        metadata_content_hash=_hash(metadata_body),
        size_bytes=len(body),
    )


def reference_matches(
    reference: Reference,
    body: bytes,
    *,
    media_type: str = "application/json",
    descriptive_metadata: Mapping[str, Any] | None = None,
) -> bool:
    """
    Match all fields of one exact authority object reference.
    """

    return reference == reference_for(
        body,
        media_type=media_type,
        descriptive_metadata=descriptive_metadata,
    )


def _hash(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"
