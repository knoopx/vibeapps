import os

class Note:

    def __init__(self, relative_path):
        self._relative_path = relative_path

    @property
    def relative_path(self):
        return self._relative_path

    @relative_path.setter
    def relative_path(self, value):
        self._relative_path = value

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

    def __repr__(self):
        return f"<Note '{self.relative_path}'>"

    def __eq__(self, other):
        if isinstance(other, Note):
            return self.relative_path == other.relative_path
        return False

    def __hash__(self):
        return hash(self.relative_path)