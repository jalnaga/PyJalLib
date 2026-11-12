#!/usr/bin/env python3

import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlsplit


class ResolveError(Exception):
    pass


def read_json(inPath):
    if not inPath.is_file() or inPath.is_symlink():
        raise ResolveError(f"필수 JSON 파일이 없습니다: {inPath}")
    try:
        value = json.loads(inPath.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ResolveError(f"JSON 파일을 읽을 수 없습니다: {inPath}: {error}") from error
    if not isinstance(value, dict):
        raise ResolveError(f"JSON 최상위 값이 객체가 아닙니다: {inPath}")
    return value


def safe_file(inRoot, inRelative):
    # 검증 사본의 루트나 바로 위 디렉터리를 바꿔 경로 검사를 우회하지 못하게 한다.
    if inRoot.is_symlink() or inRoot.parent.is_symlink():
        raise ResolveError(f"참조 루트에 심볼릭 링크가 있습니다: {inRoot}")
    if not isinstance(inRelative, str):
        raise ResolveError("reference map 경로가 문자열이 아닙니다.")
    relative = PurePosixPath(inRelative)
    if relative.is_absolute() or PureWindowsPath(inRelative).drive or "\\" in inRelative or not relative.parts or any(part in (".", "..") for part in relative.parts):
        raise ResolveError(f"허용하지 않는 경로입니다: {inRelative}")
    path = inRoot
    for part in relative.parts:
        path = path / part
        if path.is_symlink():
            raise ResolveError(f"참조 경로에 심볼릭 링크가 있습니다: {path}")
    if not path.is_file():
        raise ResolveError(f"참조 파일이 없습니다: {path}")
    return path


# ---------------------------------------------------------------------------
# OKF frontmatter

FRONTMATTER_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_.-]*)\s*:(?:\s+(.*?))?\s*$")
LIST_ITEM = re.compile(r"^\s*-\s+(.*?)\s*$")


def frontmatter_value(inRaw):
    """frontmatter 단일 값을 해석한다. JSON 흐름 값은 json으로, 나머지는 문자열로 읽는다."""
    value = inRaw.strip()
    if value[:1] in ('"', "[", "{"):
        try:
            return json.loads(value)
        except json.JSONDecodeError as error:
            raise ResolveError(f"frontmatter 값을 해석할 수 없습니다: {value}: {error}") from error
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    return value


def parse_frontmatter(inText):
    """`---`로 감싼 frontmatter를 (dict, 본문)으로 나눈다. frontmatter가 없으면 (None, 원문)이다."""
    text = inText[1:] if inText.startswith("\ufeff") else inText
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n").rstrip() != "---":
        return None, inText
    metadata = {}
    current = None
    for index in range(1, len(lines)):
        line = lines[index].rstrip("\r\n")
        if line.rstrip() == "---":
            return metadata, "".join(lines[index + 1:])
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = LIST_ITEM.match(line)
        if item and current is not None and isinstance(metadata.get(current), list):
            metadata[current].append(frontmatter_value(item.group(1)))
            continue
        if line[:1] in (" ", "\t"):
            # 들여쓴 중첩 값은 최상위 키가 아니므로 오류 없이 넘긴다.
            continue
        match = FRONTMATTER_KEY.match(line)
        if not match:
            raise ResolveError(f"frontmatter 줄을 해석할 수 없습니다: {line}")
        key, raw = match.group(1), match.group(2)
        if raw is None or not raw.strip():
            # 값이 없으면 다음 `- item` 줄을 리스트로 모은다. 중첩 매핑이면 빈 리스트로 남는다.
            metadata[key] = []
            current = key
        else:
            metadata[key] = frontmatter_value(raw)
            current = None
    raise ResolveError("frontmatter가 `---`로 닫히지 않았습니다.")


# ---------------------------------------------------------------------------
# 지식 색인 (OKF 번들과 구형 reference map)

BUNDLE = ".agents/references"
OKF_INDEX_PATH = BUNDLE + "/index.md"
INDEX_PATH = BUNDLE + "/reference-map.json"
METADATA_FIELDS = ("summary", "applies_when", "read_before")
RESERVED_NAMES = ("index.md", "log.md")
STATUSES = ("draft", "stable", "deprecated")
DOMAIN_NAME = re.compile(r"[a-z][a-z0-9-]*")


def heading_title(inBody):
    for line in inBody.splitlines():
        match = re.match(r"^#\s+(.+?)\s*#*\s*$", line)
        if match:
            return match.group(1).strip()
    return None


def text_field(inValue):
    """색인 필드는 문자열로 낸다. 리스트는 항목을 이어 붙인다."""
    if isinstance(inValue, str):
        return inValue.strip() or None
    if isinstance(inValue, list):
        items = [str(item).strip() for item in inValue if str(item).strip()]
        return "; ".join(items) or None
    return None


def concept_entry(inRelative, inText):
    """concept 문서의 frontmatter를 검사해 색인 정보를 만든다."""
    metadata, body = parse_frontmatter(inText)
    if metadata is None:
        raise ResolveError(f"OKF concept에 frontmatter가 없습니다: {inRelative}")
    kind = metadata.get("type")
    if not isinstance(kind, str) or not kind.strip():
        raise ResolveError(f"OKF concept의 type이 없습니다: {inRelative}")
    status = metadata.get("status", "stable")
    if status not in STATUSES:
        raise ResolveError(f"OKF concept의 status가 올바르지 않습니다: {inRelative}: {status}")
    title = metadata.get("title")
    title = title.strip() if isinstance(title, str) and title.strip() else heading_title(body) or PurePosixPath(inRelative).stem
    entry = {
        "relative_path": inRelative, "title": title, "type": kind.strip(), "status": status,
        "summary": text_field(metadata.get("description")),
        "applies_when": text_field(metadata.get("applies_when")),
        "read_before": text_field(metadata.get("read_before")),
    }
    entry["metadata_missing"] = not all(entry[field] for field in METADATA_FIELDS)
    return entry


def is_okf_root(inRoot):
    """루트 index.md frontmatter에 okf_version이 있으면 OKF 번들이다."""
    path = inRoot / OKF_INDEX_PATH
    if not path.is_file() or path.is_symlink():
        return False
    try:
        metadata, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        return False
    return isinstance(metadata, dict) and "okf_version" in metadata


def bundle_files(inRoot):
    """번들 아래 파일의 상대 경로 목록. 심볼릭 링크는 거부한다."""
    base = inRoot / BUNDLE
    if base.is_symlink():
        raise ResolveError(f"참조 경로에 심볼릭 링크가 있습니다: {base}")
    found = []
    for directory, folders, names in os.walk(base):
        current = Path(directory)
        for name in folders:
            if (current / name).is_symlink():
                raise ResolveError(f"참조 경로에 심볼릭 링크가 있습니다: {current / name}")
        for name in names:
            path = current / name
            if path.is_symlink():
                raise ResolveError(f"참조 경로에 심볼릭 링크가 있습니다: {path}")
            found.append(path.relative_to(inRoot).as_posix())
    return sorted(found)


def is_concept_path(inRelative):
    path = PurePosixPath(inRelative)
    return path.suffix == ".md" and path.name not in RESERVED_NAMES


def is_common_path(inRelative):
    parts = PurePosixPath(inRelative).relative_to(BUNDLE).parts
    return not (parts and parts[0] == "domains")


def domain_title(inText, inDomain):
    _, body = parse_frontmatter(inText)
    return heading_title(body) or inDomain


def okf_index(inRoot, inDomains):
    """OKF 번들에서 공통 concept 색인과 선택 도메인 index를 구성한다."""
    root_index = safe_file(inRoot, OKF_INDEX_PATH)
    metadata, _ = parse_frontmatter(root_index.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict) or "okf_version" not in metadata:
        raise ResolveError("중앙 OKF 루트 index.md에 okf_version이 없습니다.")
    files = bundle_files(inRoot)
    documents = []
    common = []
    for relative in files:
        if not is_common_path(relative) or not is_concept_path(relative):
            continue
        entry = concept_entry(relative, safe_file(inRoot, relative).read_text(encoding="utf-8"))
        if entry["status"] == "deprecated":
            continue
        common.append(relative)
        documents.append({"path": str(inRoot / relative), **entry})
    domain_indexes = []
    domain_paths = []
    for domain in inDomains:
        prefix = f"{BUNDLE}/domains/{domain}/"
        index = prefix + "index.md"
        if not DOMAIN_NAME.fullmatch(domain) or index not in files:
            raise ResolveError(f"등록되지 않은 도메인입니다: {domain}")
        text = safe_file(inRoot, index).read_text(encoding="utf-8")
        domain_indexes.append({"domain": domain, "path": str(inRoot / index), "relative_path": index, "title": domain_title(text, domain)})
        domain_paths.extend(relative for relative in files if relative.startswith(prefix) and PurePosixPath(relative).name == "index.md")
    paths = list(dict.fromkeys(["AGENTS.md", OKF_INDEX_PATH, *common, *domain_paths]))
    for relative in paths:
        safe_file(inRoot, relative)
    return paths, documents, domain_indexes


def okf_generated(inConcepts, inDomains):
    """루트 index.md와 host-adapters/index.md의 생성 내용을 만든다.

    inConcepts는 공통 concept 색인 항목 목록, inDomains는 (도메인, 제목) 목록이다.
    """
    def line(inEntry, inBase):
        target = PurePosixPath(inEntry["relative_path"]).relative_to(inBase).as_posix()
        return f"* [{inEntry['title']}]({target}) - {inEntry['summary'] or inEntry['type']}"

    adapters_base = f"{BUNDLE}/host-adapters"
    adapters = [entry for entry in inConcepts if entry["relative_path"].startswith(adapters_base + "/")]
    others = [entry for entry in inConcepts if entry not in adapters]
    active = [entry for entry in others if entry["status"] != "deprecated"]
    retired = [entry for entry in others if entry["status"] == "deprecated"]
    notice = "이 파일은 `project-workflow.py index`가 concept frontmatter로 생성한다. 직접 고치지 말고 문서 frontmatter를 갱신한 뒤 다시 생성한다."
    lines = ['---', 'okf_version: "0.2"', '---', '', '# 중앙 지식 색인', '', notice, '', '## 공통 지침', '']
    lines += [line(entry, BUNDLE) for entry in active]
    if adapters:
        lines.append("* [호스트 어댑터](host-adapters/index.md) - 호스트별 작업공간·역할 실행·질문·종료와 지원 한계")
    if retired:
        lines += ['', '## 폐기 문서', '']
        lines += [line(entry, BUNDLE) for entry in retired]
    lines += ['', '## 도메인', '']
    if inDomains:
        lines += [f"* [{title}](domains/{domain}/index.md) - {domain} 도메인 지식 색인" for domain, title in inDomains]
    else:
        lines.append("등록된 도메인이 없습니다. `domains/<도메인>/index.md`를 만들면 도메인으로 등록됩니다.")
    generated = {OKF_INDEX_PATH: "\n".join(lines) + "\n"}
    if adapters:
        body = ['# 호스트 어댑터', '', notice, '']
        body += [line(entry, adapters_base) for entry in adapters]
        generated[adapters_base + "/index.md"] = "\n".join(body) + "\n"
    return generated


def okf_bundle_state(inRoot):
    """디스크의 번들에서 생성 색인 입력(공통 concept 전체와 도메인)을 읽는다."""
    files = bundle_files(inRoot)
    concepts = [
        concept_entry(relative, safe_file(inRoot, relative).read_text(encoding="utf-8"))
        for relative in files if is_common_path(relative) and is_concept_path(relative)
    ]
    domains = []
    for relative in files:
        parts = PurePosixPath(relative).relative_to(BUNDLE).parts
        if len(parts) == 3 and parts[0] == "domains" and parts[2] == "index.md":
            domains.append((parts[1], domain_title(safe_file(inRoot, relative).read_text(encoding="utf-8"), parts[1])))
    return concepts, domains


EXTERNAL_EXCLUDED = (".agents", ".git", ".ai_planning", "repos", "worktrees")


def git_root_files(inRoot):
    """inRoot가 독립 Git 루트면 추적 파일 목록, 아니면 None."""
    top = subprocess.run(["git", "-C", str(inRoot), "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False)
    if top.returncode != 0 or not top.stdout.strip() or Path(top.stdout.strip()).resolve() != Path(inRoot).resolve():
        return None
    listed = subprocess.run(["git", "-C", str(inRoot), "-c", "core.quotepath=false", "ls-files", "-z"], capture_output=True, check=False)
    if listed.returncode != 0:
        return None
    return sorted(item.decode("utf-8") for item in listed.stdout.split(b"\0") if item)


def external_bundles(inRoot):
    """중앙 루트의 .agents 등 밖에서 루트 index.md에 okf_version이 있는 최상위 디렉터리 목록."""
    root = Path(inRoot)
    files = git_root_files(root)
    if files is None:
        files = []
        for directory, folders, names in os.walk(root):
            current = Path(directory)
            relative = current.relative_to(root).as_posix()
            if relative == ".":
                folders[:] = [name for name in folders if name not in EXTERNAL_EXCLUDED]
            # 중첩된 별도 Git 저장소는 중앙 지식이 아니다.
            folders[:] = [name for name in folders if not (current / name / ".git").exists() and not (current / name).is_symlink()]
            files.extend((current / name).relative_to(root).as_posix() for name in names)
    found = []
    for relative in files:
        path = PurePosixPath(relative)
        if path.name != "index.md" or len(path.parts) < 2 or path.parts[0] in EXTERNAL_EXCLUDED:
            continue
        directory = path.parent.as_posix()
        if any(directory == parent or directory.startswith(parent + "/") for parent in found):
            continue
        target = root / relative
        if target.is_symlink() or not target.is_file():
            continue
        try:
            metadata, _ = parse_frontmatter(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ResolveError):
            continue
        if isinstance(metadata, dict) and "okf_version" in metadata:
            found = [parent for parent in found if not parent.startswith(directory + "/")]
            found.append(directory)
    return sorted(found)


def reference_index(inRoot, inDomains):
    """경로 검증과 본문 읽기를 구분해 적용되는 색인만 구성한다."""
    mapping = read_json(safe_file(inRoot, INDEX_PATH))
    common, domains = mapping.get("common"), mapping.get("domains")
    if mapping.get("schema_version") != 1 or not isinstance(common, list) or not isinstance(domains, dict) or not all(isinstance(entries, list) for entries in domains.values()):
        raise ResolveError("중앙 reference map 형식이 올바르지 않습니다.")
    registered = common + [relative for entries in domains.values() for relative in entries]
    for relative in registered:
        if not isinstance(relative, str) or not relative or PurePosixPath(relative).is_absolute() or any(part in (".", "..") for part in relative.split("/")):
            raise ResolveError(f"허용하지 않는 reference map 경로입니다: {relative}")
    metadata = mapping.get("documents", {})
    if not isinstance(metadata, dict):
        raise ResolveError("중앙 문서 색인 형식이 올바르지 않습니다.")
    for relative, entry in metadata.items():
        if relative not in registered or not isinstance(entry, dict) or not all(isinstance(entry.get(field), str) and entry[field].strip() for field in METADATA_FIELDS):
            raise ResolveError(f"중앙 문서 색인 정보가 올바르지 않습니다: {relative}")
    selected = list(common)
    for domain in inDomains:
        entries = domains.get(domain)
        if entries is None:
            raise ResolveError(f"등록되지 않은 도메인입니다: {domain}")
        selected.extend(entries)
    paths = list(dict.fromkeys(["AGENTS.md", INDEX_PATH, *selected]))
    for relative in paths:
        safe_file(inRoot, relative)
    documents = []
    for relative in dict.fromkeys(selected):
        entry = metadata.get(relative)
        documents.append({
            "path": str(inRoot / relative), "relative_path": relative,
            "title": None, "type": None, "status": None,
            **{field: entry[field] if entry is not None else None for field in METADATA_FIELDS},
            "metadata_missing": entry is None,
        })
    return paths, documents


def knowledge_index(inRoot, inDomains):
    """중앙 형식을 판별해 (검증 경로, 문서 색인, 도메인 index, 색인 경로)를 돌려준다."""
    if is_okf_root(inRoot):
        paths, documents, domain_indexes = okf_index(inRoot, inDomains)
        return paths, documents, domain_indexes, OKF_INDEX_PATH
    paths, documents = reference_index(inRoot, inDomains)
    return paths, documents, [], INDEX_PATH


def reference_files(inRoot, inDomains):
    return knowledge_index(inRoot, inDomains)[0]


def central_version(inRoot):
    return checked_version(safe_file(inRoot, ".jal-harness-version").read_text(encoding="utf-8").strip())


def checked_version(inVersion):
    if not isinstance(inVersion, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", inVersion):
        raise ResolveError("중앙 버전 형식이 올바르지 않습니다.")
    return inVersion


def reading_result(inProject, inRoot, inIndex, inVersion):
    selected, documents, domain_indexes, index_path = inIndex
    verified = [str(inRoot / relative) for relative in selected]
    return {
        "startup_files": [str(safe_file(inProject, "AGENTS.md")), str(inRoot / "AGENTS.md")],
        "index_path": str(inRoot / index_path),
        "documents": documents,
        "domain_indexes": domain_indexes,
        "verified_files": verified,
        "files": verified,
        "files_usage": "검증 대상 경로입니다. 전체 본문 읽기 목록이 아닙니다. 시작 시 startup_files와 documents 색인만 읽고, 도메인 본문은 domain_indexes의 index에서 필요한 것만 선택하세요.",
        "central_version": inVersion,
    }


# ---------------------------------------------------------------------------
# Git과 원격 중앙

def git_output(inRoot, *inArgs):
    result = subprocess.run(["git", "-C", str(inRoot), *inArgs], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise ResolveError(result.stderr.strip() or "Git 저장소를 확인할 수 없습니다.")
    return result.stdout.strip()


def git_common_dir(inProject):
    return Path(git_output(inProject, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()


def central_revision(inCentral, inPaths):
    # 버전 변경도 중앙 근거에 포함하되 구형 snapshot 파일 집합은 바꾸지 않는다.
    inPaths = list(dict.fromkeys([*inPaths, ".jal-harness-version"]))
    result = subprocess.run(["git", "-C", str(inCentral), "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    head = result.stdout.strip() if result.returncode == 0 else "unborn"
    status = subprocess.run(["git", "-C", str(inCentral), "status", "--porcelain", "--", *inPaths], capture_output=True, text=True, check=False)
    if status.returncode != 0:
        raise ResolveError(status.stderr.strip() or "중앙 Git 상태를 확인할 수 없습니다.")
    if not status.stdout.strip() and head != "unborn":
        return head
    checksum = hashlib.sha256()
    for relative in inPaths:
        checksum.update(relative.encode("utf-8"))
        checksum.update(safe_file(inCentral, relative).read_bytes())
    return f"{head}+uncommitted:{checksum.hexdigest()}"


SCP_REMOTE = re.compile(r"^(?P<user>[A-Za-z0-9._-]+)@(?P<host>[A-Za-z0-9.-]+):(?P<path>[^\s:\\]+)$")
REMOTE_SEGMENT = re.compile(r"[A-Za-z0-9._~-]+")


def remote_parts(inUrl):
    """원격 URL을 (scheme, host, 경로 조각)으로 검사한다. 자격 증명·query·fragment는 거부한다."""
    if not isinstance(inUrl, str) or not inUrl or inUrl != inUrl.strip() or any(character.isspace() for character in inUrl) or "\\" in inUrl:
        raise ResolveError(f"원격 중앙 URL 형식이 올바르지 않습니다: {inUrl!r}")
    # project.json의 값은 신뢰할 수 없으므로 git 옵션으로 해석될 수 있는 '-' 시작 값을 거부한다.
    if inUrl.startswith("-"):
        raise ResolveError(f"원격 중앙 URL은 '-'로 시작할 수 없습니다: {inUrl}")
    scp = SCP_REMOTE.match(inUrl)
    if scp and "://" not in inUrl:
        if scp.group("user").startswith("-") or scp.group("host").startswith("-"):
            raise ResolveError(f"원격 중앙 URL의 사용자·호스트는 '-'로 시작할 수 없습니다: {inUrl}")
        scheme, host, path = "scp", scp.group("host").lower(), scp.group("path")
    else:
        try:
            parsed = urlsplit(inUrl)
            port = parsed.port
        except ValueError as error:
            raise ResolveError(f"원격 중앙 URL 형식이 올바르지 않습니다: {inUrl}") from error
        scheme = parsed.scheme.lower()
        if scheme not in ("https", "ssh", "file") or parsed.query or parsed.fragment or "?" in inUrl or "#" in inUrl:
            raise ResolveError(f"허용하지 않는 원격 중앙 URL입니다(https, ssh, git@host:path, file만 허용): {inUrl}")
        if parsed.password is not None or (scheme == "https" and parsed.username is not None):
            raise ResolveError("원격 중앙 URL에 자격 증명을 넣을 수 없습니다.")
        if scheme == "file":
            if parsed.netloc not in ("", "localhost") or not parsed.path.strip("/"):
                raise ResolveError(f"file 원격 중앙 URL 형식이 올바르지 않습니다: {inUrl}")
            parts = [part for part in unquote(parsed.path).split("/") if part]
            if any(part.startswith("-") for part in parts):
                raise ResolveError(f"원격 중앙 URL 경로 조각은 '-'로 시작할 수 없습니다: {inUrl}")
            return scheme, "file", parts
        if not parsed.hostname:
            raise ResolveError(f"원격 중앙 URL에 호스트가 없습니다: {inUrl}")
        if parsed.hostname.startswith("-") or (parsed.username or "").startswith("-"):
            raise ResolveError(f"원격 중앙 URL의 사용자·호스트는 '-'로 시작할 수 없습니다: {inUrl}")
        host = parsed.hostname.lower() + (f"_{port}" if port else "")
        path = parsed.path
    segments = [part for part in path.strip("/").split("/") if part]
    if not segments or any(part in (".", "..") or part.startswith("-") or not REMOTE_SEGMENT.fullmatch(part) for part in segments):
        raise ResolveError(f"원격 중앙 URL 경로가 올바르지 않습니다: {inUrl}")
    return scheme, host, segments


def checked_remote(inUrl):
    """허용한 원격 URL만 정규화해 돌려준다. 실패하면 ResolveError."""
    scheme, _, _ = remote_parts(inUrl)
    if scheme in ("https", "ssh"):
        return inUrl.rstrip("/")
    return inUrl


def harness_home():
    configured = os.environ.get("JAL_HARNESS_HOME")
    return Path(configured).expanduser() if configured else Path("~").expanduser() / ".jal-harness"


def remote_cache_path(inUrl):
    """원격 중앙의 홈 공용 캐시 경로. file URL은 이름과 URL 해시로 구분한다."""
    normalized = checked_remote(inUrl)
    scheme, host, segments = remote_parts(normalized)
    central = harness_home() / "central"
    if scheme == "file":
        name = re.sub(r"[^A-Za-z0-9._-]", "_", segments[-1].removesuffix(".git")) or "central"
        return central / "file" / f"{name}-{hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:8]}"
    segments = [*segments[:-1], segments[-1].removesuffix(".git")]
    if not segments[-1]:
        raise ResolveError(f"원격 중앙 URL 경로가 올바르지 않습니다: {inUrl}")
    return central.joinpath(host, *segments)


# 원격 중앙 캐시의 clone·sync에 적용하는 Windows 긴 경로 설정 키
LONGPATHS_CONFIG = "core.longpaths"


def remove_tree(inPath):
    """Windows의 읽기 전용 Git 객체도 지울 수 있게 권한을 바꿔 다시 시도한다."""
    def retry(inFunction, inTarget, *_):
        os.chmod(inTarget, stat.S_IWRITE)
        inFunction(inTarget)
    if sys.version_info >= (3, 12):
        shutil.rmtree(inPath, onexc=retry)
    else:
        shutil.rmtree(inPath, onerror=retry)


def clone_remote(inUrl, inCache, inExpectedId=None):
    """임시 위치에 clone하고 중앙 식별자를 확인한 뒤 캐시 위치로 옮긴다."""
    url = checked_remote(inUrl)
    cache = Path(inCache)
    if cache.exists() or cache.is_symlink():
        raise ResolveError(f"원격 중앙 캐시 위치가 이미 있습니다: {cache}")
    cache.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{cache.name}.clone-", dir=cache.parent))
    try:
        environment = dict(os.environ, GIT_TERMINAL_PROMPT="0")
        # Windows는 core.longpaths가 꺼져 있으면 260자를 넘는 작업 트리 경로를 만들지 못한다.
        # clone 실행과 새 캐시의 로컬 설정에 모두 적용해 이후 fetch·merge·checkout도 같은 설정을 쓴다(비Windows에서는 무해).
        command = ["git", "-c", f"{LONGPATHS_CONFIG}=true", "clone", "-q", "-c", f"{LONGPATHS_CONFIG}=true", "--", url, str(staging / "repo")]
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False, env=environment, timeout=900)
        except subprocess.TimeoutExpired as error:
            raise ResolveError(f"원격 중앙 clone 시간이 초과되었습니다: {url}") from error
        if result.returncode != 0:
            raise ResolveError(f"원격 중앙을 clone할 수 없습니다: {url}: {result.stderr.strip()}")
        marker = staging / "repo/.jal-harness/central.json"
        if not marker.is_file() or marker.is_symlink():
            raise ResolveError(f"원격 저장소가 JalHarness 중앙이 아닙니다: {url}")
        identity = read_json(marker).get("id")
        if inExpectedId is not None and identity != inExpectedId:
            raise ResolveError(f"원격 중앙의 식별자가 프로젝트와 달라 clone을 삭제했습니다: {url}")
        os.replace(staging / "repo", cache)
    finally:
        remove_tree(staging)
    return cache.resolve()


def remote_status(inCentral):
    """로컬 tracking ref 기준 ahead/behind. fetch하지 않으며 upstream이 없으면 None."""
    result = subprocess.run(["git", "-C", str(inCentral), "rev-list", "--left-right", "--count", "HEAD...@{upstream}"], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None
    try:
        ahead, behind = (int(value) for value in result.stdout.split())
    except ValueError:
        return None
    return {"ahead": ahead, "behind": behind}


def is_central(inPath):
    marker = inPath / ".jal-harness/central.json"
    return inPath.is_dir() and not inPath.is_symlink() and marker.is_file() and not marker.is_symlink()


def central_result(inProject, inCentral, inManifest, inOrigin, inRemote):
    marker = read_json(safe_file(inCentral, ".jal-harness/central.json"))
    if marker.get("id") != inManifest["central_id"]:
        raise ResolveError("연결된 중앙 저장소의 식별자가 프로젝트와 다릅니다.")
    index = knowledge_index(inCentral, inManifest["domains"])
    return {
        "source": "central",
        "stale": False,
        "central_root": str(inCentral),
        "central_commit": central_revision(inCentral, index[0]),
        "central_remote": inRemote,
        "central_origin": inOrigin,
        "remote_status": remote_status(inCentral),
        "remote_error": None,
        **reading_result(inProject, inCentral, index, central_version(inCentral)),
    }


def resolve(inProject, allow_clone=True):
    project = Path(inProject).resolve()
    manifest = read_json(safe_file(project, ".jal-harness/project.json"))
    if manifest.get("schema_version") != 1 or not isinstance(manifest.get("central_id"), str) or not isinstance(manifest.get("domains"), list) or not all(isinstance(domain, str) and re.fullmatch(r"[a-z][a-z0-9-]*", domain) for domain in manifest["domains"]):
        raise ResolveError("프로젝트 연결 정보의 형식이 올바르지 않습니다.")
    remote = manifest.get("central_remote")
    if remote is not None:
        remote = checked_remote(remote)
    common = git_common_dir(project)
    connection = common / "jal-harness-central"
    candidate, origin = None, None
    if connection.exists() or connection.is_symlink():
        if connection.is_symlink() or not connection.is_file():
            raise ResolveError("중앙 로컬 연결 파일이 올바르지 않습니다.")
        candidate, origin = Path(connection.read_text(encoding="utf-8").strip()).expanduser(), "connection"
    elif common.name == ".git" and common.parent.parent.name == "repos":
        candidate, origin = common.parent.parent.parent, "repos"
    if candidate is not None and candidate.is_dir():
        return central_result(project, candidate.resolve(), manifest, origin, remote)
    remote_error = None
    if remote is not None:
        cache = remote_cache_path(remote)
        if cache.exists() or cache.is_symlink():
            if is_central(cache):
                return central_result(project, cache.resolve(), manifest, "remote-cache", remote)
            remote_error = f"원격 중앙 캐시 위치에 중앙이 아닌 항목이 있어 보존하고 사용하지 않았습니다: {cache}"
        elif allow_clone:
            try:
                cloned = clone_remote(remote, cache, manifest["central_id"])
            except (ResolveError, OSError) as error:
                remote_error = str(error)
            else:
                return central_result(project, cloned, manifest, "remote-clone", remote)
        else:
            remote_error = f"원격 중앙 캐시가 없고 clone을 생략했습니다: {cache}"
    try:
        result = snapshot_result(project, manifest)
    except ResolveError as error:
        if remote_error:
            raise ResolveError(f"{error} (원격 중앙: {remote_error})") from error
        raise
    return {**result, "central_remote": remote, "remote_error": remote_error}


def snapshot_result(inProject, inManifest):
    snapshot = inProject / ".jal-harness/snapshot/central"
    saved = read_json(safe_file(inProject, ".jal-harness/snapshot.json"))
    if saved.get("central_id") != inManifest["central_id"] or not isinstance(saved.get("files"), dict):
        raise ResolveError("검증된 중앙 지침 사본이 없습니다.")
    if snapshot.is_symlink() or snapshot.parent.is_symlink():
        raise ResolveError(f"참조 루트에 심볼릭 링크가 있습니다: {snapshot}")
    actual_files = {path.relative_to(snapshot).as_posix() for path in snapshot.rglob("*") if path.is_file() or path.is_symlink()}
    if actual_files != set(saved["files"]):
        raise ResolveError("중앙 지침 사본의 파일 목록과 실제 파일이 다릅니다.")
    # 본문을 해석하기 전에 해시를 확인해 변조된 사본을 먼저 거부한다.
    for relative, expected in saved["files"].items():
        actual = hashlib.sha256(safe_file(snapshot, relative).read_bytes()).hexdigest()
        if actual != expected:
            raise ResolveError(f"중앙 지침 사본의 해시가 다릅니다: {relative}")
    index = knowledge_index(snapshot, inManifest["domains"])
    if set(index[0]) != set(saved["files"]):
        raise ResolveError("중앙 지침 사본의 파일 목록이 다릅니다.")
    return {
        "source": "snapshot",
        "stale": True,
        "central_root": None,
        "central_commit": saved.get("central_commit", "unknown"),
        "central_remote": None,
        "central_origin": "snapshot",
        "remote_status": None,
        "remote_error": None,
        **reading_result(inProject, snapshot, index, checked_version(saved["central_version"]) if "central_version" in saved else "unknown"),
    }


def main(inArgs=None):
    args = sys.argv[1:] if inArgs is None else inArgs
    if any(arg not in ("--no-clone",) for arg in args):
        print("사용법: python3 .jal-harness/resolve.py [--no-clone]", file=sys.stderr)
        return 2
    try:
        result = resolve(Path.cwd(), allow_clone="--no-clone" not in args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except ResolveError as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
