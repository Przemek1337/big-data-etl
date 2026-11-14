import zipfile
from pathlib import Path


class UnexpectedArchiveError(RuntimeError):
    pass


def unpack_if_archive(path: Path, target_dir: Path) -> Path:
    if path.suffix.lower() != ".zip":
        return path
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(members) != 1:
            raise UnexpectedArchiveError(
                f"Expected exactly one CSV in {path.name}, found {len(members)}"
            )
        extracted = Path(archive.extract(members[0], target_dir))
    path.unlink()
    return extracted
