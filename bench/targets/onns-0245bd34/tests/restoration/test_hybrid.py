from __future__ import annotations

import torch
from torch import nn

from experiments.restoration.optical_bench import OpticalBenchConfig
from experiments.restoration.fixed_measurement.learning.connection import ConnectionConfig, build_connection
from experiments.restoration.fixed_measurement.optics.frontend import RestorationFrontend
from experiments.restoration.fixed_measurement.learning.hybrid import FrozenFrontendBackend, JointFrontendBackend


class _TinyBackend(nn.Module):
    """
    鎻愪緵鍏夋暟娣峰悎娴嬭瘯澶瑰叿
    """
    def __init__(self) -> None:
        """
        鎸傝浇鍗曞弬鏁版祴璇曞悗绔潈閲?        """
        super().__init__()
        self.weight = nn.Parameter(torch.tensor(1.0))

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        """
        鎵ц鍏夋暟娣峰悎鍓嶅悜浼犳挱
        """
        return torch.clamp(image * self.weight, 0.0, 1.0)


class _RecordingBackend(nn.Module):
    """
    Capture the image handed from the hybrid connection to the backend.
    """

    def __init__(self) -> None:
        """
        Install one trainable weight so backend trainability is observable.
        """
        super().__init__()
        self.weight = nn.Parameter(torch.tensor(1.0))
        self.last_input: torch.Tensor | None = None

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        """
        Return the captured backend input unchanged.
        """
        self.last_input = image.detach().clone()
        return image * self.weight


def _frontend() -> RestorationFrontend:
    """
    鏋勫缓鍏夋暟娣峰悎娴嬭瘯鏁版嵁
    """
    return RestorationFrontend(
        OpticalBenchConfig(
            wavelength=1.0,
            input_plane_pixel_size=1.0,
            slm1_pixel_size=1.0,
            slm2_pixel_size=1.0,
            camera_pixel_size=1.0,
            focal_length=1.0,
            input_array_resolution=(8, 8),
            slm1_resolution=(8, 8),
            slm2_resolution=(16, 16),
            camera_resolution=(8, 8),
            phase_mask_resolution=8,
            slm2_active_resolution=(16, 16),
        )
    )


def test_frozen_frontend_backend_freezes_frontend_parameters() -> None:
    """
    鏍￠獙鍏夋暟娣峰悎濂戠害
    """
    model = FrozenFrontendBackend(_frontend(), _TinyBackend())

    assert all(not parameter.requires_grad for parameter in model.frontend.parameters())
    assert any(parameter.requires_grad for parameter in model.backend.parameters())


def test_joint_frontend_backend_keeps_both_sides_trainable() -> None:
    """
    鏍￠獙鍏夋暟娣峰悎濂戠害
    """
    model = JointFrontendBackend(_frontend(), _TinyBackend())

    assert any(parameter.requires_grad for parameter in model.frontend.parameters())
    assert any(parameter.requires_grad for parameter in model.backend.parameters())


def test_hybrid_forward_returns_image_shape() -> None:
    """
    鏍￠獙鍏夋暟娣峰悎濂戠害
    """
    model = JointFrontendBackend(_frontend(), _TinyBackend())
    field = torch.ones((2, 1, 8, 8), dtype=torch.complex64)

    output = model(field)

    assert output.shape == (2, 1, 8, 8)


def test_serial_connection_routes_optical_output_to_backend() -> None:
    """
    Serial connection preserves the original frontend-to-backend route.
    """
    frontend = _frontend()
    backend = _RecordingBackend()
    model = JointFrontendBackend(
        frontend,
        backend,
        connection=build_connection(ConnectionConfig("serial")),
    )
    field = torch.ones((2, 1, 8, 8), dtype=torch.complex64)
    expected_backend_input = frontend(field).to(dtype=torch.float32)

    output = model(field)

    assert output.shape == (2, 1, 8, 8)
    assert backend.last_input is not None
    assert torch.allclose(backend.last_input, expected_backend_input)


def test_joint_optical_residual_gate_starts_near_optical_image() -> None:
    """
    Scalar residual gate tanh(0)=0 makes the backend initially see degradation.
    """
    backend = _RecordingBackend()
    model = JointFrontendBackend(
        _frontend(),
        backend,
        connection=build_connection(
            ConnectionConfig.with_optical_residual_gate(initial_gate=0.75)
        ),
        is_connection_trainable=True,
    )
    field = torch.full((1, 1, 8, 8), 0.5 + 0.0j, dtype=torch.complex64)
    degraded_image = field.abs().square().real
    optical_restoration_image = model.frontend(field).to(dtype=torch.float32)

    output = model(field)

    assert output.shape == (1, 1, 8, 8)
    assert backend.last_input is not None
    expected = degraded_image + 0.75 * (
        optical_restoration_image - degraded_image
    )
    assert torch.allclose(backend.last_input, expected)
    assert any(parameter.requires_grad for parameter in model.connection.parameters())
    assert model.trainable_parameter_names() == [
        "phase_mask_fourier",
        "connection",
        "backend",
    ]


def test_frozen_frontend_backend_freezes_connection_when_not_requested() -> None:
    """
    Frozen hybrid freezes frontend always and connection unless requested.
    """
    model = FrozenFrontendBackend(
        _frontend(),
        _RecordingBackend(),
        connection=build_connection(ConnectionConfig.with_optical_residual_gate()),
    )

    assert all(not parameter.requires_grad for parameter in model.frontend.parameters())
    assert all(not parameter.requires_grad for parameter in model.connection.parameters())
    assert any(parameter.requires_grad for parameter in model.backend.parameters())
    assert model.trainable_parameter_names() == ["backend"]
