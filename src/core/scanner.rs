use std::fs::{self, File};
use std::io::Read;
use std::path::{Path, PathBuf};

use crate::core::error::{CoreError, Result};
use crate::core::issue::Language;

/// 保存一次工作区扫描得到的文件清单和指纹
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct WorkspaceState {
    /// 扫描根目录
    pub root: PathBuf,
    /// 用户请求扫描的规范化目标路径
    pub target: PathBuf,
    /// 本次扫描关联的 profile ID
    pub profile_id: String,
    /// 扫描命中的源文件列表
    pub files: Vec<FileUnit>,
    /// 由文件路径和内容指纹生成的工作区指纹
    pub fingerprint: String,
}

/// 保存单个源文件的扫描结果
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FileUnit {
    /// 文件事实 ID
    pub id: String,
    /// 文件系统绝对路径
    pub path: PathBuf,
    /// 相对扫描根目录的统一路径
    pub relative_path: String,
    /// 文件语言
    pub language: Language,
    /// 是否识别为生成文件
    pub generated: bool,
    /// 是否从后续评估中排除
    pub excluded: bool,
    /// 文件内容指纹
    pub fingerprint: String,
}

/// 扫描文件或目录并返回可供证据提取使用的工作区状态
pub fn scan_workspace(target: &Path, exclude_dirs: &[&str]) -> Result<WorkspaceState> {
    let target_exists = target.try_exists().map_err(|source| CoreError::Io {
        path: target.display().to_string(),
        source,
    })?;
    if !target_exists {
        return Err(CoreError::MissingTarget(target.display().to_string()));
    }

    let target = canonicalize(target)?;
    let root = if target.is_file() {
        target
            .parent()
            .map(Path::to_path_buf)
            .unwrap_or_else(|| PathBuf::from("."))
    } else {
        target.clone()
    };

    let mut files = Vec::new();
    if target.is_file() {
        collect_file(&root, &target, &mut files)?;
    } else {
        collect_dir(&root, &target, exclude_dirs, &mut files)?;
    }
    files.sort_by(|left, right| left.relative_path.cmp(&right.relative_path));

    let mut workspace_hasher = blake3::Hasher::new();
    for file in &files {
        workspace_hasher.update(file.relative_path.as_bytes());
        workspace_hasher.update(b"\0");
        workspace_hasher.update(file.fingerprint.as_bytes());
        workspace_hasher.update(b"\0");
    }

    Ok(WorkspaceState {
        root,
        target,
        profile_id: "default".to_string(),
        files,
        fingerprint: format!("blake3:{}", workspace_hasher.finalize().to_hex()),
    })
}

fn collect_dir(
    root: &Path,
    dir: &Path,
    exclude_dirs: &[&str],
    files: &mut Vec<FileUnit>,
) -> Result<()> {
    let mut entries = fs::read_dir(dir)
        .map_err(|source| CoreError::Io {
            path: dir.display().to_string(),
            source,
        })?
        .collect::<std::io::Result<Vec<_>>>()
        .map_err(|source| CoreError::Io {
            path: dir.display().to_string(),
            source,
        })?;
    entries.sort_by_key(|entry| entry.path());

    for entry in entries {
        let path = entry.path();
        let file_type = entry.file_type().map_err(|source| CoreError::Io {
            path: path.display().to_string(),
            source,
        })?;

        if file_type.is_dir() {
            if is_excluded_dir(&path, exclude_dirs) {
                continue;
            }
            collect_dir(root, &path, exclude_dirs, files)?;
        } else if file_type.is_file() {
            collect_file(root, &path, files)?;
        }
    }

    Ok(())
}

fn collect_file(root: &Path, path: &Path, files: &mut Vec<FileUnit>) -> Result<()> {
    let Some(language) = language_for_path(path) else {
        return Ok(());
    };

    let relative_path = relative_path(root, path);
    let generated = (matches!(language, Language::C | Language::Cpp)
        && generated_file_marker(path)?)
        || (language == Language::Typescript && is_generated_typescript(&relative_path));
    let fingerprint = fingerprint_file(path)?;
    let id = format!("file:{}", blake3::hash(relative_path.as_bytes()).to_hex());

    files.push(FileUnit {
        id,
        path: path.to_path_buf(),
        relative_path,
        language,
        generated,
        excluded: false,
        fingerprint,
    });

    Ok(())
}

fn generated_file_marker(path: &Path) -> Result<bool> {
    let mut file = File::open(path).map_err(|source| CoreError::Io {
        path: path.display().to_string(),
        source,
    })?;
    let mut bytes = Vec::new();
    file.by_ref()
        .take(8192)
        .read_to_end(&mut bytes)
        .map_err(|source| CoreError::Io {
            path: path.display().to_string(),
            source,
        })?;
    let header = String::from_utf8(bytes).unwrap_or_default();
    Ok(is_generated_source(path, &header))
}

fn is_generated_source(path: &Path, content: &str) -> bool {
    let file_name = path
        .file_name()
        .and_then(|name| name.to_str())
        .unwrap_or_default()
        .to_ascii_lowercase();

    let header = content.to_ascii_lowercase();

    file_name.ends_with(".pb.cc")
        || file_name.ends_with(".pb.h")
        || header.contains("do not edit")
        || header.contains("automatically generated")
        || header.contains("generated by")
        || header.contains("amalgamation")
        || header.contains("single source file, bootstrap version")
}

fn language_for_path(path: &Path) -> Option<Language> {
    let extension = path.extension()?.to_str()?.to_ascii_lowercase();
    match extension.as_str() {
        "py" => Some(Language::Python),
        "rs" => Some(Language::Rust),
        "c" | "h" => Some(Language::C),
        "cc" | "cpp" | "cxx" | "hpp" | "hh" | "hxx" => Some(Language::Cpp),
        "ts" | "tsx" | "mts" | "cts" => Some(Language::Typescript),
        _ => None,
    }
}

/// 判断 TypeScript 文件是否为声明文件等生成产物
fn is_generated_typescript(relative_path: &str) -> bool {
    relative_path.ends_with(".d.ts")
}

fn is_excluded_dir(path: &Path, exclude_dirs: &[&str]) -> bool {
    let Some(name) = path.file_name().and_then(|name| name.to_str()) else {
        return false;
    };
    exclude_dirs
        .iter()
        .any(|excluded| excluded_dir_matches(name, excluded))
}

#[cfg(windows)]
fn excluded_dir_matches(name: &str, excluded: &str) -> bool {
    name.eq_ignore_ascii_case(excluded)
}

#[cfg(not(windows))]
fn excluded_dir_matches(name: &str, excluded: &str) -> bool {
    name == excluded
}

fn relative_path(root: &Path, path: &Path) -> String {
    path.strip_prefix(root)
        .unwrap_or(path)
        .to_string_lossy()
        .replace('\\', "/")
}

fn canonicalize(path: &Path) -> Result<PathBuf> {
    fs::canonicalize(path).map_err(|source| CoreError::Io {
        path: path.display().to_string(),
        source,
    })
}

fn fingerprint_file(path: &Path) -> Result<String> {
    let mut file = File::open(path).map_err(|source| CoreError::Io {
        path: path.display().to_string(),
        source,
    })?;
    let mut hasher = blake3::Hasher::new();
    let mut buffer = [0_u8; 64 * 1024];

    loop {
        let bytes_read = file.read(&mut buffer).map_err(|source| CoreError::Io {
            path: path.display().to_string(),
            source,
        })?;
        if bytes_read == 0 {
            break;
        }
        hasher.update(&buffer[..bytes_read]);
    }

    Ok(format!("blake3:{}", hasher.finalize().to_hex()))
}
