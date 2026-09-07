from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .aperture import (
        Aperture as Aperture,
        Cell as Cell,
        Circle as Circle,
        Ellipse as Ellipse,
        Geometry as Geometry,
        Material as Material,
        Rectangle as Rectangle,
        Square as Square,
    )
    from .brief import (
        ApertureExtent as ApertureExtent,
        ApertureFootprint as ApertureFootprint,
        ApertureIntent as ApertureIntent,
        AtomIntent as AtomIntent,
        ControlStrategy as ControlStrategy,
        ContinuousBandSpectrum as ContinuousBandSpectrum,
        MaterialIntent as MaterialIntent,
        MetalensBrief as MetalensBrief,
        MonochromaticSpectrum as MonochromaticSpectrum,
        OperatingSpectrum as OperatingSpectrum,
        Polarization as Polarization,
    )
    from .focal_field_comparison import (
        FocalFieldComparison as FocalFieldComparison,
    )
    from .design import (
        MetalensDesign as MetalensDesign,
        TargetPhase as TargetPhase,
        require_metalens_design as require_metalens_design,
    )
    from .focus import (
        FocalRegion as FocalRegion,
        Focus as Focus,
        FocusSurvey as FocusSurvey,
        Leakage as Leakage,
        evaluate_focus as evaluate_focus,
        evaluate_vector_focus as evaluate_vector_focus,
    )
    from .height import (
        FabricationRange as FabricationRange,
        HeightAdviceBasis as HeightAdviceBasis,
        HeightBasis as HeightBasis,
        HeightChoice as HeightChoice,
        HeightConstraintBasis as HeightConstraintBasis,
        HeightDomain as HeightDomain,
    )
    from .height_advice import (
        HeightAdvice as HeightAdvice,
        HeightRecommendation as HeightRecommendation,
    )
    from .cell_study import (
        CellInputBasis as CellInputBasis,
        CellResponseChannel as CellResponseChannel,
        CellResponseWork as CellResponseWork,
        CellStudy as CellStudy,
        CellStudyConsultation as CellStudyConsultation,
        CellStudyConsultationResult as CellStudyConsultationResult,
        CellStudyEvidenceRequirement as CellStudyEvidenceRequirement,
        CellStudyFormationError as CellStudyFormationError,
        CellStudyOption as CellStudyOption,
        CellStudyPlan as CellStudyPlan,
        CellStudyRoute as CellStudyRoute,
        InvalidCellStudyAnswer as InvalidCellStudyAnswer,
        LocalPbCellStudy as LocalPbCellStudy,
        PropagationCellStudy as PropagationCellStudy,
        accept_cell_study_answer as accept_cell_study_answer,
        build_bounded_cell_study_options as build_bounded_cell_study_options,
        form_cell_study_consultation as form_cell_study_consultation,
    )
    from .material import (
        BoundMaterial as BoundMaterial,
        MaterialBinding as MaterialBinding,
    )
    from .period import (
        PeriodAdviceBasis as PeriodAdviceBasis,
        PeriodBasis as PeriodBasis,
        PeriodChoice as PeriodChoice,
        PeriodConstraintBasis as PeriodConstraintBasis,
        PeriodDomain as PeriodDomain,
    )
    from .period_advice import (
        PeriodAdvice as PeriodAdvice,
        PeriodRecommendation as PeriodRecommendation,
    )
    from .result import (
        AchromaticResult as AchromaticResult,
        GeometricResult as GeometricResult,
        PointwiseGeometricResult as PointwiseGeometricResult,
        PointwisePropagationResult as PointwisePropagationResult,
        PropagationResult as PropagationResult,
    )
    from .run_projection import (
        RunManifest as RunManifest,
        RunStep as RunStep,
        project_run_manifest as project_run_manifest,
    )

_EXPORTS = {
    "AchromaticResult": (".result", "AchromaticResult"),
    "Aperture": (".aperture", "Aperture"),
    "ApertureExtent": (".brief", "ApertureExtent"),
    "ApertureFootprint": (".brief", "ApertureFootprint"),
    "ApertureIntent": (".brief", "ApertureIntent"),
    "AtomIntent": (".brief", "AtomIntent"),
    "BoundMaterial": (".material", "BoundMaterial"),
    "CellInputBasis": (".cell_study", "CellInputBasis"),
    "CellResponseChannel": (".cell_study", "CellResponseChannel"),
    "CellResponseWork": (".cell_study", "CellResponseWork"),
    "CellStudy": (".cell_study", "CellStudy"),
    "CellStudyConsultation": (".cell_study", "CellStudyConsultation"),
    "CellStudyConsultationResult": (
        ".cell_study",
        "CellStudyConsultationResult",
    ),
    "CellStudyEvidenceRequirement": (
        ".cell_study",
        "CellStudyEvidenceRequirement",
    ),
    "CellStudyFormationError": (".cell_study", "CellStudyFormationError"),
    "CellStudyOption": (".cell_study", "CellStudyOption"),
    "CellStudyPlan": (".cell_study", "CellStudyPlan"),
    "CellStudyRoute": (".cell_study", "CellStudyRoute"),
    "Cell": (".aperture", "Cell"),
    "Circle": (".aperture", "Circle"),
    "ControlStrategy": (".brief", "ControlStrategy"),
    "ContinuousBandSpectrum": (".brief", "ContinuousBandSpectrum"),
    "Ellipse": (".aperture", "Ellipse"),
    "FabricationRange": (".height", "FabricationRange"),
    "FocalFieldComparison": (".focal_field_comparison", "FocalFieldComparison"),
    "FocalRegion": (".focus", "FocalRegion"),
    "Focus": (".focus", "Focus"),
    "FocusSurvey": (".focus", "FocusSurvey"),
    "Geometry": (".aperture", "Geometry"),
    "GeometricResult": (".result", "GeometricResult"),
    "HeightAdvice": (".height_advice", "HeightAdvice"),
    "HeightAdviceBasis": (".height", "HeightAdviceBasis"),
    "HeightBasis": (".height", "HeightBasis"),
    "HeightChoice": (".height", "HeightChoice"),
    "HeightConstraintBasis": (".height", "HeightConstraintBasis"),
    "HeightDomain": (".height", "HeightDomain"),
    "HeightRecommendation": (".height_advice", "HeightRecommendation"),
    "Leakage": (".focus", "Leakage"),
    "LocalPbCellStudy": (".cell_study", "LocalPbCellStudy"),
    "InvalidCellStudyAnswer": (".cell_study", "InvalidCellStudyAnswer"),
    "Material": (".aperture", "Material"),
    "MaterialBinding": (".material", "MaterialBinding"),
    "MaterialIntent": (".brief", "MaterialIntent"),
    "MetalensBrief": (".brief", "MetalensBrief"),
    "MonochromaticSpectrum": (".brief", "MonochromaticSpectrum"),
    "OperatingSpectrum": (".brief", "OperatingSpectrum"),
    "MetalensDesign": (".design", "MetalensDesign"),
    "PeriodAdvice": (".period_advice", "PeriodAdvice"),
    "PeriodAdviceBasis": (".period", "PeriodAdviceBasis"),
    "PeriodBasis": (".period", "PeriodBasis"),
    "PeriodChoice": (".period", "PeriodChoice"),
    "PeriodConstraintBasis": (".period", "PeriodConstraintBasis"),
    "PeriodDomain": (".period", "PeriodDomain"),
    "PeriodRecommendation": (".period_advice", "PeriodRecommendation"),
    "PointwiseGeometricResult": (".result", "PointwiseGeometricResult"),
    "PointwisePropagationResult": (".result", "PointwisePropagationResult"),
    "Polarization": (".brief", "Polarization"),
    "PropagationResult": (".result", "PropagationResult"),
    "PropagationCellStudy": (".cell_study", "PropagationCellStudy"),
    "Rectangle": (".aperture", "Rectangle"),
    "Square": (".aperture", "Square"),
    "TargetPhase": (".design", "TargetPhase"),
    "RunManifest": (".run_projection", "RunManifest"),
    "RunStep": (".run_projection", "RunStep"),
    "accept_cell_study_answer": (
        ".cell_study",
        "accept_cell_study_answer",
    ),
    "build_bounded_cell_study_options": (
        ".cell_study",
        "build_bounded_cell_study_options",
    ),
    "evaluate_focus": (".focus", "evaluate_focus"),
    "evaluate_vector_focus": (".focus", "evaluate_vector_focus"),
    "require_metalens_design": (".design", "require_metalens_design"),
    "form_cell_study_consultation": (
        ".cell_study",
        "form_cell_study_consultation",
    ),
    "project_run_manifest": (".run_projection", "project_run_manifest"),
}

__all__ = list(_EXPORTS)  # pyright: ignore[reportUnsupportedDunderAll]


def __getattr__(name: str) -> Any:
    """
    Load one requested metalens value without opening unrelated realizations.
    """

    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as error:
        raise AttributeError(name) from error
    module = import_module(module_name, __name__)
    for export_name, (export_module, export_attribute) in _EXPORTS.items():
        if export_module == module_name:
            globals()[export_name] = getattr(module, export_attribute)
    return globals()[name]
