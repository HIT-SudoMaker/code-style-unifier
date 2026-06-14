use std::fs;

use tempfile::tempdir;
use unifier::core::evaluators::evaluate_all;
use unifier::core::evidence::{
    DependencyGroup, EvidenceStore, ExpressionKind, SymbolKind, SymbolVisibility, TextRole,
};
use unifier::core::frontend::extract_text_evidence;
use unifier::core::profile::Profile;
use unifier::core::scanner::scan_workspace;

fn has_attribute(symbol: &unifier::core::evidence::SymbolFact, expected: &str) -> bool {
    symbol
        .attributes
        .iter()
        .any(|attribute| attribute == expected)
}

fn store_from_python_source(source: &str) -> EvidenceStore {
    store_from_python_file("module.py", source)
}

fn store_from_python_file(path: &str, source: &str) -> EvidenceStore {
    let dir = tempdir().unwrap();
    fs::write(dir.path().join(path), source).unwrap();
    let state = scan_workspace(dir.path(), &[]).unwrap();
    extract_text_evidence(&state).unwrap()
}

#[test]
fn python_internal_docstring_surface_still_reports_core013() {
    let store = store_from_python_source(
        r#"
def _helper():
    """Internal helper contract."""
    return 1
"#,
    );

    assert!(
        store.public_surfaces.iter().any(|surface| {
            surface.symbol_name == "_helper"
                && surface.visibility == "internal"
                && surface.has_doc_region
        }),
        "internal documented symbols must still create public-surface facts for Core013"
    );

    let profile = Profile::from_toml_str(include_str!("../../profiles/default.toml")).unwrap();
    let issues = evaluate_all(&store, &profile);

    assert!(
        issues.iter().any(|issue| issue.rule == "Core013"),
        "Core013 must still review source-derived internal API docs"
    );
}

#[test]
fn extracts_python_module_symbols_imports_and_expressions() {
    let store = store_from_python_source(
        "from __future__ import annotations\n\
from typing import List\n\
import logging\n\
LOGGER = logging.getLogger(__name__)\n\
\n\
class Runner:\n\
    \"\"\"运行器\"\"\"\n\
    def run(self, value) -> List[str]:\n\
        LOGGER.info(f\"value={value}\")\n\
        return []\n",
    );

    assert!(store
        .module_units
        .iter()
        .any(|module| module.path == "module.py"));
    assert!(store
        .dependency_edges
        .iter()
        .any(|edge| edge.group == DependencyGroup::Future));
    assert!(store
        .dependency_edges
        .iter()
        .any(|edge| edge.source == "typing" && edge.imported == "List"));
    assert!(store
        .symbols
        .iter()
        .any(|symbol| symbol.name == "Runner" && symbol.kind == SymbolKind::Class));
    assert!(store.symbols.iter().any(
        |symbol| symbol.name == "run" && symbol.missing_parameter_annotations == vec!["value"]
    ));
    assert!(store
        .expressions
        .iter()
        .any(|expr| expr.kind == ExpressionKind::LoggingCall));
    assert!(store.symbols.iter().any(|symbol| symbol.name == "LOGGER"
        && symbol.kind == SymbolKind::Constant
        && symbol.type_text.as_deref() == Some("logging.getLogger")));
    assert!(store
        .expressions
        .iter()
        .any(|expr| expr.kind == ExpressionKind::TypeExpression && expr.text == "List[str]"));
}

#[test]
fn python_embedded_probe_code_inside_triple_string_does_not_create_symbols() {
    let store = store_from_python_file(
        "test_output_path_contracts.py",
        r#"
def build_probe():
    return textwrap.dedent("""
        class FakeQtSignal:
            def connect(self, callback):
                self.callback = callback

        def helper():
            return 1
    """)
"#,
    );

    assert!(
        store
            .symbols
            .iter()
            .all(|symbol| symbol.name != "connect" && symbol.name != "helper"),
        "symbols inside embedded triple-quoted data must not become real Python symbols"
    );
}

#[test]
fn python_triple_string_opener_preserves_code_prefix_facts() {
    let store = store_from_python_source(
        r#"
def fail() -> None:
    flag: bool = """enabled"""
    raise ValueError("""bad value""")
"#,
    );

    assert!(
        store
            .symbols
            .iter()
            .any(|symbol| symbol.name == "flag" && symbol.type_text.as_deref() == Some("bool")),
        "bool annotations before triple strings must still become symbols"
    );
    assert!(
        store.expressions.iter().any(|expr| {
            expr.kind == ExpressionKind::ErrorMessage
                && expr.callee.as_deref() == Some("ValueError")
        }),
        "error messages with triple-quoted string arguments must still be extracted"
    );
}

#[test]
fn python_triple_string_segments_do_not_merge_prefix_and_suffix_facts() {
    let store = store_from_python_source(
        r#"
import logging

logger = logging.getLogger(__name__)

def run() -> None:
    payload = """x"""; is_ready: bool = False
    other = """
    text
    """; has_value: bool = False
    raise ValueError("""bad"""); logger.info("done")
"#,
    );

    assert!(
        !store.symbols.iter().any(|symbol| {
            matches!(symbol.name.as_str(), "payload" | "other")
                && symbol.type_text.as_deref() == Some("bool")
        }),
        "triple-string prefix assignments must not absorb bool suffix annotations"
    );
    assert!(
        store
            .symbols
            .iter()
            .any(|symbol| symbol.name == "is_ready" && symbol.type_text.as_deref() == Some("bool")),
        "same-line suffix bool annotation must still be extracted"
    );
    assert!(
        store.symbols.iter().any(|symbol| {
            symbol.name == "has_value" && symbol.type_text.as_deref() == Some("bool")
        }),
        "multi-line closer suffix bool annotation must still be extracted"
    );
    assert!(
        store.expressions.iter().any(|expr| {
            expr.kind == ExpressionKind::LoggingCall
                && expr.callee.as_deref() == Some("logger.info")
        }),
        "suffix logging call after a triple-string argument must still be extracted"
    );
}

#[test]
fn extracts_python_module_docstring_fact() {
    let store = store_from_python_source("\"\"\"模块说明\"\"\"\n\nVALUE = 1\n");

    let module = store
        .module_units
        .iter()
        .find(|module| module.path == "module.py")
        .unwrap();
    assert!(module.has_module_doc_region);
    assert!(store
        .doc_regions
        .iter()
        .any(|doc| doc.file_id == module.file_id && doc.symbol_name == "__module__"));
    assert!(store
        .text_spans
        .iter()
        .any(|text| text.role == TextRole::DocSummary && text.normalized_text == "模块说明"));
}

#[test]
fn extracts_python_protocol_methods_and_bool_parameter_symbols() {
    let store = store_from_python_source(
        "class Runner:\n\
    enable_static_template: bool = False\n\
    def __call__(\n\
        self,\n\
        should_stop: bool,\n\
    ) -> None:\n\
        return None\n",
    );

    assert!(store
        .symbols
        .iter()
        .any(|symbol| symbol.name == "__call__" && symbol.visibility == SymbolVisibility::Public));
    assert!(store
        .public_surfaces
        .iter()
        .any(|surface| surface.symbol_name == "__call__"));
    assert!(store
        .symbols
        .iter()
        .any(|symbol| symbol.name == "should_stop"
            && symbol.kind == SymbolKind::Parameter
            && symbol.range == "5:1-5:1"
            && symbol.type_text.as_deref() == Some("bool")));
    assert!(store
        .symbols
        .iter()
        .any(|symbol| symbol.name == "enable_static_template"
            && symbol.kind == SymbolKind::Variable
            && symbol.type_text.as_deref() == Some("bool")));
}

#[test]
fn python_multiline_property_docstring_binds_to_symbol_start() {
    let store = store_from_python_file(
        "config_bundle.py",
        r#"
class Bundle:
    @property
    def control_area_layout_configuration(
        self,
    ) -> DemonstrationControlAreaLayoutConfigProtocol:
        """
        返回控制区布局配置
        """
        return self._layout
"#,
    );

    let symbol = store
        .symbols
        .iter()
        .find(|symbol| symbol.name == "control_area_layout_configuration")
        .expect("property symbol is extracted");

    assert!(
        symbol.range.starts_with("4:"),
        "symbol range must start at the def line, got {}",
        symbol.range
    );
    assert!(
        symbol.doc_region_id.is_some(),
        "multi-line signature docstring must bind to the property symbol"
    );

    let surface = store
        .public_surfaces
        .iter()
        .find(|surface| surface.symbol_name == "control_area_layout_configuration")
        .expect("property has public surface fact");

    assert!(
        surface.has_doc_region,
        "Core011 must see the bound doc region through PublicSurfaceFact"
    );
}

#[test]
fn python_multiline_signature_blank_line_docstring_binds_to_symbol() {
    let store = store_from_python_file(
        "bundle.py",
        "class Bundle:\n\
    def run(\n\
        self,\n\
    ) -> int:\n\
\n\
        \"\"\"\n\
        返回结果\n\
        \"\"\"\n\
        return 1\n",
    );

    let run = store
        .symbols
        .iter()
        .find(|symbol| symbol.name == "run")
        .expect("run function is extracted");

    assert!(
        run.doc_region_id.is_some(),
        "docstring after a blank line must bind to the multi-line signature"
    );

    let surface = store
        .public_surfaces
        .iter()
        .find(|surface| surface.symbol_name == "run")
        .expect("run function has public surface fact");

    assert!(
        surface.has_doc_region,
        "Core011 must see the doc region bound through PublicSurfaceFact"
    );

    let profile = Profile::from_toml_str(include_str!("../../profiles/default.toml")).unwrap();
    let issues = evaluate_all(&store, &profile);

    assert!(
        !issues.iter().any(|issue| {
            issue.rule == "Core011"
                && issue
                    .path
                    .as_deref()
                    .is_some_and(|path| path.ends_with("bundle.py"))
                && issue
                    .range
                    .as_deref()
                    .is_some_and(|range| range.starts_with("2:"))
        }),
        "documented run function must not trigger Core011 on its declaration range"
    );
}

#[test]
fn python_inline_body_signature_does_not_consume_next_docstring() {
    let store = store_from_python_source(
        "def first(): pass\ndef second():\n    \"\"\"Second doc\"\"\"\n    pass\n",
    );

    let first = store
        .symbols
        .iter()
        .find(|symbol| symbol.name == "first")
        .expect("first function is extracted");
    let second = store
        .symbols
        .iter()
        .find(|symbol| symbol.name == "second")
        .expect("second function is extracted");

    assert!(
        first.doc_region_id.is_none(),
        "inline-body function must not consume the following docstring"
    );
    assert!(
        second.doc_region_id.is_some(),
        "following function docstring must bind to the following function"
    );

    let profile = Profile::from_toml_str(include_str!("../../profiles/default.toml")).unwrap();
    let issues = evaluate_all(&store, &profile);

    assert!(
        !issues.iter().any(|issue| {
            issue.rule == "Core011"
                && issue
                    .path
                    .as_deref()
                    .is_some_and(|path| path.ends_with("module.py"))
                && issue
                    .range
                    .as_deref()
                    .is_some_and(|range| range.starts_with("2:"))
        }),
        "documented second function must not trigger Core011 on line 2"
    );
    assert!(
        issues.iter().any(|issue| {
            issue.rule == "Core011"
                && issue
                    .path
                    .as_deref()
                    .is_some_and(|path| path.ends_with("module.py"))
                && issue
                    .range
                    .as_deref()
                    .is_some_and(|range| range.starts_with("1:"))
        }),
        "undocumented first function can still trigger Core011 on line 1"
    );
}

#[test]
fn python_signature_with_trailing_comment_binds_docstring() {
    let store = store_from_python_source(
        "def documented():  # public API\n    \"\"\"Doc\"\"\"\n    pass\n",
    );

    let documented = store
        .symbols
        .iter()
        .find(|symbol| symbol.name == "documented")
        .expect("documented function is extracted");

    assert!(
        documented.doc_region_id.is_some(),
        "trailing-comment signature docstring must bind to the function"
    );

    let profile = Profile::from_toml_str(include_str!("../../profiles/default.toml")).unwrap();
    let issues = evaluate_all(&store, &profile);

    assert!(
        !issues.iter().any(|issue| {
            issue.rule == "Core011"
                && issue
                    .path
                    .as_deref()
                    .is_some_and(|path| path.ends_with("module.py"))
                && issue
                    .range
                    .as_deref()
                    .is_some_and(|range| range.starts_with("1:"))
        }),
        "documented trailing-comment function must not trigger Core011 on line 1"
    );
}

#[test]
fn python_parameter_parsing_respects_nested_commas() {
    let store = store_from_python_source(
        "from collections.abc import Callable\n\n\
def run(mapping: dict[str, str], callback: Callable[..., None]) -> None:\n    return None\n",
    );

    let run = store
        .symbols
        .iter()
        .find(|symbol| symbol.name == "run")
        .unwrap();
    assert!(run.missing_parameter_annotations.is_empty());
    assert!(store.symbols.iter().any(|symbol| symbol.name == "mapping"
        && symbol.kind == SymbolKind::Parameter
        && symbol.type_text.as_deref() == Some("dict[str, str]")));
    assert!(store.symbols.iter().any(|symbol| symbol.name == "callback"
        && symbol.kind == SymbolKind::Parameter
        && symbol.type_text.as_deref() == Some("Callable[..., None]")));
}

#[test]
fn extracts_python_logging_and_typing_facts_without_comment_or_string_false_positives() {
    let store = store_from_python_source(
        "from typing import Mapping, Sequence\n\
# value: List[str]\n\
text = \"logging.getLogger(\"\n\
class Runner:\n\
    def __init__(self) -> None:\n\
        self._logger = logging.getLogger(__name__)\n\
    def run(\n\
        self,\n\
        value: int,\n\
    ) -> None:\n\
        client.info(f\"skip={value}\")\n\
        logger.critical(f\"value={value}\")\n\
        return None\n",
    );

    assert!(store
        .dependency_edges
        .iter()
        .any(|edge| edge.source == "typing" && edge.imported == "Mapping, Sequence"));
    assert!(store
        .symbols
        .iter()
        .any(|symbol| symbol.name == "self._logger"
            && symbol.kind == SymbolKind::Field
            && symbol.type_text.as_deref() == Some("logging.getLogger")));
    assert!(store.symbols.iter().any(|symbol| symbol.name == "run"
        && symbol.return_annotation.as_deref() == Some("None")
        && symbol.missing_parameter_annotations.is_empty()
        && symbol
            .type_text
            .as_deref()
            .is_some_and(|text| text.contains("value: int"))));
    assert!(!store
        .symbols
        .iter()
        .any(|symbol| symbol.name == "text"
            && symbol.type_text.as_deref() == Some("logging.getLogger")));
    assert!(!store
        .expressions
        .iter()
        .any(|expr| expr.kind == ExpressionKind::TypeExpression && expr.text == "List[str]"));
    assert!(!store
        .expressions
        .iter()
        .any(|expr| expr.kind == ExpressionKind::LoggingCall && expr.text.contains("client.info")));
    assert!(store
        .expressions
        .iter()
        .any(|expr| expr.kind == ExpressionKind::LoggingCall
            && expr.callee.as_deref() == Some("logger.critical")));
}

#[test]
fn python_stdlib_imports_do_not_trigger_core008_grouping() {
    let store = store_from_python_source(
        "from __future__ import annotations\n\
from collections.abc import Callable\n\
import fcntl\n\
import logging\n\
import stat\n\
import threading\n\
import winreg\n\
from numbers import Real\n\
from typing import Any\n",
    );
    let profile = Profile::from_toml_str(include_str!("../../profiles/default.toml")).unwrap();
    let issues = evaluate_all(&store, &profile);

    assert!(
        !issues
            .iter()
            .any(|issue| issue.rule == "Core008" && issue.path.as_deref() == Some("module.py")),
        "Python standard library imports should remain in the standard group"
    );
}

#[test]
fn python_dependency_edges_record_import_block_contexts() {
    let store = store_from_python_source(concat!(
        "from beta import Beta\n",
        "from alpha import Alpha\n",
        "\n",
        "if TYPE_CHECKING:\n",
        "    from delta import Delta\n",
        "    from charlie import Charlie\n",
        "\n",
        "def load_model():\n",
        "    import torch\n",
        "    import timm\n",
    ));

    let beta = store
        .dependency_edges
        .iter()
        .find(|edge| edge.source == "beta")
        .unwrap();
    let alpha = store
        .dependency_edges
        .iter()
        .find(|edge| edge.source == "alpha")
        .unwrap();
    let delta = store
        .dependency_edges
        .iter()
        .find(|edge| edge.source == "delta")
        .unwrap();
    let charlie = store
        .dependency_edges
        .iter()
        .find(|edge| edge.source == "charlie")
        .unwrap();
    let torch = store
        .dependency_edges
        .iter()
        .find(|edge| edge.source == "torch")
        .unwrap();
    let timm = store
        .dependency_edges
        .iter()
        .find(|edge| edge.source == "timm")
        .unwrap();

    assert_eq!(beta.block_id, alpha.block_id);
    assert!(!beta.is_deferred);
    assert!(!beta.is_type_checking);
    assert!(!beta.is_conditional);

    assert_eq!(delta.block_id, charlie.block_id);
    assert_ne!(beta.block_id, delta.block_id);
    assert!(delta.is_type_checking);
    assert!(delta.is_conditional);
    assert!(!delta.is_deferred);

    assert_eq!(torch.block_id, timm.block_id);
    assert_ne!(beta.block_id, torch.block_id);
    assert!(torch.is_deferred);
    assert!(!torch.is_type_checking);
    assert!(!torch.is_conditional);
}

#[test]
fn python_qt_members_record_class_and_override_context_attributes() {
    let store = store_from_python_source(concat!(
        "class Rows(QAbstractTableModel):\n",
        "    def rowCount(self, parent: QModelIndex) -> int:\n",
        "        return 0\n",
        "\n",
        "    def refreshPreviewPane(self) -> None:\n",
        "        pass\n",
    ));

    let row_count = store
        .symbols
        .iter()
        .find(|symbol| symbol.name == "rowCount")
        .unwrap();
    let refresh_preview = store
        .symbols
        .iter()
        .find(|symbol| symbol.name == "refreshPreviewPane")
        .unwrap();

    assert!(has_attribute(row_count, "python.qt_class_context"));
    assert!(has_attribute(row_count, "python.qt_override_context"));
    assert!(has_attribute(refresh_preview, "python.qt_class_context"));
    assert!(!has_attribute(
        refresh_preview,
        "python.qt_override_context"
    ));
}

#[test]
fn extracts_module_fact_for_non_utf8_file() {
    let dir = tempdir().unwrap();
    fs::write(dir.path().join("bad.py"), [0xff, 0xfe, 0xfd]).unwrap();
    let state = scan_workspace(dir.path(), &[]).unwrap();
    let store = extract_text_evidence(&state).unwrap();

    assert!(store
        .module_units
        .iter()
        .any(|module| module.path == "bad.py"));
    assert!(store.text_spans.is_empty());
}

#[test]
fn extracts_python_alias_and_extended_rust_panic_facts() {
    let dir = tempdir().unwrap();
    fs::write(
        dir.path().join("module.py"),
        "import numpy as np\nfrom collections.abc import Mapping as MappingAlias\n",
    )
    .unwrap();
    fs::write(
        dir.path().join("lib.rs"),
        "pub fn fail() {\n\
    panic!(\"secret\");\n\
    value.expect(\"secret\");\n\
    todo!();\n\
    unimplemented!();\n\
}\n",
    )
    .unwrap();
    let state = scan_workspace(dir.path(), &[]).unwrap();
    let store = extract_text_evidence(&state).unwrap();

    assert!(store
        .dependency_edges
        .iter()
        .any(|edge| edge.source == "numpy"
            && edge.imported == "numpy"
            && edge.alias.as_deref() == Some("np")));
    assert!(store
        .dependency_edges
        .iter()
        .any(|edge| edge.source == "collections.abc"
            && edge.imported == "Mapping"
            && edge.alias.as_deref() == Some("MappingAlias")));
    assert!(
        store
            .expressions
            .iter()
            .filter(|expr| expr.kind == ExpressionKind::Panic)
            .count()
            >= 4
    );
}

#[test]
fn distinguishes_module_docs_from_symbol_docs() {
    let dir = tempdir().unwrap();
    fs::write(
        dir.path().join("api.c"),
        "/**\n * 运行\n */\nint run(void);\n",
    )
    .unwrap();
    fs::write(dir.path().join("lib.rs"), "//! 模块说明\npub fn run() {}\n").unwrap();
    let state = scan_workspace(dir.path(), &[]).unwrap();
    let store = extract_text_evidence(&state).unwrap();

    let c_module = store
        .module_units
        .iter()
        .find(|module| module.path == "api.c")
        .unwrap();
    let rust_module = store
        .module_units
        .iter()
        .find(|module| module.path == "lib.rs")
        .unwrap();

    assert!(!c_module.has_module_doc_region);
    assert!(rust_module.has_module_doc_region);
    assert_eq!(
        store
            .doc_regions
            .iter()
            .filter(|doc| doc.file_id == c_module.file_id)
            .count(),
        1
    );
    assert!(store.symbols.iter().any(|symbol| symbol.name == "run"
        && symbol.file_id == c_module.file_id
        && symbol.doc_region_id.is_some()));
    assert!(store.symbols.iter().any(|symbol| symbol.name == "run"
        && symbol.file_id == rust_module.file_id
        && symbol.doc_region_id.is_none()));
}
