"""NCERT curriculum alignment for Classes 8, 9 and 10.

The project targets students following the NCERT/CBSE syllabus in India. This
module is deliberately small and dependency-free: it stores the chapter map for
the six courses we care about (Science and Mathematics for each class) and
matches a transcript to the most likely chapters using titles, key terms and
explicit "chapter N" mentions.

The match is used in two places:

* the notes prompt, as a *terminology* hint -- never as a source of facts;
* the dashboard and Markdown export, as a "Syllabus alignment" section.

Grounding is unchanged: the verifier still checks every generated line against
the transcript, so a chapter hint can only influence wording, not invent content.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable
from dataclasses import dataclass

CLASS_LEVELS = (8, 9, 10)
SUBJECTS = ("science", "maths")
SUBJECT_LABELS = {"science": "Science", "maths": "Mathematics"}

_SUBJECT_ALIASES = {
    "science": "science",
    "maths": "maths",
    "math": "maths",
    "mathematics": "maths",
    "maths.": "maths",
}

_WORD = re.compile(r"[a-z0-9][a-z0-9'\-]*")
_CHAPTER_MENTION = re.compile(r"\bchapter\s+(\d{1,2})\b", re.IGNORECASE)

#: Words that add no signal when matching a chapter title.
_TITLE_NOISE = frozenset(
    """
    a an and are as at based chapter class for from in into introduction is it its of on or our
    reaching related some the their then there this to understanding unit using what why with
    """.split()  # noqa: SIM905 - a word list reads better than a long literal
)

_STOPWORDS = frozenset(
    """
    a about above after again against all also am an and any are as at be because been before
    being below between both but by can could did do does doing down during each few for from
    further had has have having he her here him his how i if in into is it its itself just me
    more most my no nor not of off on once only or other our out over own same she should so
    some such than that the their them then there these they this those through to too under
    until up very was we were what when where which while who whom why will with would you your
    """.split()  # noqa: SIM905 - a word list reads better than a long literal
)


@dataclass(frozen=True, slots=True)
class Chapter:
    number: int
    title: str
    keywords: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {"number": self.number, "title": self.title}


@dataclass(frozen=True, slots=True)
class Course:
    class_level: int
    subject: str
    chapters: tuple[Chapter, ...]

    @property
    def label(self) -> str:
        return f"Class {self.class_level} {SUBJECT_LABELS[self.subject]}"

    def chapter(self, number: int) -> Chapter | None:
        return next((item for item in self.chapters if item.number == number), None)

    def to_dict(self) -> dict[str, object]:
        return {
            "class_level": self.class_level,
            "subject": self.subject,
            "label": self.label,
            "chapters": [chapter.to_dict() for chapter in self.chapters],
        }


def _course(class_level: int, subject: str, chapters: Iterable[Chapter]) -> Course:
    return Course(class_level=class_level, subject=subject, chapters=tuple(chapters))


SCIENCE_8 = _course(
    8,
    "science",
    [
        Chapter(1, "Crop Production and Management", (
            "crop", "kharif", "rabi", "ploughing", "manure", "fertiliser", "fertilizer",
            "irrigation", "weeds", "weeding", "harvesting", "threshing", "storage of grains",
        )),
        Chapter(2, "Microorganisms: Friend and Foe", (
            "microorganism", "microbe", "bacteria", "fungi", "protozoa", "algae", "virus",
            "fermentation", "antibiotic", "vaccine", "food preservation", "nitrogen fixation",
        )),
        Chapter(3, "Coal and Petroleum", (
            "coal", "petroleum", "fossil fuel", "refining", "natural gas", "exhaustible",
            "inexhaustible", "carbonisation", "destructive distillation",
        )),
        Chapter(4, "Combustion and Flame", (
            "combustion", "fuel", "flame", "ignition temperature", "inflammable",
            "calorific value", "fire extinguisher", "global warming",
        )),
        Chapter(5, "Conservation of Plants and Animals", (
            "conservation", "deforestation", "wildlife sanctuary", "national park",
            "biosphere reserve", "endangered", "extinct", "ecosystem", "biodiversity",
        )),
        Chapter(6, "Reproduction in Animals", (
            "reproduction", "fertilisation", "fertilization", "zygote", "embryo",
            "metamorphosis", "tadpole", "viviparous", "oviparous", "cloning",
        )),
        Chapter(7, "Reaching the Age of Adolescence", (
            "adolescence", "puberty", "hormone", "thyroxine", "insulin", "adrenaline",
            "secondary sexual characteristics", "menstruation", "reproductive health",
        )),
        Chapter(8, "Force and Pressure", (
            "force", "pressure", "magnetic force", "electrostatic force", "gravitational force",
            "atmospheric pressure", "liquid pressure", "contact force",
        )),
        Chapter(9, "Friction", (
            "friction", "static friction", "sliding friction", "rolling friction", "lubricant",
            "ball bearing", "drag", "fluid friction",
        )),
        Chapter(10, "Sound", (
            "sound", "vibration", "amplitude", "frequency", "pitch", "loudness", "audible range",
            "noise pollution", "eardrum",
        )),
        Chapter(11, "Chemical Effects of Electric Current", (
            "electric current", "electrolyte", "electrolysis", "electrode", "anode", "cathode",
            "electroplating", "conducting solution",
        )),
        Chapter(12, "Some Natural Phenomena", (
            "lightning", "earthquake", "electric charge", "static electricity", "seismograph",
            "thunder", "earthing", "lightning conductor",
        )),
        Chapter(13, "Light", (
            "light", "reflection", "refraction", "mirror", "lens", "dispersion", "spectrum",
            "image", "periscope", "kaleidoscope",
        )),
    ],
)

MATHS_8 = _course(
    8,
    "maths",
    [
        Chapter(1, "Rational Numbers", (
            "rational number", "numerator", "denominator", "additive inverse",
            "multiplicative inverse", "number line", "equivalent rational numbers",
        )),
        Chapter(2, "Linear Equations in One Variable", (
            "linear equation", "variable", "transpose", "solution", "both sides",
        )),
        Chapter(3, "Understanding Quadrilaterals", (
            "quadrilateral", "parallelogram", "rectangle", "square", "rhombus", "trapezium",
            "kite", "angle sum", "diagonals",
        )),
        Chapter(4, "Data Handling", (
            "data", "bar graph", "histogram", "pie chart", "probability", "frequency",
            "tally marks", "random experiment",
        )),
        Chapter(5, "Squares and Square Roots", (
            "square", "perfect square", "square root", "prime factorisation",
            "prime factorization", "long division", "radical", "repeated subtraction",
        )),
        Chapter(6, "Cubes and Cube Roots", (
            "cube", "perfect cube", "cube root", "prime factorisation", "estimation",
        )),
        Chapter(7, "Comparing Quantities", (
            "ratio", "percentage", "profit", "loss", "discount", "simple interest",
            "compound interest", "sales tax", "cost price", "selling price",
        )),
        Chapter(8, "Algebraic Expressions and Identities", (
            "algebraic expression", "term", "coefficient", "monomial", "binomial",
            "polynomial", "identity", "factorisation",
        )),
        Chapter(9, "Mensuration", (
            "area", "perimeter", "trapezium", "rhombus", "surface area", "volume", "cube",
            "cuboid", "cylinder",
        )),
        Chapter(10, "Exponents and Powers", (
            "exponent", "power", "base", "laws of exponents", "negative exponent",
            "standard form",
        )),
        Chapter(11, "Direct and Inverse Proportions", (
            "direct proportion", "inverse proportion", "variation", "constant", "ratio",
        )),
        Chapter(12, "Factorisation", (
            "factorisation", "common factor", "regrouping", "identity", "algebraic expression",
            "division",
        )),
        Chapter(13, "Introduction to Graphs", (
            "graph", "bar graph", "pie chart", "histogram", "line graph", "linear graph",
            "coordinates", "x-axis", "y-axis",
        )),
    ],
)

SCIENCE_9 = _course(
    9,
    "science",
    [
        Chapter(1, "Matter in Our Surroundings", (
            "matter", "solid", "liquid", "gas", "evaporation", "condensation", "sublimation",
            "latent heat", "diffusion", "temperature", "pressure",
        )),
        Chapter(2, "Is Matter Around Us Pure", (
            "mixture", "solution", "suspension", "colloid", "separation", "distillation",
            "crystallisation", "chromatography", "pure substance", "compound",
        )),
        Chapter(3, "Atoms and Molecules", (
            "atom", "molecule", "ion", "chemical formula", "mole", "molar mass", "avogadro",
            "law of conservation of mass", "valency",
        )),
        Chapter(4, "Structure of the Atom", (
            "electron", "proton", "neutron", "nucleus", "atomic number", "mass number",
            "valency", "isotope", "isobar", "bohr model", "rutherford",
        )),
        Chapter(5, "The Fundamental Unit of Life", (
            "cell", "plasma membrane", "nucleus", "cytoplasm", "organelle", "mitochondria",
            "chloroplast", "vacuole", "osmosis", "cell wall", "prokaryotic", "eukaryotic",
        )),
        Chapter(6, "Tissues", (
            "tissue", "meristematic", "parenchyma", "collenchyma", "sclerenchyma", "xylem",
            "phloem", "epithelial", "connective", "muscular", "nervous", "neuron",
        )),
        Chapter(7, "Motion", (
            "motion", "distance", "displacement", "speed", "velocity", "acceleration",
            "uniform motion", "non-uniform motion", "distance-time graph",
            "velocity-time graph", "equations of motion",
        )),
        Chapter(8, "Force and Laws of Motion", (
            "force", "inertia", "mass", "momentum", "newton", "action", "reaction",
            "conservation of momentum", "balanced force", "unbalanced force",
        )),
        Chapter(9, "Gravitation", (
            "gravitation", "gravity", "free fall", "acceleration due to gravity", "mass",
            "weight", "thrust", "pressure", "buoyancy", "archimedes", "relative density",
        )),
        Chapter(10, "Work and Energy", (
            "work", "energy", "kinetic energy", "potential energy", "power", "joule", "watt",
            "conservation of energy", "commercial unit of energy",
        )),
        Chapter(11, "Sound", (
            "sound", "wave", "longitudinal wave", "compression", "rarefaction", "frequency",
            "amplitude", "wavelength", "speed of sound", "echo", "reverberation",
            "audible range", "ultrasound",
        )),
        Chapter(12, "Improvement in Food Resources", (
            "food resources", "crop production", "manure", "fertiliser", "irrigation",
            "cropping pattern", "mixed farming", "poultry", "fish farming", "bee keeping",
            "animal husbandry",
        )),
    ],
)

MATHS_9 = _course(
    9,
    "maths",
    [
        Chapter(1, "Number Systems", (
            "number system", "natural number", "whole number", "integer", "rational number",
            "irrational number", "real number", "number line", "decimal expansion",
            "rationalisation", "exponent",
        )),
        Chapter(2, "Polynomials", (
            "polynomial", "degree", "coefficient", "zero of a polynomial", "remainder theorem",
            "factor theorem", "algebraic identity", "factorisation",
        )),
        Chapter(3, "Coordinate Geometry", (
            "coordinate geometry", "cartesian plane", "x-axis", "y-axis", "origin", "quadrant",
            "abscissa", "ordinate", "coordinates",
        )),
        Chapter(4, "Linear Equations in Two Variables", (
            "linear equation", "two variables", "solution", "graph", "straight line",
            "consistent", "inconsistent",
        )),
        Chapter(5, "Introduction to Euclid's Geometry", (
            "euclid", "axiom", "postulate", "theorem", "point", "line", "plane", "incidence",
        )),
        Chapter(6, "Lines and Angles", (
            "line", "angle", "acute", "obtuse", "right angle", "complementary", "supplementary",
            "linear pair", "vertically opposite", "parallel lines", "transversal",
            "corresponding angles", "alternate angles",
        )),
        Chapter(7, "Triangles", (
            "triangle", "congruent", "congruence", "sss", "sas", "asa", "rhs", "isosceles",
            "equilateral", "angle sum", "exterior angle",
        )),
        Chapter(8, "Quadrilaterals", (
            "quadrilateral", "parallelogram", "rectangle", "square", "rhombus", "trapezium",
            "kite", "diagonals", "midpoint theorem",
        )),
        Chapter(9, "Circles", (
            "circle", "radius", "diameter", "chord", "arc", "segment", "sector",
            "cyclic quadrilateral", "tangent", "secant", "angle subtended",
        )),
        Chapter(10, "Heron's Formula", (
            "heron", "semi-perimeter", "triangle", "area", "side", "equilateral triangle",
        )),
        Chapter(11, "Surface Areas and Volumes", (
            "surface area", "volume", "cube", "cuboid", "cylinder", "cone", "sphere",
            "hemisphere", "capacity", "lateral surface area",
        )),
        Chapter(12, "Statistics", (
            "statistics", "data", "frequency", "class interval", "mean", "median", "mode",
            "bar graph", "histogram", "frequency polygon",
        )),
    ],
)

SCIENCE_10 = _course(
    10,
    "science",
    [
        Chapter(1, "Chemical Reactions and Equations", (
            "chemical reaction", "equation", "reactant", "product", "balanced equation",
            "combination", "decomposition", "displacement", "double displacement", "oxidation",
            "reduction", "corrosion", "rancidity",
        )),
        Chapter(2, "Acids, Bases and Salts", (
            "acid", "base", "salt", "indicator", "litmus", "ph", "neutralisation",
            "neutralization", "sodium hydroxide", "hydrochloric acid", "baking soda",
            "washing soda", "bleaching powder", "plaster of paris",
        )),
        Chapter(3, "Metals and Non-metals", (
            "metal", "non-metal", "metallurgy", "ore", "mineral", "reactivity series",
            "ionic compound", "corrosion", "alloy", "amphoteric oxide",
        )),
        Chapter(4, "Carbon and its Compounds", (
            "carbon", "covalent bond", "hydrocarbon", "alkane", "alkene", "alkyne",
            "functional group", "alcohol", "carboxylic acid", "esterification", "soap",
            "detergent", "isomer",
        )),
        Chapter(5, "Life Processes", (
            "life process", "nutrition", "respiration", "digestion", "transport", "excretion",
            "photosynthesis", "stomata", "xylem", "phloem", "blood", "nephron", "autotrophic",
            "heterotrophic",
        )),
        Chapter(6, "Control and Coordination", (
            "control", "coordination", "nervous system", "neuron", "brain", "spinal cord",
            "reflex action", "hormone", "pituitary", "thyroid", "insulin", "adrenaline",
            "tropism",
        )),
        Chapter(7, "How do Organisms Reproduce?", (
            "reproduction", "asexual", "sexual", "binary fission", "budding", "fragmentation",
            "pollination", "fertilisation", "fertilization", "placenta", "menstrual cycle",
            "contraceptive",
        )),
        Chapter(8, "Heredity", (
            "heredity", "inheritance", "gene", "chromosome", "dna", "dominant", "recessive",
            "genotype", "phenotype", "mendel", "sex determination", "evolution",
        )),
        Chapter(9, "Light - Reflection and Refraction", (
            "light", "reflection", "refraction", "mirror", "lens", "focal length",
            "principal focus", "concave", "convex", "refractive index", "incident ray",
            "reflected ray", "real image", "virtual image", "magnification",
        )),
        Chapter(10, "The Human Eye and the Colourful World", (
            "human eye", "cornea", "iris", "pupil", "retina", "lens", "accommodation",
            "myopia", "hypermetropia", "presbyopia", "cataract", "dispersion", "spectrum",
            "rainbow", "scattering",
        )),
        Chapter(11, "Electricity", (
            "electricity", "electric current", "charge", "potential difference", "voltage",
            "resistance", "ohm's law", "resistor", "series", "parallel", "electric power",
            "heating effect", "fuse",
        )),
        Chapter(12, "Magnetic Effects of Electric Current", (
            "magnetic field", "magnet", "solenoid", "electromagnet", "electric motor",
            "generator", "fleming", "electromagnetic induction", "alternating current",
            "direct current",
        )),
        Chapter(13, "Our Environment", (
            "environment", "ecosystem", "food chain", "food web", "trophic level", "producer",
            "consumer", "decomposer", "biodegradable", "non-biodegradable", "ozone",
            "waste management",
        )),
    ],
)

MATHS_10 = _course(
    10,
    "maths",
    [
        Chapter(1, "Real Numbers", (
            "real number", "euclid's division lemma", "fundamental theorem of arithmetic",
            "hcf", "lcm", "prime factorisation", "rational number", "irrational number",
            "decimal expansion",
        )),
        Chapter(2, "Polynomials", (
            "polynomial", "degree", "zero", "coefficient", "quadratic polynomial",
            "relationship between zeros", "division algorithm",
        )),
        Chapter(3, "Pair of Linear Equations in Two Variables", (
            "linear equation", "two variables", "pair", "graph", "substitution", "elimination",
            "cross multiplication", "consistent", "inconsistent", "dependent",
        )),
        Chapter(4, "Quadratic Equations", (
            "quadratic equation", "root", "factorisation", "completing the square",
            "quadratic formula", "discriminant", "real roots", "equal roots", "sum of roots",
            "product of roots",
        )),
        Chapter(5, "Arithmetic Progressions", (
            "arithmetic progression", "common difference", "nth term",
            "sum of first n terms", "sequence", "series",
        )),
        Chapter(6, "Triangles", (
            "triangle", "similarity", "similar triangles", "basic proportionality theorem",
            "thales", "congruent", "ratio of areas", "pythagoras theorem",
        )),
        Chapter(7, "Coordinate Geometry", (
            "coordinate geometry", "distance formula", "section formula", "midpoint",
            "coordinates", "x-axis", "y-axis", "origin",
        )),
        Chapter(8, "Introduction to Trigonometry", (
            "trigonometry", "trigonometric ratio", "sine", "cosine", "tangent", "cosecant",
            "secant", "cotangent", "right triangle", "angle", "hypotenuse", "opposite",
            "adjacent",
        )),
        Chapter(9, "Some Applications of Trigonometry", (
            "height", "distance", "angle of elevation", "angle of depression", "line of sight",
            "trigonometry", "tower", "building",
        )),
        Chapter(10, "Circles", (
            "circle", "tangent", "secant", "chord", "radius", "diameter", "number of tangents",
            "length of tangent",
        )),
        Chapter(11, "Areas Related to Circles", (
            "area", "circle", "sector", "segment", "circumference", "arc", "radius", "diameter",
            "minor sector", "major sector",
        )),
        Chapter(12, "Surface Areas and Volumes", (
            "surface area", "volume", "cube", "cuboid", "cylinder", "cone", "sphere",
            "hemisphere", "frustum", "capacity",
        )),
        Chapter(13, "Statistics", (
            "statistics", "mean", "median", "mode", "grouped data", "class interval",
            "cumulative frequency", "ogive", "frequency distribution",
        )),
        Chapter(14, "Probability", (
            "probability", "outcome", "event", "sample space", "equally likely",
            "random experiment", "dice", "coin", "deck of cards", "impossible event",
            "sure event",
        )),
    ],
)

COURSES: dict[tuple[int, str], Course] = {
    (8, "science"): SCIENCE_8,
    (8, "maths"): MATHS_8,
    (9, "science"): SCIENCE_9,
    (9, "maths"): MATHS_9,
    (10, "science"): SCIENCE_10,
    (10, "maths"): MATHS_10,
}


def normalize_subject(subject: str) -> str:
    key = subject.strip().lower()
    normalized = _SUBJECT_ALIASES.get(key)
    if normalized is None:
        allowed = ", ".join(SUBJECTS)
        raise ValueError(f"Unknown subject {subject!r}; choose one of: {allowed}")
    return normalized


def get_course(class_level: int, subject: str) -> Course:
    """Return the NCERT course or raise ``ValueError`` with the allowed values."""
    try:
        level = int(class_level)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid class level {class_level!r}") from exc
    normalized = normalize_subject(subject)
    course = COURSES.get((level, normalized))
    if course is None:
        allowed = ", ".join(str(level) for level in CLASS_LEVELS)
        raise ValueError(f"Unsupported class {level}; choose one of: {allowed}")
    return course


def list_courses() -> list[Course]:
    return [COURSES[(level, subject)] for level in CLASS_LEVELS for subject in SUBJECTS]


def course_catalogue() -> list[dict[str, object]]:
    return [course.to_dict() for course in list_courses()]


# ------------------------------------------------------------------ matching
def _stem(token: str) -> str:
    if len(token) > 5 and token.endswith("ies"):
        return token[:-3] + "y"
    for suffix in ("ing", "ed", "es", "s"):
        if len(token) > len(suffix) + 3 and token.endswith(suffix):
            base = token[: -len(suffix)]
            if len(base) > 3 and base[-1] == base[-2]:
                base = base[:-1]
            return base
    return token


def _tokens(text: str) -> list[str]:
    return [_stem(token) for token in _WORD.findall(text.lower())]


def _phrase_stems(phrase: str) -> tuple[str, ...]:
    stems = []
    for token in _WORD.findall(phrase.lower()):
        if len(token) < 2 or token in _TITLE_NOISE or token in _STOPWORDS:
            continue
        stems.append(_stem(token))
    return tuple(stems)


def _ngrams(tokens: list[str], *, max_n: int = 4) -> set[tuple[str, ...]]:
    found: set[tuple[str, ...]] = set()
    for size in range(1, max_n + 1):
        for start in range(0, len(tokens) - size + 1):
            found.add(tuple(tokens[start : start + size]))
    return found


def _candidate_phrases(chapter: Chapter) -> list[str]:
    candidates = [
        token
        for token in _WORD.findall(chapter.title.lower())
        if len(token) > 2 and token not in _TITLE_NOISE
    ]
    candidates.extend(chapter.keywords)
    # Preserve order while removing duplicates.
    cleaned = (candidate.strip().lower() for candidate in candidates)
    return list(dict.fromkeys(candidate for candidate in cleaned if candidate))


@dataclass(frozen=True, slots=True)
class ChapterMatch:
    chapter: Chapter
    score: float
    matched_terms: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "number": self.chapter.number,
            "title": self.chapter.title,
            "score": round(self.score, 2),
            "matched_terms": list(self.matched_terms),
        }


def match_chapters(
    text: str,
    course: Course,
    *,
    limit: int = 3,
    min_score: float = 2.0,
) -> list[ChapterMatch]:
    """Rank the course chapters most likely covered by ``text``.

    A single incidental word is not enough: a chapter needs at least two
    supporting terms (or an explicit "chapter N" mention). Scores favour
    multi-word phrases because they are much less ambiguous than single words.
    """
    tokens = _tokens(text)
    stem_set = set(tokens)
    ngrams = _ngrams(tokens)
    text_words = " ".join(_WORD.findall(text.lower()))
    mentioned_numbers = {
        int(number) for number in _CHAPTER_MENTION.findall(text)
    }

    matches: list[ChapterMatch] = []
    for chapter in course.chapters:
        score = 0.0
        terms: list[str] = []

        if chapter.number in mentioned_numbers:
            score += 3.0
            terms.append(f"chapter {chapter.number}")

        title_words = " ".join(_WORD.findall(chapter.title.lower()))
        if title_words and f" {title_words} " in f" {text_words} ":
            score += 2.0
            terms.append(chapter.title)

        seen: set[tuple[str, ...]] = set()
        for phrase in _candidate_phrases(chapter):
            stems = _phrase_stems(phrase)
            if not stems or stems in seen:
                continue
            seen.add(stems)
            if len(stems) == 1:
                if stems[0] in stem_set:
                    score += 1.0
                    terms.append(phrase)
            elif stems in ngrams:
                score += 1.0 + 0.75 * (len(stems) - 1)
                terms.append(phrase)

        unique_terms = tuple(dict.fromkeys(terms))
        enough_evidence = len(unique_terms) >= 2 or chapter.number in mentioned_numbers
        if score >= min_score and enough_evidence:
            matches.append(
                ChapterMatch(chapter=chapter, score=score, matched_terms=unique_terms[:10])
            )

    matches.sort(key=lambda match: (-match.score, match.chapter.number))
    return matches[:limit]


@dataclass(frozen=True, slots=True)
class SyllabusContext:
    course: Course
    matches: tuple[ChapterMatch, ...]

    @property
    def class_level(self) -> int:
        return self.course.class_level

    @property
    def subject(self) -> str:
        return self.course.subject

    def to_dict(self) -> dict[str, object]:
        return {
            "class_level": self.class_level,
            "subject": self.subject,
            "subject_label": SUBJECT_LABELS[self.subject],
            "course": self.course.label,
            "matches": [match.to_dict() for match in self.matches],
        }

    def prompt(self) -> str:
        lines = [f"Syllabus alignment: {self.course.label} (NCERT)."]
        if self.matches:
            lines.append("This lecture most likely covers:")
            for match in self.matches:
                terms = ", ".join(match.matched_terms[:8])
                suffix = f" (transcript mentions: {terms})" if terms else ""
                lines.append(f"- Chapter {match.chapter.number}: {match.chapter.title}{suffix}.")
            lines.append(
                "When the transcript uses these ideas, prefer the standard NCERT wording and "
                "spelling for the terms."
            )
        else:
            lines.append("No specific chapter matched confidently; do not guess a chapter.")
        lines.append(
            "The syllabus is only a terminology hint. Do not add facts, formulas, examples, "
            "or definitions that the transcript does not contain."
        )
        return "\n".join(lines)


def build_syllabus_context(
    text: str,
    class_level: int,
    subject: str,
    *,
    limit: int = 3,
) -> SyllabusContext:
    course = get_course(class_level, subject)
    return SyllabusContext(course=course, matches=tuple(match_chapters(text, course, limit=limit)))


def estimate_syllabus_confidence(context: SyllabusContext) -> float:
    """A 0-1 score for UI badges; not used by the verifier."""
    if not context.matches:
        return 0.0
    top = context.matches[0].score
    return round(min(1.0, math.log1p(top) / math.log1p(8.0)), 2)
