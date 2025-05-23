import re
from functools import cached_property
from typing import Optional, List, Set, Dict


class ReleaseName(str):
    def __new__(cls, content):
        instance = super().__new__(cls, content)
        # Initialize cached properties
        instance._artist = None
        instance._title = None
        instance._year = None
        instance._label = None
        instance._tags = None
        instance._is_split = None
        return instance

    def _clean_string(self, input: str, transforms: List[tuple] = None) -> str:
        if transforms is None:
            transforms = []

        patterns = (
            [
                (r"(\([^\)]*\)?)+", "", 0),
                (r"(\[[^\]]*\]?)+", "", 0),
                (r"[_]+", " ", 0),
                (r"\s+", " ", 0),
                (r"\b\s*&\s*\b", " and ", 0),
                (r"\b([_\'\-\s]+)n([_\'\-\s])+\b", " and ", 0),
            ]
            + transforms
            + [(r"^[_\-\s]+", "", 0), (r"[_\-\s]+$", "", 0)]
        )

        result = input
        for pattern, replacement, flags in patterns:
            result = re.sub(pattern, replacement, result, flags=flags)
            if not result.strip():
                result = replacement
        return result.strip()

    def _extract_label_part(self) -> str:
        match = re.search(r"[-]+(\d{4})[-]+(.*)$", self)
        if match:
            return match.group(2)

        match = re.search(r"\b(\d{4})\b(.*)$", self)
        if match:
            return match.group(2)

        return ""

    @cached_property
    def year(self) -> Optional[int]:
        match = re.search(r"[-]+(\d{4})[-]+", self)
        if not match:
            match = re.search(r"\b(\d{4})\b", self)

        if match:
            try:
                year = int(match.group(1))
                if 1900 <= year <= 2100:
                    return year
            except ValueError:
                pass
        return None

    @cached_property
    def is_split(self) -> bool:
        patterns = [
            r"[-_\s]split[-_\s]",
            r"\b\d+[-_\s]*artists\b",
            r"[-_\s]vs[-_\s]",
            r"[-_\s]with[-_\s]",
            r"(?:^|[-_\s])and(?:[-_\s]|$)",  # Match "and" with boundaries
            r"__",  # Double underscore often indicates split
            r"[-_\s]&[-_\s]",  # Additional split indicator
        ]
        return any(re.search(pattern, self, re.I) for pattern in patterns)

    def _extract_artists(self, text: str) -> List[str]:
        # Split on common separators while preserving the separators in the result
        separators = ["-", "_", " and ", " & ", "__"]
        parts = [text]
        for sep in separators:
            new_parts = []
            for part in parts:
                if sep in part:
                    split_parts = [p.strip() for p in part.split(sep)]
                    new_parts.extend(p for p in split_parts if p)
                else:
                    new_parts.append(part)
            parts = new_parts
        return [
            p
            for p in parts
            if p and not re.match(r"^(split|ep|vinyl|cd|web)$", p, re.I)
        ]

    @cached_property
    def title(self) -> str:
        # Special case for names like "1982_Trio-A-B-2014-gF"
        special_match = re.match(r"^([^-]+)-([^-]+(?:-[^-]+)*)-(\d{4})-([^-]+)$", self)
        if special_match:
            title_part = special_match.group(2)
        elif "--" in self:
            parts = self.split("--", 1)
            title_part = parts[1]
        else:
            parts = self.split("-", 1)
            title_part = parts[1] if len(parts) > 1 else parts[0]

        # Special handling for split releases
        if self.is_split:
            # Extract all artists from the title part
            artists = self._extract_artists(title_part)
            if artists:
                # Join artists with " / " for display
                title_part = " / ".join(artists)

        # Updated title cleaning transforms
        title_transforms = [
            # Convert '_' to spaces first
            (r"_", " ", 0),
            # Extract and clean up series/volumes
            (
                r"(?i)(single[\s_]*serie[s]?[\s_]*(?:part[\s_]*)?(\d+))",
                r"Single Series Part \2",
                0,
            ),
            # Remove inch measurements completely
            (r"(?i)(\d+[\s_]*(?:inch|\"|\u201D))", "", 0),
            # Move format/media info to tags
            (r"(?i)\b(vinyl|cd|web|tape|digital)\b", "", 0),
            # Clean up region codes
            (r"-([A-Z]{2})-", "", 0),
            # Remove year and anything after
            (r"[-]+\d{4}[-]+.*$", "", 0),
            (r"\b\d{4}\b.*$", "", 0),
            # Other existing transforms
            (r"\b(TRACKFIX|DIRFIX|READ[\-\s]*NFO)\b", "", re.I),
            (
                r"\b(S[\-\_\s\.]*T[\-\_\s\.]|SELF[\-\_\s\.]*TITLED)\b",
                "Self-Titled",
                re.I,
            ),
            (r"\b((RE[\-\s]*)?(MASTERED|ISSUE|PACKAGE|EDITION))\b", "", re.I),
            (
                r"\b(ADVANCE|PROMO|SAMPLER|PROPER|RERIP|RETAIL|REMIX|BONUS|LTD\.?|LIMITED)\b",
                "",
                re.I,
            ),
            (
                r"\b(CDM|CDEP|CDR|CDS|CD|MCD|DVDA|DVD|TAPE|VINYL|VLS|WEB|SAT|CABLE)\b",
                "",
                re.I,
            ),
            (r"\b(EP|LP|BOOTLEG|SINGLE)\b", "", re.I),
            (r"\b(WEB|FLAC|MP3|320|V0|V2|AAC)\b", "", re.I),
            (r"\b(VA|OST)\b[\-\s]*", "", re.I),
            (r"\bsplit\b", "", re.I),
            # Clean up multiple spaces and trim
            (r"\s+", " ", 0),
        ]

        return self._clean_string(title_part, title_transforms)

    @property
    def artist(self) -> str:
        if self._artist is None:
            # Special case for names like "1982_Trio-A-B-2014-gF"
            special_match = re.match(
                r"^([^-]+)-([^-]+(?:-[^-]+)*)-(\d{4})-([^-]+)$", self
            )
            if special_match:
                artist_part = special_match.group(1)
            # Process splits differently
            elif self.is_split:
                if "--" in self:
                    artist_part = self.split("--", 1)[0]
                else:
                    artist_part = self.split("-", 1)[0]

                artists = self._extract_artists(artist_part)
                if artists:
                    # Join multiple artists with " / "
                    self._artist = " / ".join(artists)
                else:
                    self._artist = "Various Artists"  # Fallback for splits
                return self._artist
            else:
                # Regular releases
                if "--" in self:
                    artist_part = self.split("--", 1)[0]
                else:
                    artist_part = self.split("-", 1)[0]

            # Clean up the artist name using existing method
            self._artist = self._clean_string(artist_part)
        return self._artist

    @cached_property
    def tags(self) -> Set[str]:
        tags = set()
        if self.is_split:
            tags.add("Split")

        format_patterns = [
            (r"(?i)(\d+)\s*(?:inch|\"|\u201D)", r'\1"'),
            (r"(?i)\b(vinyl|cd|web|tape|digital)\b", r"\1"),
        ]

        for pattern, tag_format in format_patterns:
            match = re.search(pattern, self, re.I)
            if match:
                tags.add(match.expand(tag_format).title())

        # Add region code if present
        region_match = re.search(r"-([A-Z]{2})-", self)
        if region_match:
            tags.add(region_match.group(1))

        # Only add INT tag here, group name will be handled separately
        if self.endswith("_INT") or re.search(r"[-]([A-Za-z0-9]+)_INT$", self):
            tags.add("INT")

        return tags

    @cached_property
    def label(self) -> str:
        # Extract group name separately from _INT suffix
        int_group_match = re.search(r"[-]([A-Za-z0-9]+)_INT$", self)
        if int_group_match:
            return int_group_match.group(1)  # Return just the group name

        # Handle regular group/label
        if scene_match := re.search(r"[-]([A-Za-z0-9]+)$", self):
            return scene_match.group(1)

        # Fall back to standard label extraction for other cases
        return self._clean_string(self._extract_label_part())
