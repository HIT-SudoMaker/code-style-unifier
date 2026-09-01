from chromatix_next import optics
from chromatix_next.optics import detection, element, propagation, source

grid = optics.SpatialGrid.centered(
    sample_counts=(64, 64),
    sample_spacing=(4.0e-6, 4.0e-6),
)
spectrum = optics.Spectrum.monochromatic(532.0e-9)
polarization = optics.Polarization.linear_x()
source_field = source.PlaneWave(
    spectrum=spectrum,
    polarization=polarization,
    propagation_direction=optics.PropagationDirection.forward(),
    relative_amplitude=1.0,
)(grid)
pupil_field = element.circular_pupil(
    source_field,
    grid=grid,
    radius=80.0e-6,
)
lens_field = element.ideal_thin_lens(
    pupil_field,
    grid=grid,
    focal_length=50.0e-3,
)
propagated_field = propagation.fresnel_transform(
    lens_field,
    axial_distance=50.0e-3,
)
intensity = detection.intensity_detection(propagated_field)
assert intensity.values[32, 32] == intensity.values.max()
