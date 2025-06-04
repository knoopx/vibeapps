from pathlib import Path
from typing import Set, Dict, Iterator, ValuesView, ItemsView, Optional
from collection import Collection


class CollectionManager:

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = Path(base_dir)
        self._collections: Dict[str, Collection] = {}
        self._load_all_collections()

    def _load_all_collections(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        for file_path in self.base_dir.glob("*.json"):
            self._collections[file_path.stem] = Collection(file_path)

    def _load_collection(self, name: str) -> Collection:
        if name not in self._collections:
            collection_file = self.base_dir / f"{name}.json"
            self._collections[name] = Collection(collection_file)
        return self._collections[name]

    def keys(self) -> Set[str]:
        return set(self._collections.keys())

    def __getitem__(self, name: str) -> Collection:
        return self._load_collection(name)

    def __setitem__(self, name: str, collection: Collection) -> None:
        self._collections[name] = collection

    def __delitem__(self, name: str) -> None:
        if name in self._collections:
            collection = self._collections[name]
            try:
                if collection.file.exists():
                    collection.file.unlink()
                del self._collections[name]
            except OSError:
                raise KeyError(f"Collection '{name}' could not be deleted")
        else:
            raise KeyError(f"Collection '{name}' not found")

    def __contains__(self, name: str) -> bool:
        return name in self._collections

    def __iter__(self) -> Iterator[str]:
        return iter(sorted(self._collections.keys()))

    def __len__(self) -> int:
        return len(self._collections)

    def values(self) -> ValuesView[Collection]:
        return self._collections.values()

    def items(self) -> ItemsView[str, Collection]:
        return self._collections.items()

    def get(
        self, name: str, default: Optional[Collection] = None
    ) -> Optional[Collection]:
        try:
            return self[name]
        except KeyError:
            return default

    def lookup(self, release_path: str) -> list[Collection]:
        collections = [
            collection
            for collection in self._collections.values()
            if collection.contains(release_path)
        ]
        return sorted(collections, key=lambda c: c.name)
