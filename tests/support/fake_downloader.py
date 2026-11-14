from pathlib import Path


class FakeDownloader:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def download(self, file_name: str, target_dir: Path) -> Path:
        self.calls.append(file_name)
        target = target_dir / file_name
        target.write_bytes(b"header\nrow\n")
        return target
