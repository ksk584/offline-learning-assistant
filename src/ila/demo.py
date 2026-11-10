"""Built-in NCERT demo lectures for the dashboard.

These are short, realistic lecture transcripts written for the three class
levels and two subjects the project targets. They let a teacher or judge see the
whole workflow -- captions, transcript accumulation, syllabus matching and
grounded notes -- without a microphone and without any network access.

Timestamps are synthetic but monotonic, so the caption pane and note timestamps
behave exactly as they do for a real recording.
"""

from __future__ import annotations

from dataclasses import dataclass

from ila.curriculum import CLASS_LEVELS, SUBJECTS


@dataclass(frozen=True, slots=True)
class DemoLine:
    text: str
    start: float
    end: float

    def to_dict(self) -> dict[str, object]:
        return {"text": self.text, "start": self.start, "end": self.end}


@dataclass(frozen=True, slots=True)
class DemoLecture:
    id: str
    title: str
    class_level: int
    subject: str
    chapter: str
    lines: tuple[DemoLine, ...]

    @property
    def chapter_number(self) -> int | None:
        import re

        match = re.search(r"\bchapter\s+(\d{1,2})\b", self.chapter, re.IGNORECASE)
        return int(match.group(1)) if match else None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "class_level": self.class_level,
            "subject": self.subject,
            "chapter": self.chapter,
            "lines": [line.to_dict() for line in self.lines],
        }


def _lines(*rows: tuple[str, float, float]) -> tuple[DemoLine, ...]:
    return tuple(DemoLine(text=text, start=start, end=end) for text, start, end in rows)


DEMOS: tuple[DemoLecture, ...] = (
    DemoLecture(
        id="class8-science-crops",
        title="Crop Production and Management",
        class_level=8,
        subject="science",
        chapter="Chapter 1: Crop Production and Management",
        lines=_lines(
            (
                "Today we will study crop production and management from Chapter 1 of the "
                "NCERT Class 8 Science book.",
                0.0,
                5.4,
            ),
            (
                "Crops are plants that are grown in large quantities for food, fibre or other "
                "useful products.",
                5.8,
                11.6,
            ),
            (
                "India grows two main types of crops: kharif crops and rabi crops.",
                12.0,
                17.4,
            ),
            (
                "Kharif crops are sown in the rainy season and harvested in autumn, for example "
                "paddy and maize.",
                17.8,
                24.2,
            ),
            (
                "Rabi crops are sown in winter and harvested in spring, for example wheat and "
                "mustard.",
                24.6,
                30.4,
            ),
            (
                "Before sowing, the soil is prepared by ploughing, levelling and manuring.",
                30.8,
                36.2,
            ),
            (
                "Ploughing loosens the soil so that roots can breathe and grow easily.",
                36.6,
                41.8,
            ),
            (
                "Manure is organic matter that improves soil fertility and water-holding "
                "capacity.",
                42.2,
                48.0,
            ),
            (
                "Fertilisers are chemical substances that supply specific nutrients like "
                "nitrogen, phosphorus and potassium.",
                48.4,
                55.2,
            ),
            (
                "Irrigation supplies water to crops at regular intervals.",
                55.6,
                60.2,
            ),
            (
                "Weeds are unwanted plants that compete with crops for water, nutrients and "
                "sunlight.",
                60.6,
                66.4,
            ),
            (
                "Weeding is the removal of weeds, and it can be done manually or with "
                "weedicides.",
                66.8,
                72.2,
            ),
            (
                "Harvesting is the cutting of mature crops, followed by threshing to separate "
                "grain from chaff.",
                72.6,
                78.8,
            ),
            (
                "Storage of grains must protect them from moisture, insects and rats.",
                79.2,
                84.4,
            ),
        ),
    ),
    DemoLecture(
        id="class9-science-motion",
        title="Motion: Distance, Velocity and Acceleration",
        class_level=9,
        subject="science",
        chapter="Chapter 7: Motion",
        lines=_lines(
            (
                "Today we will discuss motion, distance and displacement from Chapter 7 of the "
                "NCERT Class 9 Science book.",
                0.0,
                5.6,
            ),
            (
                "An object is said to be in motion if its position changes with respect to time "
                "and a reference point.",
                6.0,
                12.2,
            ),
            (
                "Distance is the total path length travelled by an object, while displacement is "
                "the shortest straight-line distance between the initial and final positions.",
                12.6,
                20.4,
            ),
            (
                "Displacement has both magnitude and direction, so it is a vector quantity.",
                20.8,
                26.6,
            ),
            (
                "Speed is the distance travelled per unit time, and velocity is displacement per "
                "unit time.",
                27.0,
                33.2,
            ),
            (
                "The SI unit of speed and velocity is metres per second.",
                33.6,
                38.0,
            ),
            (
                "Uniform motion means equal distances in equal intervals of time.",
                38.4,
                43.2,
            ),
            (
                "Non-uniform motion means unequal distances in equal intervals of time.",
                43.6,
                48.4,
            ),
            (
                "Acceleration is the rate of change of velocity with time.",
                48.8,
                53.6,
            ),
            (
                "A body has uniform acceleration when its velocity changes by equal amounts in "
                "equal intervals of time.",
                54.0,
                60.2,
            ),
            (
                "The equations of motion relate initial velocity, final velocity, acceleration, "
                "time and displacement.",
                60.6,
                66.8,
            ),
            (
                "For uniform acceleration, we use v equals u plus a t, s equals u t plus half a "
                "t squared, and v squared equals u squared plus two a s.",
                67.2,
                75.4,
            ),
            (
                "Graphs of distance against time and velocity against time help us describe "
                "motion.",
                75.8,
                81.2,
            ),
            (
                "The slope of a velocity-time graph gives acceleration, and the area under it "
                "gives displacement.",
                81.6,
                88.0,
            ),
        ),
    ),
    DemoLecture(
        id="class10-science-light",
        title="Light: Reflection and Refraction",
        class_level=10,
        subject="science",
        chapter="Chapter 9: Light - Reflection and Refraction",
        lines=_lines(
            (
                "Today we will study light, reflection and refraction from Chapter 9 of the "
                "NCERT Class 10 Science book.",
                0.0,
                6.0,
            ),
            (
                "Light is a form of energy that travels in straight lines and allows us to see "
                "objects.",
                6.4,
                12.2,
            ),
            (
                "When light falls on a polished surface, it bounces back. This phenomenon is "
                "called reflection.",
                12.6,
                19.0,
            ),
            (
                "The ray that strikes the mirror is the incident ray, and the ray that comes "
                "back is the reflected ray.",
                19.4,
                26.2,
            ),
            (
                "The angle of incidence is always equal to the angle of reflection. This is the "
                "law of reflection.",
                26.6,
                33.4,
            ),
            (
                "A plane mirror forms a virtual and erect image of the same size as the object.",
                33.8,
                39.6,
            ),
            (
                "The image is formed behind the mirror at the same distance as the object in "
                "front of it.",
                40.0,
                46.0,
            ),
            (
                "Spherical mirrors are of two types: concave mirrors and convex mirrors.",
                46.4,
                51.6,
            ),
            (
                "A concave mirror is a converging mirror, and a convex mirror is a diverging "
                "mirror.",
                52.0,
                58.0,
            ),
            (
                "The principal focus is the point where rays parallel to the principal axis meet "
                "after reflection.",
                58.4,
                65.2,
            ),
            (
                "The distance from the pole to the principal focus is called the focal length.",
                65.6,
                71.0,
            ),
            (
                "When light travels from one transparent medium to another, it bends. This is "
                "called refraction.",
                71.4,
                78.2,
            ),
            (
                "Refraction happens because the speed of light is different in different media.",
                78.6,
                84.0,
            ),
            (
                "The refractive index measures how much a medium slows down light.",
                84.4,
                89.6,
            ),
            (
                "A lens can also converge or diverge light, just like a spherical mirror.",
                90.0,
                95.6,
            ),
        ),
    ),
    DemoLecture(
        id="class8-maths-squares",
        title="Squares and Square Roots",
        class_level=8,
        subject="maths",
        chapter="Chapter 5: Squares and Square Roots",
        lines=_lines(
            (
                "Today we will study squares and square roots from Chapter 5 of the NCERT Class "
                "8 Mathematics book.",
                0.0,
                5.8,
            ),
            (
                "When a number is multiplied by itself, the product is called the square of that "
                "number.",
                6.2,
                12.0,
            ),
            (
                "For example, seven multiplied by seven is forty-nine, so forty-nine is the "
                "square of seven.",
                12.4,
                18.6,
            ),
            (
                "A perfect square is a number that is the square of an integer.",
                19.0,
                24.0,
            ),
            (
                "Numbers ending in two, three, seven or eight are never perfect squares.",
                24.4,
                29.8,
            ),
            (
                "The square of an even number is even, and the square of an odd number is odd.",
                30.2,
                36.0,
            ),
            (
                "The square root of a number is the value that, when multiplied by itself, gives "
                "the original number.",
                36.4,
                43.2,
            ),
            (
                "The square root symbol is called the radical sign.",
                43.6,
                48.0,
            ),
            (
                "We can find square roots by repeated subtraction, by prime factorisation, or by "
                "the long division method.",
                48.4,
                55.6,
            ),
            (
                "In prime factorisation, we pair equal factors and take one factor from each "
                "pair.",
                56.0,
                62.0,
            ),
            (
                "The square root of one hundred and forty-four is twelve, because twelve times "
                "twelve is one hundred and forty-four.",
                62.4,
                69.8,
            ),
            (
                "Square roots are useful in geometry, especially when finding the side of a "
                "square from its area.",
                70.2,
                76.6,
            ),
        ),
    ),
    DemoLecture(
        id="class9-maths-number-systems",
        title="Number Systems",
        class_level=9,
        subject="maths",
        chapter="Chapter 1: Number Systems",
        lines=_lines(
            (
                "Today we will study number systems from Chapter 1 of the NCERT Class 9 "
                "Mathematics book.",
                0.0,
                5.6,
            ),
            (
                "Natural numbers are counting numbers, and whole numbers include zero along with "
                "the natural numbers.",
                6.0,
                12.4,
            ),
            (
                "Integers include positive numbers, negative numbers and zero.",
                12.8,
                18.0,
            ),
            (
                "Rational numbers can be written in the form p by q, where p and q are integers "
                "and q is not zero.",
                18.4,
                25.6,
            ),
            (
                "Irrational numbers cannot be written as a ratio of two integers.",
                26.0,
                31.2,
            ),
            (
                "The square root of two is an irrational number.",
                31.6,
                36.2,
            ),
            (
                "Every real number is either rational or irrational.",
                36.6,
                41.2,
            ),
            (
                "We can represent real numbers on the number line.",
                41.6,
                46.2,
            ),
            (
                "Between any two rational numbers, there are infinitely many rational numbers.",
                46.6,
                52.4,
            ),
            (
                "The decimal expansion of a rational number either terminates or repeats.",
                52.8,
                58.4,
            ),
            (
                "The decimal expansion of an irrational number is non-terminating and "
                "non-repeating.",
                58.8,
                64.6,
            ),
            (
                "We use laws of exponents to simplify expressions with powers.",
                65.0,
                70.2,
            ),
            (
                "Rationalisation removes a square root from the denominator by multiplying with "
                "its conjugate.",
                70.6,
                77.2,
            ),
        ),
    ),
    DemoLecture(
        id="class10-maths-quadratics",
        title="Quadratic Equations",
        class_level=10,
        subject="maths",
        chapter="Chapter 4: Quadratic Equations",
        lines=_lines(
            (
                "Today we will study quadratic equations from Chapter 4 of the NCERT Class 10 "
                "Mathematics book.",
                0.0,
                5.8,
            ),
            (
                "A quadratic equation is an equation of the form a x squared plus b x plus c "
                "equals zero, where a is not equal to zero.",
                6.2,
                14.0,
            ),
            (
                "The degree of a quadratic equation is two, so it has at most two roots.",
                14.4,
                20.0,
            ),
            (
                "A real number alpha is a root if it satisfies the equation.",
                20.4,
                25.4,
            ),
            (
                "We can find the roots by factorisation, by completing the square, or by using "
                "the quadratic formula.",
                25.8,
                32.6,
            ),
            (
                "The quadratic formula is x equals minus b plus or minus the square root of b "
                "squared minus four a c, all divided by two a.",
                33.0,
                41.4,
            ),
            (
                "The expression b squared minus four a c is called the discriminant.",
                41.8,
                47.6,
            ),
            (
                "If the discriminant is positive, the equation has two distinct real roots.",
                48.0,
                53.8,
            ),
            (
                "If the discriminant is zero, the equation has two equal real roots.",
                54.2,
                59.4,
            ),
            (
                "If the discriminant is negative, the equation has no real roots.",
                59.8,
                64.8,
            ),
            (
                "The sum of the roots is minus b by a, and the product of the roots is c by a.",
                65.2,
                71.6,
            ),
            (
                "We can use quadratic equations to solve problems about areas, speeds and ages.",
                72.0,
                78.2,
            ),
        ),
    ),
)

DEMOS_BY_ID = {demo.id: demo for demo in DEMOS}


def demo_summaries() -> list[dict[str, object]]:
    return [
        {
            "id": demo.id,
            "title": demo.title,
            "class_level": demo.class_level,
            "subject": demo.subject,
            "chapter": demo.chapter,
        }
        for demo in DEMOS
    ]


def find_demo(class_level: int, subject: str) -> tuple[DemoLecture, bool]:
    """Return the best demo for a class/subject pair and whether it is exact."""
    normalized_subject = subject.strip().lower()
    for demo in DEMOS:
        if demo.class_level == class_level and demo.subject == normalized_subject:
            return demo, True
    for demo in DEMOS:
        if demo.class_level == class_level:
            return demo, False
    for demo in DEMOS:
        if demo.subject == normalized_subject:
            return demo, False
    return DEMOS[0], False


def validate_selection(class_level: int, subject: str) -> None:
    if class_level not in CLASS_LEVELS:
        allowed = ", ".join(str(level) for level in CLASS_LEVELS)
        raise ValueError(f"Unsupported class {class_level}; choose one of: {allowed}")
    if subject.strip().lower() not in SUBJECTS:
        allowed = ", ".join(SUBJECTS)
        raise ValueError(f"Unknown subject {subject!r}; choose one of: {allowed}")
