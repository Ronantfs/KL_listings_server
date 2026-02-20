from typing import List, Dict, Optional, TypedDict

class StructuredDateStrings(TypedDict):
    Weekday: str  # e.g., "Sunday"
    Month: str  # e.g., "May"
    day_str: str  # e.g., "5th"


class Listing_When_Date(TypedDict):
    date: str  # Format of str: YYYY-MM-DD
    structured_date_strings: StructuredDateStrings
    year: int
    month: int
    day: int
    showtimes: List[str]  # Format of str: HH:MM

# Additional info types — progressively enriched at each pipeline stage
class RawListingAdditionalInfo(TypedDict, total=False):
    """Fields populated by cinema scrapers."""
    title: Optional[str]
    directors: Optional[List[str]]
    cast: Optional[List[str]]
    countries: Optional[List[str]]
    year: Optional[int]
    runtime_mins: Optional[int]
    screening_medium: Optional[str]
    age_rating: Optional[int]


class MatchedListingAdditionalInfo(RawListingAdditionalInfo, total=False):
    """Adds TMDB match result on top of scraper fields."""
    db_id: Optional[int]  # TMDB id — added by TMDB matching process


class CleanedCompactListingAdditionalInfo(MatchedListingAdditionalInfo, total=False):
    """Adds provenance tracking on top of matched fields."""
    original_raw_titles: List[str]  # raw title key(s) before cleaning/compaction


# Listing types — shared base + one per pipeline stage.
# Only _additional_info changes between stages.

class _BaseFilmListing(TypedDict):
    """Shared fields across all pipeline stages."""
    description: str
    screen: Optional[str]
    screeningType: str                  # e.g. "standard", "35mm", "IMAX"
    url: Optional[str]
    when: List[Listing_When_Date]
    image_to_download: Optional[str]    # source URL for image to download
    isImageGood: bool                   # default False for later verification
    s3ImageURL: str                     # default "" until uploaded


class RawFilmListing(_BaseFilmListing):
    """Output of cinema scrapers."""
    _additional_info: RawListingAdditionalInfo


class MatchedListing(_BaseFilmListing):
    """Output of TMDB matching — _additional_info gains db_id."""
    _additional_info: MatchedListingAdditionalInfo


class CleanedCompactListing(_BaseFilmListing):
    """Output of clean-and-compact — _additional_info gains original_raw_titles."""
    _additional_info: CleanedCompactListingAdditionalInfo
# ---------------------------------------------------------------------------
# Dict aliases — keyed by title string, one per pipeline stage
# ---------------------------------------------------------------------------
CinemasRawListings = dict[str, RawFilmListing]
CinemasMatchedListings = dict[str, MatchedListing]
CinemasCleanedCompactListings = dict[str, CleanedCompactListing]


# New PanCinemaCleanedCompactedListings

# str keys are cinema names
CleanMatchedFilmsCinemaListings = dict[str, CleanedCompactListing]
# int keys are db_id's
PanCinemaCleanedCompactedListings = dict[int, CleanMatchedFilmsCinemaListings]