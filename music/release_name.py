import re
from functools import cached_property
from typing import Optional, List, Set


class ReleaseName(str):
    """
    A class to represent a release name, providing methods to extract
    metadata such as artist, title, year, group and other tags from the
    release name string.

    A release name is typically formatted as:
        * Artist-Title-Year-Group

    However, the format can vary, and this class provides methods
    to handle various cases, including compilation releases and different
    naming conventions.

    Typically a release name uses "-" as a separator, but it can also mistakenly use double dashes ("--") to separate components (as a result of joining artist + blank title for example).
    Release names have no spaces, they use underscores ("_") instead but again, they might mistakenly use multiple underscores ("__") to separate components (as a result of replacing non-alphanumeric characters with "_").

    Ripping group name is usually at the end of the release name, and should be preceded by a year but they might be absent if is not a proper release.
    Ripping groups suffix with "_INT" when they are internal releases but the "_INT" part should not be considered part of the group's name.

    Release names might also contain other separators like "&", "and", "vs", "with" or "split" to indicate multiple artists or groups involved in the release. Strip these for multiple artists.
    Release names might also include a country code in the format "-XX-" (e.g., "-US-") to indicate the country of origin of the band typically before the year. Some releases use non-iso country codes like "-SP-" for Spain instead of "-ES-". Normalize them.

    The year is usually a four-digit number but some uncertainly released might use a less precise notation like "198X".
    The release name might also include a format or media source (e.g., "vinyl", "cd", "web", "DVDA", "DVD", "TAPE", "VINYL", "VLS", "WEB", "SAT" or "CABLE", etc.) which should be extracted as tags.
    Unless specified by "FLAC", releases are assumed to be in MP3 format, so the "MP3" tag should not be added.

    Apart from the media source, they might also include media "length" with tags like "7inch", "3inch", "EP", "2CD", "LP", "4xLP", "CDM", "CDS", etc... These give a hint about the media length (is it a single? a full album? etc...) and should be extracted as tags.
    "REMIX", "BONUS", "DEMO", "OST", "LTD.", "LIMITED", "PROMO", "SAMPLER", "RETAIL", "BOOTLEG", "SINGLE",

    The release name might also include special internal group tags like "PROPER", "RETAIL", "ADVANCE", "RERIP", which indicate the "ripping" details and should be also part of the extracted tags.

    Compilation and split albums releases typically start "VA-".
    Split releases are typically indicated by the presence of multiple artists in the title, or by the presence of certain keywords like "split".

    Any information that is not part of the artist, title, year or group should be considered as tags and stripped.
    """

    # Country code normalization mapping
    COUNTRY_CODES = {
        "SP": "ES",  # Spain
        "UK": "GB",  # United Kingdom
        "EN": "GB",  # England -> Great Britain
    }

    TAG_PATTERNS = {
        "media_source": r"\b(?:vinyl|cd|web|dvda|dvd|tape|vls|sat|cable|digital)\b",
        "media_length": r"\b(?:\d+(?:cd|lp)|ep|lp|cdm|cds|mcd|\d+(?:inch))\b",
        "special_tags": r"\b(?:remix|bonus|demo|ost|ltd\.?|limited|promo|sampler|retail|bootleg|single)\b",
        "rip_tags": r"\b(?:proper|advance|rerip|flac|mp3|320|v0|v2|aac)\b",
    }

    TAG_ALIASES = {
        "Limited": ["LTD.", "LIMITED"],
    }

    def __new__(cls, content):
        instance = super().__new__(cls, content)
        instance._parsed = False
        instance._artists = []
        instance._title = None
        instance._year = None
        instance._group = None
        instance._tags = set()
        instance._is_split = None
        instance._is_va = None
        return instance

    def _parse_release_name(self):
        """Parse the release name into components"""
        if self._parsed:
            return

        self._parsed = True
        self._is_va = self.upper().startswith("VA-")
        self._extract_tags()

        cleaned = self._get_cleaned_string()
        self._parse_year_and_group(cleaned)
        self._parse_artists_and_title(cleaned)

    def _get_cleaned_string(self) -> str:
        """Get a cleaned version of the string for parsing"""
        result = str(self)

        for pattern in self.TAG_PATTERNS.values():
            result = re.sub(pattern, "", result, flags=re.IGNORECASE)

        result = re.sub(r"[-_]{2,}", "-", result)
        return re.sub(r"^[-_]+|[-_]+$", "", result)

    def _extract_tags(self):
        """Extract all tags from the release name"""
        self._tags = set()

        # Extract all tag types
        for tag_type, pattern in self.TAG_PATTERNS.items():
            matches = re.finditer(pattern, self, re.IGNORECASE)
            for match in matches:
                tag = match.group().upper().replace(".", "")
                if tag != "MP3":  # Don't add MP3 as it's default
                    self._tags.add(tag)

        # Handle tag aliases
        for normalized, aliases in self.TAG_ALIASES.items():
            pattern = r"\b(" + "|".join(re.escape(alias) for alias in aliases) + r")\b"
            if re.search(pattern, self, re.IGNORECASE):
                self._tags.add(normalized)

        # Extract and normalize country codes
        for match in re.finditer(r"-([A-Z]{2,3})-", self):
            country = match.group(1)
            self._tags.add(self.COUNTRY_CODES.get(country, country))

        # Check for special indicators
        if re.search(r"_INT(?:[-_]|$)", self):
            self._tags.add("Internal")

        if re.search(r"\bSplit\b", self, re.IGNORECASE):
            self._tags.add("Split")
            self._is_split = True
        else:
            self._is_split = False

    def _parse_year_and_group(self, cleaned_string: str):
        """Parse year and group from the cleaned string"""
        # Handle uncertain years like "198X"
        year_match = re.search(r"\b(\d{3}[X\d])\b", cleaned_string)
        if year_match:
            year_str = year_match.group(1)
            if not year_str.endswith("X"):
                try:
                    year = int(year_str)
                    if 1900 <= year <= 2100:
                        self._year = year
                except ValueError:
                    pass

        # Extract group (remove _INT suffix if present)
        group_match = re.search(r"-([A-Za-z0-9]+)(?:_INT)?$", self)
        self._group = group_match.group(1) if group_match else None

    def _parse_artists_and_title(self, cleaned_string: str):
        """Parse artists and title from the cleaned string"""
        content = cleaned_string[3:] if self._is_va else cleaned_string

        if self._is_va:
            self._artists = ["Various Artists"]

        # Remove year and group from the end
        if self._year:
            content = re.sub(rf"-{self._year}-.*$", "", content)
        elif self._group:
            content = re.sub(rf"-{self._group}(?:_INT)?$", "", content)

        # Handle multiple artists or single artist
        if self._has_multiple_artists(content):
            self._parse_multiple_artists(content)
        else:
            parts = content.split("-", 1)
            self._artists = [self._clean_name(parts[0])] if not self._is_va else self._artists
            self._title = self._clean_title(parts[1] if len(parts) > 1 else "")

    def _has_multiple_artists(self, content: str) -> bool:
        """Check if content contains multiple artists"""
        return (self._is_split or "__" in content or
                any(sep in content for sep in [" and ", " & ", " vs ", " with "]))

    def _parse_multiple_artists(self, content: str):
        """Parse multiple artists from content"""
        separators = ["__", "--", " and ", " & ", " vs ", " with ", "-"]
        parts = [content]

        for sep in separators:
            new_parts = []
            for part in parts:
                new_parts.extend(part.split(sep) if sep in part else [part])
            parts = new_parts

        # Clean and filter parts
        cleaned_parts = [
            self._clean_name(part) for part in parts
            if part and not re.match(r"^(split|ep|single)$", part.strip(), re.IGNORECASE)
        ]

        if cleaned_parts:
            if not self._is_va:
                self._artists = [cleaned_parts[0]]
            self._title = " / ".join(cleaned_parts[1:]) if len(cleaned_parts) > 1 else ""

    def _clean_name(self, name: str) -> str:
        """Clean artist/group name"""
        if not name:
            return ""

        cleaned = name.replace("_", " ")
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip(" -_")

    def _clean_title(self, title: str) -> str:
        """Clean title string"""
        if not title:
            return ""

        cleaned = title.replace("_", " ")

        # Handle self-titled albums
        if re.match(r"^(s[\-\_\s\.]*t[\-\_\s\.]|self[\-\_\s\.]*titled)$", cleaned, re.IGNORECASE):
            return "Self-Titled"

        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip(" -_")

    @property
    def artists(self) -> List[str]:
        """Get list of artists"""
        self._parse_release_name()
        return self._artists

    @property
    def artist(self) -> str:
        """Get primary artist (first artist)"""
        artists = self.artists
        return artists[0] if artists else ""

    @cached_property
    def title(self) -> str:
        """Get release title"""
        self._parse_release_name()
        return self._title or ""

    @cached_property
    def year(self) -> Optional[int]:
        """Get release year"""
        self._parse_release_name()
        return self._year

    @cached_property
    def group(self) -> Optional[str]:
        """Get ripping group name"""
        self._parse_release_name()
        return self._group

    @cached_property
    def tags(self) -> Set[str]:
        """Get all extracted tags"""
        self._parse_release_name()
        return self._tags.copy()

    @cached_property
    def is_split(self) -> bool:
        """Check if this is a split release"""
        self._parse_release_name()
        return self._is_split

    @cached_property
    def is_va(self) -> bool:
        """Check if this is a Various Artists compilation"""
        self._parse_release_name()
        return self._is_va

    def __repr__(self) -> str:
        return f"ReleaseName('{str(self)}')"