import os
from constants import NOTES_DIR, EXT
from note import Note

class Repository:

    def __init__(self, notes_dir=NOTES_DIR, extension=EXT):
        self.notes_dir = notes_dir
        self.extension = extension
        self.notes = []
        os.makedirs(self.notes_dir, exist_ok=True)
        self.load_all_notes()

    def _find_notes_recursively(self, directory):
        found_notes = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(self.extension):
                    relative_path = os.path.relpath(os.path.join(root, file), self.notes_dir)
                    found_notes.append(Note(relative_path))
        return found_notes

    def load_all_notes(self):
        self.notes = self._find_notes_recursively(self.notes_dir)
        self.notes.sort(key=lambda n: n.relative_path)

    def get_all_notes(self):
        return self.notes

    def get_note_by_relative_path(self, relative_path):
        for note in self.notes:
            if note.relative_path.lower() == relative_path.lower():
                return note
        return None

    def create_note(self, relative_path, initial_content=''):
        full_path = os.path.join(self.notes_dir, relative_path)
        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(initial_content)
            new_note = Note(relative_path)
            self.notes.append(new_note)
            self.notes.sort(key=lambda n: n.relative_path)
            return new_note
        except OSError as e:
            print(f'Error creating note {full_path}: {e}')
            return None

    def delete_note(self, note_obj):
        if note_obj not in self.notes:
            print(f'Note {note_obj.relative_path} not in repository.')
            return False
        full_path = os.path.join(self.notes_dir, note_obj.relative_path)
        try:
            os.remove(full_path)
            current_dir = os.path.dirname(full_path)
            while current_dir != self.notes_dir and (not os.listdir(current_dir)):
                os.rmdir(current_dir)
                current_dir = os.path.dirname(current_dir)
            self.notes.remove(note_obj)
            return True
        except OSError as e:
            print(f'Error deleting note {full_path}: {e}')
            return False

    def rename_note(self, note_obj, new_relative_path):
        if note_obj not in self.notes:
            print(f'Note {note_obj.relative_path} not in repository.')
            return False
        old_full_path = os.path.join(self.notes_dir, note_obj.relative_path)
        new_full_path = os.path.join(self.notes_dir, new_relative_path)
        if os.path.exists(new_full_path):
            print(f'Target path {new_full_path} already exists.')
            return False
        try:
            os.makedirs(os.path.dirname(new_full_path), exist_ok=True)
            os.rename(old_full_path, new_full_path)
            note_obj.relative_path = new_relative_path
            current_dir = os.path.dirname(old_full_path)
            while current_dir != self.notes_dir and os.path.exists(current_dir) and (not os.listdir(current_dir)):
                os.rmdir(current_dir)
                current_dir = os.path.dirname(current_dir)
            self.notes.sort(key=lambda n: n.relative_path)
            return True
        except OSError as e:
            print(f'Error renaming note {old_full_path} to {new_full_path}: {e}')
            return False

    def save_note_content(self, note_obj, content):
        full_path = os.path.join(self.notes_dir, note_obj.relative_path)
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except OSError as e:
            print(f'Error saving note {full_path}: {e}')
            return False

    def load_note_content(self, note_obj):
        full_path = os.path.join(self.notes_dir, note_obj.relative_path)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f'File not found: {full_path}')
            return ''
        except OSError as e:
            print(f'Error loading note {full_path}: {e}')
            return ''

    def ensure_note_extension(self, path_or_filename):
        if not path_or_filename.lower().endswith(self.extension):
            return path_or_filename + self.extension
        return path_or_filename

    def generate_unique_relative_path(self, desired_relative_path):
        base, ext = os.path.splitext(desired_relative_path)
        if ext.lower() != self.extension.lower():
            base = desired_relative_path
            ext = self.extension
        path_to_check = base + ext
        counter = 1
        while self.get_note_by_relative_path(path_to_check):
            path_to_check = f'{base}_{counter}{ext}'
            counter += 1
        return path_to_check

    def get_notes_dir(self):
        return self.notes_dir