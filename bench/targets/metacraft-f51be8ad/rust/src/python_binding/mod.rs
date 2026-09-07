#![allow(unexpected_cfgs)] // PyO3 0.22's exception macro checks its legacy feature.

use std::path::PathBuf;

use pyo3::create_exception;
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::{pyclass, pymethods, pymodule, Bound, PyErr, PyModule, PyResult, Python};
use pyo3::types::{PyBytes, PyModuleMethods};

use crate::authority::Authority as CoreAuthority;

create_exception!(
    _authority,
    ReferenceUnresolvableError,
    PyRuntimeError,
    "An immutable Authority reference cannot be resolved."
);

#[pyclass(name = "Authority")]
struct Authority {
    core: CoreAuthority,
}

#[pymethods]
impl Authority {
    #[new]
    fn new(workspace: String) -> PyResult<Self> {
        CoreAuthority::open(PathBuf::from(workspace))
            .map(|core| Self { core })
            .map_err(native_error)
    }

    fn check(&self) -> PyResult<String> {
        canonical_json(self.core.check().map_err(native_error)?)
    }

    fn view(&self) -> PyResult<String> {
        canonical_json(self.core.view().map_err(native_error)?)
    }

    fn fetch<'py>(&self, python: Python<'py>, reference: &str) -> PyResult<Bound<'py, PyBytes>> {
        let bytes = self.core.fetch(reference).map_err(fetch_error)?;
        Ok(PyBytes::new_bound(python, &bytes))
    }

    #[pyo3(signature = (proposal, *, at))]
    fn decide(&self, proposal: &str, at: &str) -> PyResult<String> {
        canonical_json(self.core.decide(proposal, at).map_err(native_error)?)
    }
}

#[pymodule]
fn _authority(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add("__metacraft_native__", true)?;
    module.add_class::<Authority>()?;
    module.add(
        "ReferenceUnresolvableError",
        module.py().get_type_bound::<ReferenceUnresolvableError>(),
    )?;
    Ok(())
}

fn canonical_json(value: serde_json::Value) -> PyResult<String> {
    serde_jcs::to_string(&value)
        .map_err(|error| PyRuntimeError::new_err(format!("protocol_serialization_failed: {error}")))
}

fn native_error(message: String) -> PyErr {
    PyRuntimeError::new_err(message)
}

fn fetch_error(message: String) -> PyErr {
    if message.starts_with("reference_unresolvable:") {
        return ReferenceUnresolvableError::new_err(message);
    }
    native_error(message)
}
