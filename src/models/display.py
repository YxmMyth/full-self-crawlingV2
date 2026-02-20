"""
Display manifest models - How to present crawled data.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class DisplayLayout(Enum):
    """Display layout types."""
    ARTICLE = "article"           # Standard article list
    GALLERY = "gallery"           # Image grid
    VIDEO_GRID = "video_grid"     # Video grid
    TABLE = "table"               # Table view
    TIMELINE = "timeline"         # Timeline view
    CARD = "card"                 # Card grid
    LIST = "list"                 # Simple list


@dataclass
class DisplayManifest:
    """
    Configuration for how to display crawled results.

    This guides the frontend on how to present the data.
    """
    layout: DisplayLayout
    primary_field: str           # Main field to display (e.g., "title")
    preview_field: Optional[str] = None  # Field for preview/summary
    sort_field: Optional[str] = None     # Field to sort by
    sort_order: str = "desc"             # "asc" or "desc"
    group_by: Optional[str] = None       # Field to group by
    metadata_fields: List[str] = None    # Fields to show in metadata
    display_config: Dict[str, Any] = None  # Additional layout-specific config

    def __post_init__(self):
        if self.metadata_fields is None:
            self.metadata_fields = []
        if self.display_config is None:
            self.display_config = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "layout": self.layout.value,
            "primary_field": self.primary_field,
            "preview_field": self.preview_field,
            "sort_field": self.sort_field,
            "sort_order": self.sort_order,
            "group_by": self.group_by,
            "metadata_fields": self.metadata_fields,
            "display_config": self.display_config
        }

    @classmethod
    def for_articles(cls) -> "DisplayManifest":
        """Create manifest for article display."""
        return cls(
            layout=DisplayLayout.ARTICLE,
            primary_field="title",
            preview_field="content",
            sort_field="crawl_timestamp",
            sort_order="desc",
            metadata_fields=["author", "date", "url"]
        )

    @classmethod
    def for_gallery(cls) -> "DisplayManifest":
        """Create manifest for image gallery."""
        return cls(
            layout=DisplayLayout.GALLERY,
            primary_field="image_url",
            preview_field="title",
            sort_field="crawl_timestamp",
            sort_order="desc",
            metadata_fields=["caption", "size"]
        )
