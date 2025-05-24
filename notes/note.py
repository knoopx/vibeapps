import os
import shutil

from constants import NOTES_DIR

class Note:
    def __init__(self, relative_path):
        self._relative_path = relative_path
        self._content = None
        self._loaded = False

    @property
    def full_path(self):
        return os.path.join(NOTES_DIR, self._relative_path)

    @property
    def relative_path(self):
        return self._relative_path

    @property
    def filename(self):
        return os.path.basename(self._relative_path)

    @property
    def title(self):
        return os.path.splitext(self.filename)[0]

    @property
    def display_name(self):
        return os.path.splitext(self.relative_path)[0]

    @property
    def directory_relative(self):
        return os.path.dirname(self._relative_path)

    def exists(self):
        return os.path.exists(self.full_path)

    def load(self):
        if not self._loaded:
            if self.exists():
                try:
                    with open(self.full_path, "r") as f:
                        self._content = f.read()
                except OSError as e:
                    print(f"Error loading note {self.full_path}: {e}")
                    self._content = ""  # Ensure content is empty on error
            else:
                self._content = ""  # Note doesn't exist, content is empty
            self._loaded = True
        return self._content

    @property
    def content(self):
        return self.load()

    def save(self, content):
        try:
            os.makedirs(os.path.dirname(self.full_path), exist_ok=True)
            with open(self.full_path, "w") as f:
                f.write(content)
            self._content = content
            self._loaded = True  # Content is now loaded (and matches file)
            # print(f"Saved: {self.full_path}")
            return True
        except OSError as e:
            print(f"Error saving note {self.full_path}: {e}")
            return False

    def delete(self):
        if self.exists():
            try:
                os.remove(self.full_path)
                return True
            except OSError as e:
                print(f"Error deleting note {self.full_path}: {e}")
                return False
        return True  # Note didn't exist, so it's "deleted"

    def rename(self, new_relative_path):
        new_full_path = os.path.join(NOTES_DIR, new_relative_path)
        if self.full_path == new_full_path:
            return True  # No change needed

        if os.path.exists(new_full_path):
            print(f"Error renaming: target {new_full_path} already exists.")
            return False

        try:
            os.makedirs(os.path.dirname(new_full_path), exist_ok=True)
            if self.exists():
                shutil.move(self.full_path, new_full_path)
            self._relative_path = new_relative_path
            # Content remains the same, path changes
            return True
        except OSError as e:
            print(f"Error renaming note from {self.full_path} to {new_full_path}: {e}")
            return False

    @classmethod
    def create(cls, relative_path, initial_content=""):
        note = cls(relative_path)
        if not note.exists():
            if note.save(initial_content):
                return note
            else:
                return None  # Failed to save
        else:
            # print(f"Note {relative_path} already exists, not creating.")
            return note  # Return existing note if it somehow exists
