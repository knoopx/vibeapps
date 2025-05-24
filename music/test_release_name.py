import unittest
from release_name import ReleaseName


class TestReleaseName(unittest.TestCase):
    """Test cases for the ReleaseName class"""

    def assertReleaseProperties(self, release_name, expected_artist=None,
                               expected_title=None, expected_year=None,
                               expected_group=None, expected_tags=None,
                               expected_is_va=None, expected_is_split=None):
        """Helper method to test basic release properties"""
        release = ReleaseName(release_name)

        if expected_artist is not None:
            self.assertEqual(release.artist, expected_artist)
        if expected_title is not None:
            self.assertEqual(release.title, expected_title)
        if expected_year is not None:
            self.assertEqual(release.year, expected_year)
        if expected_group is not None:
            self.assertEqual(release.group, expected_group)
        if expected_tags is not None:
            if isinstance(expected_tags, (list, tuple)):
                for tag in expected_tags:
                    self.assertIn(tag, release.tags)
            elif isinstance(expected_tags, set):
                self.assertTrue(expected_tags.issubset(release.tags))
            else:
                self.assertIn(expected_tags, release.tags)
        if expected_is_va is not None:
            self.assertEqual(release.is_va, expected_is_va)
        if expected_is_split is not None:
            self.assertEqual(release.is_split, expected_is_split)

        return release

    def assertTagsInRelease(self, test_cases):
        """Helper method to test tag extraction with multiple test cases"""
        for release_name, expected_tag in test_cases:
            with self.subTest(release_name=release_name):
                release = ReleaseName(release_name)
                self.assertIn(expected_tag, release.tags)

    def assertPropertyValues(self, test_cases, property_name):
        """Helper method to test property values with multiple test cases"""
        for release_name, expected_value in test_cases:
            with self.subTest(release_name=release_name):
                release = ReleaseName(release_name)
                actual_value = getattr(release, property_name)
                self.assertEqual(actual_value, expected_value)

    def assertComplexRelease(self, test_case):
        """Helper method for testing complex real-world release names"""
        release = ReleaseName(test_case["name"])
        expected = test_case["expected"]

        # Test basic properties
        if "artist" in expected:
            self.assertEqual(release.artist, expected["artist"])
        if "title" in expected:
            self.assertEqual(release.title, expected["title"])
        if "year" in expected:
            self.assertEqual(release.year, expected["year"])
        if "group" in expected:
            self.assertEqual(release.group, expected["group"])

        # Test artists property if specified
        if "artists" in expected:
            self.assertEqual(release.artists, expected["artists"])

        # Test tags if specified
        if "tags" in expected:
            for tag in expected["tags"]:
                self.assertIn(
                    tag,
                    release.tags,
                    f"Expected tag '{tag}' not found in {release.tags}",
                )

        # Test split flag if specified
        if "is_split" in expected:
            self.assertEqual(release.is_split, expected["is_split"])

    def test_basic_release_parsing(self):
        """Test basic artist-title-year-group parsing"""
        self.assertReleaseProperties(
            "Artist-Title-2023-GROUP",
            expected_artist="Artist",
            expected_title="Title",
            expected_year=2023,
            expected_group="GROUP",
            expected_is_va=False,
            expected_is_split=False
        )

    def test_release_with_underscores(self):
        """Test release names with underscores instead of spaces"""
        self.assertReleaseProperties(
            "My_Artist-Album_Title-2023-GROUP",
            expected_artist="My Artist",
            expected_title="Album Title",
            expected_year=2023,
            expected_group="GROUP"
        )

    def test_va_compilation(self):
        """Test Various Artists compilation releases"""
        release = self.assertReleaseProperties(
            "VA-Compilation_Title-2023-GROUP",
            expected_artist="Various Artists",
            expected_year=2023,
            expected_group="GROUP",
            expected_is_va=True
        )
        self.assertEqual(release.artists, ["Various Artists"])

    def test_internal_group_release(self):
        """Test internal group releases with _INT suffix"""
        self.assertReleaseProperties(
            "Artist-Title-2023-GROUP_INT",
            expected_group="GROUP",
            expected_tags="INT"
        )

    def test_split_release(self):
        """Test split releases"""
        self.assertReleaseProperties(
            "Artist1__Artist2-Split_Album-2023-GROUP",
            expected_artist="Artist1",
            expected_is_split=True
        )

    def test_multiple_artists_with_separators(self):
        """Test multiple artists with various separators"""
        test_cases = [
            ("Artist1_and_Artist2-Title-2023-GROUP", "Artist1", "Title"),
            ("Artist1_&_Artist2-Title-2023-GROUP", "Artist1", "Title"),
            ("Artist1_vs_Artist2-Title-2023-GROUP", "Artist1", "Title"),
            ("Artist1_with_Artist2-Title-2023-GROUP", "Artist1", "Title"),
        ]

        for release_name, expected_artist, expected_title in test_cases:
            with self.subTest(release_name=release_name):
                self.assertReleaseProperties(
                    release_name,
                    expected_artist=expected_artist,
                    expected_title=expected_title
                )

    def test_country_code_extraction_and_normalization(self):
        """Test country code extraction and normalization"""
        test_cases = [
            ("Artist-Title-US-2023-GROUP", "US"),
            ("Artist-Title-SP-2023-GROUP", "ES"),  # Spain normalization
            ("Artist-Title-UK-2023-GROUP", "GB"),  # UK normalization
            ("Artist-Title-EN-2023-GROUP", "GB"),  # England normalization
        ]
        self.assertTagsInRelease(test_cases)

    def test_media_source_tags(self):
        """Test media source tag extraction"""
        test_cases = [
            ("Artist-Title-CD-2023-GROUP", "CD"),
            ("Artist-Title-VINYL-2023-GROUP", "VINYL"),
            ("Artist-Title-WEB-2023-GROUP", "WEB"),
            ("Artist-Title-DVDA-2023-GROUP", "DVDA"),
            ("Artist-Title-TAPE-2023-GROUP", "TAPE"),
            ("Artist-Title-DIGITAL-2023-GROUP", "DIGITAL"),
        ]
        self.assertTagsInRelease(test_cases)

    def test_media_length_tags(self):
        """Test media length tag extraction"""
        test_cases = [
            ("Artist-Title-EP-2023-GROUP", "EP"),
            ("Artist-Title-LP-2023-GROUP", "LP"),
            ("Artist-Title-2CD-2023-GROUP", "2CD"),
            ("Artist-Title-CDM-2023-GROUP", "CDM"),
            ("Artist-Title-VLS-2023-GROUP", "VLS"),
        ]
        self.assertTagsInRelease(test_cases)

    def test_special_tags(self):
        """Test special tag extraction"""
        test_cases = [
            ("Artist-Title-REMIX-2023-GROUP", "REMIX"),
            ("Artist-Title-BONUS-2023-GROUP", "BONUS"),
            ("Artist-Title-DEMO-2023-GROUP", "DEMO"),
            ("Artist-Title-OST-2023-GROUP", "OST"),
            ("Artist-Title-LIMITED-2023-GROUP", "LIMITED"),
            ("Artist-Title-PROMO-2023-GROUP", "PROMO"),
            ("Artist-Title-BOOTLEG-2023-GROUP", "BOOTLEG"),
            ("Artist-Title-SINGLE-2023-GROUP", "SINGLE"),
        ]
        self.assertTagsInRelease(test_cases)

    def test_rip_tags(self):
        """Test ripping-related tag extraction"""
        test_cases = [
            ("Artist-Title-PROPER-2023-GROUP", "PROPER"),
            ("Artist-Title-ADVANCE-2023-GROUP", "ADVANCE"),
            ("Artist-Title-RERIP-2023-GROUP", "RERIP"),
            ("Artist-Title-FLAC-2023-GROUP", "FLAC"),
        ]
        self.assertTagsInRelease(test_cases)

    def test_mp3_tag_not_added(self):
        """Test that MP3 tag is not added (since it's default)"""
        release = ReleaseName("Artist-Title-MP3-2023-GROUP")
        self.assertNotIn("MP3", release.tags)

    def test_year_parsing(self):
        """Test various year formats"""
        test_cases = [
            ("Artist-Title-2023-GROUP", 2023),
            ("Artist-Title-1995-GROUP", 1995),
            ("Artist-Title-198X-GROUP", None),  # Uncertain year
            ("Artist-Title-2024-GROUP", 2024),
        ]
        self.assertPropertyValues(test_cases, "year")

    def test_self_titled_albums(self):
        """Test self-titled album detection"""
        test_cases = [
            ("Artist-s.t-2023-GROUP", "Self-Titled"),
            ("Artist-s_t-2023-GROUP", "Self-Titled"),
            ("Artist-self_titled-2023-GROUP", "Self-Titled"),
            ("Artist-self.titled-2023-GROUP", "Self-Titled"),
        ]
        self.assertPropertyValues(test_cases, "title")

    def test_double_separators_handling(self):
        """Test handling of double separators (-- and __)"""
        self.assertReleaseProperties(
            "Artist--Title__With__Underscores--2023-GROUP",
            expected_artist="Artist",
            expected_title="Title With Underscores"
        )

    def test_no_year_or_group(self):
        """Test releases without year or group"""
        self.assertReleaseProperties(
            "Artist-Title",
            expected_artist="Artist",
            expected_title="Title",
            expected_year=None,
            expected_group=None
        )

    def test_no_title(self):
        """Test releases with just artist"""
        self.assertReleaseProperties(
            "Artist",
            expected_artist="Artist",
            expected_title=""
        )

    def test_empty_or_invalid_input(self):
        """Test edge cases with empty or invalid input"""
        self.assertReleaseProperties(
            "",
            expected_artist="",
            expected_title="",
            expected_year=None,
            expected_group=None
        )

    def test_complex_release_name(self):
        """Test a complex release name with multiple components"""
        expected_tags = {"FLAC", "CD", "EP", "LIMITED", "US", "INT"}
        self.assertReleaseProperties(
            "My_Artist-Great_Album-FLAC-CD-EP-LIMITED-US-2023-MYGROUP_INT",
            expected_artist="My Artist",
            expected_title="Great Album",
            expected_year=2023,
            expected_group="MYGROUP",
            expected_tags=expected_tags
        )

    def test_artists_property(self):
        """Test the artists property returns a list"""
        release = ReleaseName("Artist1__Artist2-Title-2023-GROUP")
        self.assertIsInstance(release.artists, list)
        self.assertEqual(release.artists[0], "Artist1")

    def test_cached_properties(self):
        """Test that properties are cached correctly"""
        release = ReleaseName("Artist-Title-2023-GROUP")

        # Access properties multiple times
        title1 = release.title
        title2 = release.title
        year1 = release.year
        year2 = release.year

        # Should be the same object (cached)
        self.assertIs(title1, title2)
        self.assertIs(year1, year2)

    def test_repr(self):
        """Test string representation"""
        release_name = "Artist-Title-2023-GROUP"
        release = ReleaseName(release_name)
        expected_repr = f"ReleaseName('{release_name}')"
        self.assertEqual(repr(release), expected_repr)

    def test_case_insensitive_tag_matching(self):
        """Test that tag matching is case insensitive"""
        expected_tags = {"CD", "EP", "REMIX"}
        self.assertReleaseProperties(
            "Artist-Title-cd-ep-remix-2023-GROUP",
            expected_tags=expected_tags
        )

    def test_multiple_tags_in_single_release(self):
        """Test extraction of multiple different types of tags"""
        expected_tags = {
            "FLAC",  # rip tag
            "2CD",  # media length
            "PROMO",  # special tag
            "PROPER",  # rip tag
            "GB",  # country (UK -> GB)
            "INT",  # from _INT suffix
        }

        self.assertReleaseProperties(
            "VA-Compilation-FLAC-2CD-PROMO-PROPER-UK-2023-GROUP_INT",
            expected_tags=expected_tags,
            expected_is_va=True
        )

    def test_split_keyword_detection(self):
        """Test split release detection by keyword"""
        self.assertReleaseProperties(
            "Artist1-Artist2-Split-2023-GROUP",
            expected_is_split=True
        )

    def test_year_range_validation(self):
        """Test year validation within reasonable range"""
        # Valid years
        self.assertReleaseProperties(
            "Artist-Title-2000-GROUP",
            expected_year=2000
        )

        # Invalid year (too old) should be ignored
        self.assertReleaseProperties(
            "Artist-Title-1800-GROUP",
            expected_year=None
        )

    def test_real_world_release_names(self):
        """Test real-world release names to ensure parser handles them correctly"""
        test_cases = [
            {
                "name": "Akne_Kid_Joe-Karate_Kid_Joe-WEB-DE-2018-ENTiTLED",
                "expected": {
                    "artist": "Akne Kid Joe",
                    "title": "Karate Kid Joe",
                    "year": 2018,
                    "group": "ENTiTLED",
                    "tags": {"WEB", "DE"},
                },
            },
            {
                "name": "Boysetsfire_-_Funeral_For_A_Friend-Split-VLS-2014-iTS",
                "expected": {
                    "artists": ["Boysetsfire", "Funeral For A Friend"],
                    "title": "Split",
                    "year": 2014,
                    "group": "iTS",
                    "tags": {"Split", "VLS"},
                    "is_split": True,
                },
            },
            {
                "name": "Boysetsfire-While_A_Nation_Sleeps-Bonustracks-WEB-2013-SDR",
                "expected": {
                    "artist": "Boysetsfire",
                    "title": "While A Nation Sleeps",
                    "year": 2013,
                    "group": "SDR",
                    "tags": {"WEB", "BONUS"},
                },
            },
            {
                "name": "Boyz_II_Men-Extras-Japanese_Edition-1996-iTS",
                "expected": {
                    "artist": "Boyz II Men",
                    "title": "Extras",
                    "year": 1996,
                    "group": "iTS",
                },
            },
            {
                "name": "Braid-Frame_and_Canvas-1998-iTS_INT",
                "expected": {
                    "artist": "Braid",
                    "title": "Frame and Canvas",
                    "year": 1998,
                    "group": "iTS",
                    "tags": {"INT"},
                },
            },
            {
                "name": "Breaking_Memories-Breaking_Memories-WEB-SP-2012-iTS",
                "expected": {
                    "artist": "Breaking Memories",
                    "title": "Breaking Memories",
                    "year": 2012,
                    "group": "iTS",
                    "tags": {"WEB", "ES"},  # SP should normalize to ES
                },
            },
            {
                "name": "Bruce_Springsteen-The_River-2CD-1980-FIH_INT",
                "expected": {
                    "artist": "Bruce Springsteen",
                    "title": "The River",
                    "year": 1980,
                    "group": "FIH",
                    "tags": {"2CD", "INT"},
                },
            },
        ]

        for test_case in test_cases:
            with self.subTest(name=test_case["name"]):
                self.assertComplexRelease(test_case)

    def test_challenging_release_names(self):
        """Test challenging release names with special formatting"""
        test_cases = [
            {
                "name": "(Hed)_P.E.-Evolution-(Proper)-2014-MTD",
                "expected": {
                    "artist": "(Hed) P.E.",
                    "title": "Evolution",
                    "year": 2014,
                    "group": "MTD",
                    "tags": {"PROPER"},
                },
            },
            {
                "name": "013-Armoa-FI-CDEP-2012-gF",
                "expected": {
                    "artist": "013",
                    "title": "Armoa",
                    "year": 2012,
                    "group": "gF",
                    "tags": {"FI", "CDEP"},
                },
            },
            {
                "name": "100me-Raw_Sweet_Part_2-(DEFB030)-WEB-2011-MPX",
                "expected": {
                    "artist": "100me",
                    "title": "Raw Sweet Part 2",
                    "year": 2011,
                    "group": "MPX",
                    "tags": {"WEB"},
                },
            },
            {
                "name": "1125-Untitled-Promo-READ_NFO-PL-2003-hXc",
                "expected": {
                    "artist": "1125",
                    "title": "Untitled",
                    "year": 2003,
                    "group": "hXc",
                    "tags": {"PROMO", "PL"},
                },
            },
            {
                "name": "1200_Micrograms-A_Trip_Inside_The_Outside-TIPRS11-WEB-2013-JUSTiFY",
                "expected": {
                    "artist": "1200 Micrograms",
                    "title": "A Trip Inside The Outside",
                    "year": 2013,
                    "group": "JUSTiFY",
                    "tags": {"WEB"},
                },
            },
            {
                "name": "10_Years-Division-(Limited_Edition)-2008-FTS",
                "expected": {
                    "artist": "10 Years",
                    "title": "Division",
                    "year": 2008,
                    "group": "FTS",
                    "tags": {"LIMITED"},
                },
            },
            {
                "name": "Global_Communication-Maiden_Voyage-CDM1-1994-NuHS",
                "expected": {
                    "artist": "Global Communication",
                    "title": "Maiden Voyage",
                    "year": 1994,
                    "group": "NuHS",
                    "tags": {"CDM"},
                },
            },
            {
                "name": "Yage-Some_Time_Of_A_Time-(AVM033)-2010",
                "expected": {
                    "artist": "Yage",
                    "title": "Some Time Of A Time",
                    "year": 2010,
                    "group": None,
                },
            },
            {
                "name": "Sleep_Kit-Sleep_Kit-2014",
                "expected": {
                    "artist": "Sleep Kit",
                    "title": "Sleep Kit",
                    "year": 2014,
                    "group": None,
                },
            },
            {
                "name": "Sleep_Kit-II-2015",
                "expected": {
                    "artist": "Sleep Kit",
                    "title": "II",
                    "year": 2015,
                    "group": None,
                },
            },
        ]

        for test_case in test_cases:
            with self.subTest(name=test_case["name"]):
                self.assertComplexRelease(test_case)


if __name__ == "__main__":
    unittest.main()
