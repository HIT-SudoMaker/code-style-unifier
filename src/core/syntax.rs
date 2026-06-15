use tree_sitter::{Language, Node, Parser, Tree};

use crate::core::error::{CoreError, Result};

/// 语法解析支持的语言
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SyntaxLanguage {
    /// Python 源码
    Python,
    /// Rust 源码
    Rust,
    /// C 源码
    C,
    /// C++ 源码
    Cpp,
    /// TypeScript 源码
    Typescript,
}

/// 已解析源码
pub struct ParsedSource {
    tree: Tree,
}

impl ParsedSource {
    /// 返回根节点类型
    pub fn root_kind(&self) -> &str {
        self.tree.root_node().kind()
    }

    /// 返回语法树是否包含错误节点
    pub fn has_error(&self) -> bool {
        self.tree.root_node().has_error()
    }

    /// 返回语法树根节点
    pub fn root_node(&self) -> Node<'_> {
        self.tree.root_node()
    }
}

/// 解析源码为 tree-sitter 语法树
pub fn parse_source(language: SyntaxLanguage, source: &str) -> Result<ParsedSource> {
    let mut parser = Parser::new();
    let grammar = grammar_for(language);
    parser.set_language(&grammar).map_err(|error| {
        CoreError::Serialization(format!("tree-sitter language setup failed: {error}"))
    })?;
    let tree = parser.parse(source, None).ok_or_else(|| {
        CoreError::Serialization("tree-sitter parse returned no tree".to_string())
    })?;
    Ok(ParsedSource { tree })
}

fn grammar_for(language: SyntaxLanguage) -> Language {
    match language {
        SyntaxLanguage::Python => tree_sitter_python::LANGUAGE.into(),
        SyntaxLanguage::Rust => tree_sitter_rust::LANGUAGE.into(),
        SyntaxLanguage::C => tree_sitter_c::LANGUAGE.into(),
        SyntaxLanguage::Cpp => tree_sitter_cpp::LANGUAGE.into(),
        // TSX is a superset of TS; one parser handles both .ts and .tsx.
        SyntaxLanguage::Typescript => Language::new(tree_sitter_typescript::LANGUAGE_TSX),
    }
}
