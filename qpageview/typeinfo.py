from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Union

if TYPE_CHECKING:
    pass

_CommonMimeTypes = Literal[
    # Text
    "text/plain",
    "text/x-lilypond",     # The standard for .ly files
    "text/html",
    "text/css",
    "text/markdown",

    # Data Formats
    "application/json",
    "application/xml",
    "application/pdf",     # Common LilyPond output
    "application/octet-stream",

    # Images
    "image/png",
    "image/jpeg",
    "image/svg+xml",       # Common LilyPond vector output
    "image/webp",

    # Audio/Music
    "audio/midi",          # LilyPond MIDI output
    "audio/mpeg",
    "audio/ogg",
    "audio/wav"
]

MimeType = Union[_CommonMimeTypes, str]
