from __future__ import annotations

import pytest

from experiments.restoration.fixed_measurement.learning.backend import BackendConfig
from experiments.restoration.fixed_measurement.learning.validation import (
    validate_backend_role,
    validate_connection_role,
    validate_backend_connection_compatibility,
    validate_phase_options,
)


def test_validate_backend_role_frontend_rejects_backend() -> None:
    """
    楠岃瘉绾墠绔鑹叉嫆缁濇暟瀛楀悗绔?    """
    with pytest.raises(ValueError, match="frontend_only"):
        validate_backend_role("frontend_only", BackendConfig())


def test_validate_backend_role_backend_requires_backend() -> None:
    """
    楠岃瘉鍚庣瑙掕壊瑕佹眰鏁板瓧鍚庣閰嶇疆
    """
    with pytest.raises(ValueError, match="backend"):
        validate_backend_role("backend_only", None)


def test_validate_backend_connection_rejects_single_channel_backend() -> None:
    """
    楠岃瘉鍙岄€氶亾杩炴帴鎷掔粷鍗曢€氶亾鍚庣
    """
    with pytest.raises(ValueError, match="dual_channel"):
        validate_backend_connection_compatibility(
            "dual_channel",
            BackendConfig(model_name="nafnet_s"),
        )


def test_validate_connection_role_non_serial_requires_hybrid() -> None:
    """
    楠岃瘉闈炰覆琛岃繛鎺ヤ粎鐢ㄤ簬娣峰悎妯″瀷
    """
    with pytest.raises(ValueError, match="non-serial"):
        validate_connection_role("backend_only", "dual_channel")


def test_validate_phase_options_rejects_unknown() -> None:
    """
    楠岃瘉鐩镐綅閰嶇疆鎷掔粷鏈煡鍙傛暟鍖栨柟妗?    """
    with pytest.raises(ValueError, match="phase_parameterization"):
        validate_phase_options("bogus", "zeros")
