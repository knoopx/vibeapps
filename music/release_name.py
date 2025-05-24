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

    Ripping group name is usually at the end of the release name, and should be preceeded by a year but it might be absent if is not a proper release.
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
        "media_length": r"\b(?:\d+(?:cd|lp)|ep|lp|cdm|cds|mcd|cdep|\d+(?:inch))\b",
        "special_tags": r"\b(?:remix|bonus|bonustracks|reissue|demo|ost|ltd\.?|limited|promo|sampler|retail|bootleg|single)\b",
        "rip_tags": r"\b(?:proper|advance|rerip|flac)\b",
    }

    TAG_ALIASES = {
        "Limited": ["LTD.", "LIMITED"],
        "BONUS": ["BONUSTRACKS"],
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

        # First extract tags and other metadata
        self._extract_tags()

        # Get the base string for parsing
        base_string = str(self)

        # Replace double separators with single ones
        base_string = re.sub(r"[-_]{2,}", "-", base_string)
        base_string = re.sub(r"^[-_]+|[-_]+$", "", base_string)

        # Parse year and group first (from the end)
        self._parse_year_and_group(base_string)

        # Then parse artists and title
        self._parse_artists_and_title_v2(base_string)

    def _get_cleaned_string(self) -> str:
        """Get a cleaned version of the string for parsing"""
        result = str(self)

        # Replace double separators with single ones
        result = re.sub(r"[-_]{2,}", "-", result)
        result = re.sub(r"^[-_]+|[-_]+$", "", result)

        return result

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

        # Special handling for CDM with numbers (CDM1, CDM2, etc.)
        cdm_matches = re.finditer(r"\bCDM\d*\b", self, re.IGNORECASE)
        for match in cdm_matches:
            self._tags.add("CDM")

        # Extract tags from parentheses (like "Proper", "Limited Edition")
        paren_matches = re.finditer(r"\(([^)]+)\)", self)
        for match in paren_matches:
            content = match.group(1).upper().replace("_", " ")
            # Check if parenthetical content contains known tags
            if re.search(r"\b(PROPER|LIMITED|EDITION|BONUS|PROMO|ADVANCE|RERIP)\b", content):
                if "PROPER" in content:
                    self._tags.add("PROPER")
                if "LIMITED" in content or "EDITION" in content:
                    self._tags.add("LIMITED")
                if "BONUS" in content:
                    self._tags.add("BONUS")
                if "PROMO" in content:
                    self._tags.add("PROMO")
                if "ADVANCE" in content:
                    self._tags.add("ADVANCE")
                if "RERIP" in content:
                    self._tags.add("RERIP")

        # Handle tag aliases
        for normalized, aliases in self.TAG_ALIASES.items():
            pattern = r"\b(" + "|".join(re.escape(alias) for alias in aliases) + r")\b"
            if re.search(pattern, self, re.IGNORECASE):
                self._tags.add(normalized)

        # Extract and normalize country codes
        for match in re.finditer(r"-([A-Z]{2,3})-", self):
            country = match.group(1)
            self._tags.add(self.COUNTRY_CODES.get(country, country))

        # Also check for country codes in different positions
        for match in re.finditer(r"-([A-Z]{2,3})(?=-\d{4}|-[A-Z]+$)", self):
            country = match.group(1)
            # Exclude common non-country tags and roman numerals
            if country not in ["INT", "WEB", "VLS", "CDM", "CDS", "II", "III", "IV", "VI", "VII", "VIII", "IX", "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX"]:
                self._tags.add(self.COUNTRY_CODES.get(country, country))

        # Check for special indicators
        if re.search(r"_INT(?:[-_]|$)", self):
            self._tags.add("INT")

        # Check for split releases
        # Be more careful about split detection - don't treat every "_and_" as a split
        is_split = False

        # Explicit split keyword
        if re.search(r"\bSplit\b", self, re.IGNORECASE):
            is_split = True

        # Double underscore (clear split indicator)
        elif "__" in str(self):
            is_split = True

        # _-_ pattern (clear split indicator)
        elif "_-_" in str(self):
            is_split = True

        # For other separators, only consider it a split if it appears in the artist section
        # (before the first hyphen that separates artist from title)
        else:
            first_hyphen = str(self).find("-")
            if first_hyphen > 0:
                artist_section = str(self)[:first_hyphen]
                if any(sep in artist_section for sep in ["_and_", "_&_", "_vs_", "_with_"]):
                    is_split = True

        if is_split:
            self._tags.add("Split")
            self._is_split = True
        else:
            self._is_split = False

    def _parse_year_and_group(self, cleaned_string: str):
        """Parse year and group from the cleaned string"""
        # Parse year - look for 4 digit years near the end of the string
        # Try to find year before group first
        year_before_group = re.search(r"-(\d{4})-[A-Za-z]", self)
        if year_before_group:
            year = int(year_before_group.group(1))
            if 1900 <= year <= 2100:
                self._year = year
        else:
            # Look for year at the end (without group)
            year_at_end = re.search(r"-(\d{4})$", self)
            if year_at_end:
                year = int(year_at_end.group(1))
                if 1900 <= year <= 2100:
                    self._year = year
            else:
                # Handle uncertain years like "198X"
                uncertain_year = re.search(r"-(\d{3}[X])-", self)
                if uncertain_year:
                    # Don't set year for uncertain years
                    pass

        # Extract group (remove _INT suffix if present)
        # But don't treat years as groups - look for non-numeric groups
        # Only look for groups that come after a year or are at the very end with specific patterns
        if self._year:
            # Look for group after year
            group_after_year = re.search(rf"-{self._year}-([A-Za-z][A-Za-z0-9]*)(?:_INT)?$", self)
            if group_after_year:
                self._group = group_after_year.group(1)
            else:
                self._group = None
        else:
            # Only consider it a group if it's clearly a release group pattern
            # Release groups are typically all caps or mixed case, not common words
            group_match = re.search(r"-([A-Za-z][A-Za-z0-9]*)(?:_INT)?$", self)
            if group_match:
                potential_group = group_match.group(1)
                # Make sure it's not a year and looks like a release group
                if (not re.match(r"^\d{4}$", potential_group) and
                    # Check if it looks like a release group (has caps or numbers)
                    (re.search(r"[A-Z]", potential_group) or re.search(r"\d", potential_group)) and
                    # Don't treat common title words as groups
                    potential_group.lower() not in ['title', 'album', 'single', 'ep', 'demo', 'remix']):
                    self._group = potential_group
                else:
                    self._group = None
            else:
                self._group = None

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

            if len(parts) > 1:
                title = self._clean_title(parts[1])
                # Remove any remaining tags from title
                title = self._remove_tags_from_title(title)
                self._title = title
            else:
                self._title = ""

    def _parse_artists_and_title_v2(self, base_string: str):
        """Parse artists and title with better logic"""
        # Start with the base string
        content = base_string

        # Handle VA prefix
        if self._is_va:
            content = content[3:]  # Remove "VA-"
            self._artists = ["Various Artists"]

        # Special handling for _-_ pattern first (before any cleaning)
        if "_-_" in content:
            parts = content.split("_-_", 1)
            if len(parts) == 2:
                if not self._is_va:
                    self._artists = [self._clean_name(parts[0])]

                # For splits with _-_ pattern, look for "Split" keyword
                remaining_content = parts[1]
                title_parts = remaining_content.split("-")

                # Look for "Split" keyword in the parts - prioritize it
                split_found = False
                for part in title_parts:
                    if part.lower() == "split":
                        self._title = "Split"
                        split_found = True
                        break

                if not split_found:
                    # If no explicit "Split" found, default to "Split" for _-_ patterns
                    self._title = "Split"
            return

        # Remove year and group from the end if they exist
        if self._year and self._group:
            # Try to find and remove the year-group pattern
            pattern = rf"-{self._year}-{re.escape(self._group)}(?:_INT)?$"
            content = re.sub(pattern, "", content)
        elif self._year:
            # Try to remove just the year from end
            pattern = rf"-{self._year}(?:-[^-]*)?$"
            content = re.sub(pattern, "", content)
        elif self._group:
            # Try to remove just the group from end
            pattern = rf"-{re.escape(self._group)}(?:_INT)?$"
            content = re.sub(pattern, "", content)

        # For simple cases without year/group, content should be unchanged
        # Remove all tags from the content to get clean artist-title
        clean_content = content
        for pattern in self.TAG_PATTERNS.values():
            # Only remove tags that are surrounded by separators or at the end
            clean_content = re.sub(r"-" + pattern + r"(?=-|$)", "", clean_content, flags=re.IGNORECASE)

        # Remove country codes
        clean_content = re.sub(r"-[A-Z]{2,3}(?=-|$)", "", clean_content)

        # Remove catalog numbers and additional patterns
        clean_content = re.sub(r"-\([^)]+\)(?=-|$)", "", clean_content)  # Remove (CATALOG) patterns
        clean_content = re.sub(r"-[A-Z0-9]+\d+(?=-|$)", "", clean_content)  # Remove catalog patterns like TIPRS11, CDM1
        clean_content = re.sub(r"-(READ[_\s]*NFO)(?=-|$)", "", clean_content, flags=re.IGNORECASE)  # Remove READ_NFO
        clean_content = re.sub(r"-(Bonustracks|Japanese[_\s]*Edition)(?=-|$)", "", clean_content, flags=re.IGNORECASE)

        # Clean up any remaining double separators
        clean_content = re.sub(r"-+", "-", clean_content)
        clean_content = clean_content.strip("-")

        # Now split artist and title for non-_-_ patterns
        if self._has_multiple_artists(content):  # Use original content for multi-artist detection
            self._parse_multiple_artists_v2(content)
        else:
            # Simple artist-title split
            parts = clean_content.split("-", 1)

            # If we have 2 parts after cleaning, use them
            if len(parts) >= 2:
                if not self._is_va:
                    self._artists = [self._clean_name(parts[0])]
                self._title = self._clean_title(parts[1])
            # If we only have 1 part after cleaning but original had 2, use original
            elif len(parts) == 1:
                original_parts = content.split("-", 1)
                if len(original_parts) >= 2:
                    if not self._is_va:
                        self._artists = [self._clean_name(original_parts[0])]
                    self._title = self._clean_title(original_parts[1])
                else:
                    if not self._is_va:
                        self._artists = [self._clean_name(parts[0])] if parts[0] else [""]
                    self._title = ""
            else:
                if not self._is_va:
                    self._artists = [self._clean_name(parts[0])] if parts[0] else [""]
                self._title = ""

    def _parse_multiple_artists_v2(self, content: str):
        """Parse multiple artists from content with better logic"""
        separators = ["__", "_and_", "_&_", "_vs_", "_with_"]

        # Find the best separator to use
        for sep in separators:
            if sep in content:
                parts = content.split(sep)
                if len(parts) >= 2:
                    if not self._is_va:
                        self._artists = [self._clean_name(parts[0])]

                    # For multi-artist releases, we need to find the title properly
                    # The title should come after the last artist
                    remaining = sep.join(parts[1:])

                    # If there's a clear title separator (-), use it
                    if "-" in remaining:
                        title_parts = remaining.split("-", 1)
                        if len(title_parts) > 1:
                            self._title = self._clean_title(title_parts[1])
                        else:
                            # No title after the dash, use what's left
                            self._title = self._clean_title(title_parts[0])
                    else:
                        # No clear separator, use the remaining content as title
                        self._title = self._clean_title(remaining)
                    return

        # If no multi-artist separator found, treat as regular artist-title
        parts = content.split("-", 1)
        if not self._is_va:
            self._artists = [self._clean_name(parts[0])] if parts[0] else [""]

        if len(parts) > 1:
            self._title = self._clean_title(parts[1])
        else:
            self._title = ""

    def _remove_tags_from_title(self, title: str) -> str:
        """Remove tags from title string"""
        if not title:
            return ""

        # Remove all known tags from title
        for pattern in self.TAG_PATTERNS.values():
            title = re.sub(pattern, "", title, flags=re.IGNORECASE)

        # Remove country codes (but not roman numerals)
        title = re.sub(r"-(?!II$|III$|IV$|VI$|VII$|VIII$|IX$|XI$|XII$|XIII$|XIV$|XV$|XVI$|XVII$|XVIII$|XIX$|XX$)[A-Z]{2,3}(?:-|$)", "", title)

        # Clean up separators
        title = re.sub(r"[-_]+", " ", title)
        title = re.sub(r"\s+", " ", title)

        return title.strip()

    def _has_multiple_artists(self, content: str) -> bool:
        """Check if content contains multiple artists"""
        # Check for split patterns first
        if self._is_split or "__" in content or "_-_" in content:
            return True

        # For other separators, be more conservative
        # Only treat as multiple artists if the separator appears early in the string
        # (before what would be the title)
        separators = ["_and_", "_&_", "_vs_", "_with_"]
        for sep in separators:
            if sep in content:
                # Split on the separator and check if it looks like artist names
                parts = content.split(sep, 1)
                if len(parts) == 2:
                    # Check if this appears to be separating two artist names
                    # versus being part of a title after an artist-title separator

                    # If there's a clear artist-title separator before the _and_,
                    # then _and_ is likely part of the title
                    first_dash = content.find("-")
                    and_position = content.find(sep)

                    # If _and_ comes after the first dash, it's likely part of the title
                    if first_dash >= 0 and and_position > first_dash:
                        return False

                    # If _and_ comes before any dash, it's likely separating artists
                    return True

        return False

    def _parse_multiple_artists(self, content: str):
        """Parse multiple artists from content"""
        separators = ["__", "_and_", "_&_", "_vs_", "_with_", "-"]
        parts = [content]

        for sep in separators:
            new_parts = []
            for part in parts:
                if sep in part:
                    new_parts.extend(part.split(sep))
                else:
                    new_parts.append(part)
            parts = new_parts

        # Clean and filter parts
        cleaned_parts = [
            self._clean_name(part) for part in parts
            if part and not re.match(r"^(split|ep|single)$", part.strip(), re.IGNORECASE)
        ]

        if cleaned_parts:
            if not self._is_va:
                # For multiple artists, take only the first one as the main artist
                self._artists = [cleaned_parts[0]]
            # The second part should be the title, remove tags from it
            if len(cleaned_parts) > 1:
                title = cleaned_parts[1]
                title = self._remove_tags_from_title(title)
                self._title = title
            else:
                self._title = ""

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
        # Fix double separators that became spaces
        cleaned = re.sub(r"-", " ", cleaned)

        # Remove parenthetical content that are tags/catalog numbers
        cleaned = re.sub(r"\s*\([^)]*\)\s*", " ", cleaned)

        # Remove remaining catalog numbers and tags that weren't caught earlier
        cleaned = re.sub(r"\s+[A-Z0-9]+\d+\s*", " ", cleaned)  # TIPRS11, CDM1, etc.
        cleaned = re.sub(r"\s+(READ\s*NFO|PROMO|PROPER)\s*", " ", cleaned, flags=re.IGNORECASE)

        # Remove known tag patterns that might still be in the title
        for pattern in self.TAG_PATTERNS.values():
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

        # Remove country codes if they somehow made it into the title (but not roman numerals)
        # Only remove if it looks like a country code (surrounded by spaces and not roman numerals)
        cleaned = re.sub(r"\s+(US|UK|DE|FR|ES|IT|NL|BE|AT|CH|SE|NO|DK|FI|PL|CZ|HU|RO|BG|HR|SI|SK|EE|LV|LT|IE|PT|GR|CY|MT|LU)\s+", " ", cleaned)

        # Handle self-titled albums
        if re.match(r"^(s[\-\_\s\.]*t|self[\-\_\s\.]*titled)$", cleaned, re.IGNORECASE):
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