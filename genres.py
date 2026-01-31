"""
Literature genres that existed before ~1970.
Excludes: cyberpunk, steampunk, dieselpunk, solarpunk, biopunk, grimdark,
urban fantasy, paranormal romance, climate fiction, techno-thriller,
domestic thriller, body horror, slasher, new weird, slipstream, cozy fantasy,
flash fiction, microfiction, choose your own adventure, YA, new adult, etc.
"""

LITERATURE_GENRES = {
    "literary_fiction": [
        "literary fiction",
        "contemporary fiction",
        "historical fiction",
        "biographical fiction",
        "epistolary fiction",
        "magical realism",
        "southern gothic",
        "satire",
        "allegory",
        "social realism",
        "naturalism",
        "existentialist fiction",
    ],

    "mystery_and_crime": [
        "mystery",
        "detective fiction",
        "hardboiled",
        "noir",
        "police procedural",
        "legal thriller",
        "true crime",
        "whodunit",
        "locked room mystery",
        "gentleman thief",
    ],

    "thriller_and_suspense": [
        "thriller",
        "psychological thriller",
        "political thriller",
        "spy fiction",
        "conspiracy thriller",
        "espionage",
    ],

    "horror": [
        "horror",
        "gothic horror",
        "cosmic horror",
        "supernatural horror",
        "psychological horror",
        "haunted house",
        "ghost story",
        "vampire fiction",
        "werewolf fiction",
        "occult fiction",
    ],

    "science_fiction": [
        "science fiction",
        "hard science fiction",
        "soft science fiction",
        "space opera",
        "post-apocalyptic",
        "dystopian",
        "utopian",
        "military science fiction",
        "first contact",
        "time travel",
        "alternate history",
        "planetary romance",
        "dying earth",
        "generation ship",
    ],

    "fantasy": [
        "fantasy",
        "high fantasy",
        "low fantasy",
        "epic fantasy",
        "sword and sorcery",
        "mythic fiction",
        "fairy tale",
        "fairy tale retelling",
        "portal fantasy",
        "heroic fantasy",
        "arthurian legend",
        "oriental fantasy",
    ],

    "romance": [
        "romance",
        "historical romance",
        "romantic comedy",
        "regency romance",
        "gothic romance",
        "romantic tragedy",
    ],

    "adventure": [
        "adventure",
        "action adventure",
        "survival fiction",
        "nautical fiction",
        "western",
        "exploration fiction",
        "lost world",
        "jungle adventure",
        "pirate fiction",
        "treasure hunt",
    ],

    "literary_forms": [
        "short story",
        "novella",
        "novel",
        "anthology",
        "serial fiction",
        "vignette",
        "found document",
        "epistolary",
        "frame narrative",
        "unreliable narrator",
        "stream of consciousness",
    ],

    "nonfiction_narrative": [
        "memoir",
        "autobiography",
        "biography",
        "creative nonfiction",
        "narrative nonfiction",
        "literary journalism",
        "travel writing",
        "nature writing",
        "essay",
        "personal essay",
    ],

    "classic_and_hybrid": [
        "science fantasy",
        "horror comedy",
        "historical mystery",
        "historical fantasy",
        "speculative fiction",
        "weird fiction",
        "fable",
        "parable",
        "tragedy",
        "comedy of manners",
        "picaresque",
        "bildungsroman",
        "war fiction",
    ],
}

# Flat list of all genres
ALL_GENRES = []
for category, genres in LITERATURE_GENRES.items():
    ALL_GENRES.extend(genres)

# Document types (for found-document fiction) - pre-1970 formats only
DOCUMENT_TYPES = [
    # Official/Institutional
    "incident report",
    "internal memo",
    "surveillance log",
    "personnel file",
    "autopsy report",
    "police report",
    "court transcript",
    "insurance claim",
    "medical chart",
    "inspection report",
    "performance review",
    "termination letter",
    "military dispatch",
    "ship's log",

    # Correspondence
    "letter",
    "diplomatic correspondence",
    "intercepted message",
    "telegram",
    "postcard",
    "cablegram",
    "radiogram",

    # Personal Documents
    "diary",
    "journal",
    "confession",
    "suicide note",
    "last will and testament",
    "love letter",
    "unsent letter",
    "commonplace book",

    # Academic/Technical
    "field observation notes",
    "research log",
    "lab notebook",
    "expedition journal",
    "archaeological report",
    "scientific paper",
    "grant proposal",
    "naturalist's journal",

    # Lists & Records
    "shopping list",
    "to-do list",
    "inventory",
    "manifest",
    "guest register",
    "maintenance checklist",
    "recipe",
    "ledger",
    "census record",

    # Media & Artifacts
    "newspaper clipping",
    "interview transcript",
    "margin notes in a book",
    "annotation",
    "classified ad",
    "obituary",
    "missing person notice",
    "wanted poster",
    "pamphlet",
    "broadside",
]

if __name__ == "__main__":
    print(f"Total genres: {len(ALL_GENRES)}")
    print(f"Total document types: {len(DOCUMENT_TYPES)}")
