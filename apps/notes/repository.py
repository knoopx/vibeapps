import os
from constants import NOTES_DIR, EXT
from note import Note # Assuming Note class is in note.py

class Repository:
    def __init__(self, notes_dir=NOTES_DIR, extension=EXT):
        self.notes_dir = notes_dir
        self.extension = extension
        self.notes = []
        os.makedirs(self.notes_dir, exist_ok=True)
        self.load_all_notes()

    def _find_notes_recursively(self, directory):
        """Helper to find all note files recursively."""
        found_notes = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(self.extension):
                    relative_path = os.path.relpath(os.path.join(root, file), self.notes_dir)
                    found_notes.append(Note(relative_path))
        return found_notes

    def load_all_notes(self):
        """Loads all notes from the configured notes directory."""
        self.notes = self._find_notes_recursively(self.notes_dir)
        self.notes.sort(key=lambda n: n.relative_path) # Keep sorted

    def get_all_notes(self):
        """Returns a list of all loaded Note objects."""
        return self.notes

    def get_note_by_relative_path(self, relative_path):
        """Finds a note by its relative path."""
        for note in self.notes:
            if note.relative_path.lower() == relative_path.lower():
                return note
        return None

    def create_note(self, relative_path, initial_content=""):
        """
        Creates a new note file with initial content and adds it to the repository.
        Returns the new Note object or None if creation failed.
        """
        full_path = os.path.join(self.notes_dir, relative_path)
        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(initial_content)
            new_note = Note(relative_path)
            self.notes.append(new_note)
            self.notes.sort(key=lambda n: n.relative_path)
            return new_note
        except OSError as e:
            print(f"Error creating note {full_path}: {e}")
            return None

    def delete_note(self, note_obj):
        """
        Deletes a note file and removes it from the repository.
        Returns True if successful, False otherwise.
        """
        if note_obj not in self.notes:
            print(f"Note {note_obj.relative_path} not in repository.")
            return False

        full_path = os.path.join(self.notes_dir, note_obj.relative_path)
        try:
            os.remove(full_path)
            # Attempt to remove empty parent directories
            current_dir = os.path.dirname(full_path)
            while current_dir != self.notes_dir and not os.listdir(current_dir):
                os.rmdir(current_dir)
                current_dir = os.path.dirname(current_dir)
            self.notes.remove(note_obj)
            return True
        except OSError as e:
            print(f"Error deleting note {full_path}: {e}")
            return False

    def rename_note(self, note_obj, new_relative_path):
        """
        Renames a note file and updates its path in the repository.
        Returns True if successful, False otherwise.
        """
        if note_obj not in self.notes:
            print(f"Note {note_obj.relative_path} not in repository.")
            return False

        old_full_path = os.path.join(self.notes_dir, note_obj.relative_path)
        new_full_path = os.path.join(self.notes_dir, new_relative_path)

        if os.path.exists(new_full_path):
            print(f"Target path {new_full_path} already exists.")
            return False

        try:
            os.makedirs(os.path.dirname(new_full_path), exist_ok=True)
            os.rename(old_full_path, new_full_path)
            note_obj.relative_path = new_relative_path # Update the Note object
            # Attempt to remove empty parent directories from old path
            current_dir = os.path.dirname(old_full_path)
            while current_dir != self.notes_dir and \
                  os.path.exists(current_dir) and \
                  not os.listdir(current_dir):
                os.rmdir(current_dir)
                current_dir = os.path.dirname(current_dir)
            self.notes.sort(key=lambda n: n.relative_path)
            return True
        except OSError as e:
            print(f"Error renaming note {old_full_path} to {new_full_path}: {e}")
            return False

    def save_note_content(self, note_obj, content):
        """Saves content to the specified note file."""
        full_path = os.path.join(self.notes_dir, note_obj.relative_path)
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except OSError as e:
            print(f"Error saving note {full_path}: {e}")
            return False

    def load_note_content(self, note_obj):
        """Loads content from the specified note file."""
        full_path = os.path.join(self.notes_dir, note_obj.relative_path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            print(f"File not found: {full_path}")
            return "" # Or raise error
        except OSError as e:
            print(f"Error loading note {full_path}: {e}")
            return "" # Or raise error

    def ensure_note_extension(self, path_or_filename):
        """Ensures the filename has the correct note extension."""
        if not path_or_filename.lower().endswith(self.extension):
            return path_or_filename + self.extension
        return path_or_filename

    def generate_unique_relative_path(self, desired_relative_path):
        """
        Generates a unique relative path if the desired one exists,
        by appending a number.
        """
        base, ext = os.path.splitext(desired_relative_path)
        if ext.lower() != self.extension.lower(): # Ensure correct extension for comparison
            base = desired_relative_path # Treat as base if no/wrong extension
            ext = self.extension

        path_to_check = base + ext
        counter = 1
        while self.get_note_by_relative_path(path_to_check):
            path_to_check = f"{base}_{counter}{ext}"
            counter += 1
        return path_to_check

    def get_notes_dir(self):
        return self.notes_dir
