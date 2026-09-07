from __future__ import annotations

import numpy as np


def _normalize_edge_response(response: np.ndarray) -> np.ndarray:
    response_float = np.abs(response).astype(np.float32, copy=False)
    max_value = float(response_float.max())
    if max_value == 0.0:
        return np.zeros_like(response_float, dtype=np.float32)
    return (response_float / max_value).astype(np.float32, copy=False)
