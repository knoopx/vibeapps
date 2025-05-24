#!/usr/bin/env python

import sqlite3
import os
import time
import json
from typing import Dict, List, Optional, Tuple
from contextlib import contextmanager
import threading

from release import Release
from track import Track


class MusicDatabase:
    """
    SQLite-based persistence layer for the music library.
    Replaces JSONL format for better performance and query capabilities.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()

    def _init_database(self):
        """Initialize the database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Create metadata table for cache information
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            # Create releases table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS releases (
                    path TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    artist TEXT NOT NULL,
                    year INTEGER,
                    group_label TEXT,
                    starred BOOLEAN DEFAULT FALSE,
                    tags TEXT,  -- JSON array of tags
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create tracks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tracks (
                    path TEXT PRIMARY KEY,
                    release_path TEXT NOT NULL,
                    artwork_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (release_path) REFERENCES releases (path) ON DELETE CASCADE
                )
            """)

            # Create indexes for better query performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_releases_artist ON releases (artist)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_releases_title ON releases (title)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_releases_year ON releases (year)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_releases_starred ON releases (starred)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracks_release ON tracks (release_path)")

            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper locking."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable accessing columns by name
            try:
                yield conn
            finally:
                conn.close()

    def get_last_scan_time(self) -> float:
        """Get the timestamp of the last scan."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM metadata WHERE key = 'last_scan_time'")
            result = cursor.fetchone()
            return float(result['value']) if result else 0

    def set_last_scan_time(self, timestamp: float):
        """Set the timestamp of the last scan."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO metadata (key, value)
                VALUES ('last_scan_time', ?)
            """, (str(timestamp),))
            conn.commit()

    def get_cached_dirs(self) -> Dict[str, float]:
        """Get the cached directory modification times."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM metadata WHERE key = 'cached_dirs'")
            result = cursor.fetchone()
            if result:
                try:
                    return json.loads(result['value'])
                except json.JSONDecodeError:
                    return {}
            return {}

    def set_cached_dirs(self, cached_dirs: Dict[str, float]):
        """Set the cached directory modification times."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO metadata (key, value)
                VALUES ('cached_dirs', ?)
            """, (json.dumps(cached_dirs),))
            conn.commit()

    def save_release(self, release: Release):
        """Save a single release to the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Save release
            cursor.execute("""
                INSERT OR REPLACE INTO releases
                (path, title, artist, year, group_label, starred, tags, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                release.path,
                release.title,
                release.artist,
                release.year,
                release.group,
                release.starred,
                json.dumps(list(release.tags))
            ))

            # Delete existing tracks for this release
            cursor.execute("DELETE FROM tracks WHERE release_path = ?", (release.path,))

            # Save tracks
            for track in release.tracks:
                cursor.execute("""
                    INSERT INTO tracks (path, release_path, artwork_path)
                    VALUES (?, ?, ?)
                """, (track.path, release.path, track.artwork_path))

            conn.commit()

    def save_releases_batch(self, releases: List[Release]):
        """Save multiple releases in a single transaction for better performance."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Prepare release data
            release_data = []
            track_data = []
            release_paths_to_clear = []

            for release in releases:
                release_data.append((
                    release.path,
                    release.title,
                    release.artist,
                    release.year,
                    release.group,
                    release.starred,
                    json.dumps(list(release.tags))
                ))
                release_paths_to_clear.append(release.path)

                # Prepare track data
                for track in release.tracks:
                    track_data.append((track.path, release.path, track.artwork_path))

            # Delete existing tracks for all releases in this batch
            if release_paths_to_clear:
                placeholders = ','.join('?' * len(release_paths_to_clear))
                cursor.execute(f"DELETE FROM tracks WHERE release_path IN ({placeholders})",
                             release_paths_to_clear)

            # Insert releases
            cursor.executemany("""
                INSERT OR REPLACE INTO releases
                (path, title, artist, year, group_label, starred, tags, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, release_data)

            # Insert tracks
            if track_data:
                cursor.executemany("""
                    INSERT INTO tracks (path, release_path, artwork_path)
                    VALUES (?, ?, ?)
                """, track_data)

            conn.commit()

    def load_all_releases(self) -> Dict[str, Release]:
        """Load all releases from the database."""
        releases = {}

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Load releases
            cursor.execute("""
                SELECT path, title, artist, year, group_label, starred, tags
                FROM releases
                ORDER BY artist, title
            """)

            for row in cursor.fetchall():
                release = Release(row['title'], row['artist'], row['path'], row['year'])
                release.group = row['group_label']
                release.starred = bool(row['starred'])

                # Parse tags
                try:
                    release.tags = set(json.loads(row['tags'] or '[]'))
                except json.JSONDecodeError:
                    release.tags = set()

                releases[row['path']] = release

            # Load tracks for all releases
            cursor.execute("""
                SELECT path, release_path, artwork_path
                FROM tracks
                ORDER BY release_path, path
            """)

            for row in cursor.fetchall():
                release_path = row['release_path']
                if release_path in releases:
                    track = Track(row['path'])
                    track.artwork_path = row['artwork_path']
                    track.release = releases[release_path]
                    releases[release_path].tracks.append(track)

        return releases

    def load_releases_batch(self, limit: int = 500, offset: int = 0) -> Tuple[List[Release], bool]:
        """Load releases in batches for progressive loading."""
        releases = []

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Load releases with pagination
            cursor.execute("""
                SELECT path, title, artist, year, group_label, starred, tags
                FROM releases
                ORDER BY artist, title
                LIMIT ? OFFSET ?
            """, (limit, offset))

            release_rows = cursor.fetchall()
            has_more = len(release_rows) == limit

            if not release_rows:
                return [], False

            # Create release objects
            release_paths = []
            for row in release_rows:
                release = Release(row['title'], row['artist'], row['path'], row['year'])
                release.group = row['group_label']
                release.starred = bool(row['starred'])

                try:
                    release.tags = set(json.loads(row['tags'] or '[]'))
                except json.JSONDecodeError:
                    release.tags = set()

                releases.append(release)
                release_paths.append(row['path'])

            # Load tracks for these releases
            if release_paths:
                placeholders = ','.join('?' * len(release_paths))
                cursor.execute(f"""
                    SELECT path, release_path, artwork_path
                    FROM tracks
                    WHERE release_path IN ({placeholders})
                    ORDER BY release_path, path
                """, release_paths)

                # Group tracks by release
                tracks_by_release = {}
                for row in cursor.fetchall():
                    release_path = row['release_path']
                    if release_path not in tracks_by_release:
                        tracks_by_release[release_path] = []

                    track = Track(row['path'])
                    track.artwork_path = row['artwork_path']
                    tracks_by_release[release_path].append(track)

                # Assign tracks to releases
                for release in releases:
                    release.tracks = tracks_by_release.get(release.path, [])
                    for track in release.tracks:
                        track.release = release

        return releases, has_more

    def get_release_count(self) -> int:
        """Get the total number of releases in the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM releases")
            return cursor.fetchone()['count']

    def delete_release(self, release_path: str):
        """Delete a release and its tracks from the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM releases WHERE path = ?", (release_path,))
            # Tracks will be deleted automatically due to CASCADE
            conn.commit()

    def update_release_starred(self, release_path: str, starred: bool):
        """Update the starred status of a release."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE releases
                SET starred = ?, updated_at = CURRENT_TIMESTAMP
                WHERE path = ?
            """, (starred, release_path))
            conn.commit()

    def search_releases(self, query: str, starred_only: bool = False) -> List[str]:
        """Search releases and return their paths."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            sql = """
                SELECT path FROM releases
                WHERE (title LIKE ? OR artist LIKE ?)
            """
            params = [f"%{query}%", f"%{query}%"]

            if starred_only:
                sql += " AND starred = TRUE"

            sql += " ORDER BY artist, title"

            cursor.execute(sql, params)
            return [row['path'] for row in cursor.fetchall()]

    def vacuum(self):
        """Optimize the database by running VACUUM."""
        with self._get_connection() as conn:
            conn.execute("VACUUM")

    def close(self):
        """Close the database connection."""
        # No persistent connection to close in this implementation
        pass
