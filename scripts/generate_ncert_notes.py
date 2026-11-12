"""NCERT Study Notes Generator using Local LLM (ILA Project).

Generates comprehensive, concise, 10-page study notes for NCERT Class 10
Mathematics Units 1 to 3:
- Unit 1: Real Numbers (jemh101.pdf)
- Unit 2: Polynomials (jemh102.pdf)
- Unit 3: Pair of Linear Equations in Two Variables (jemh103.pdf)

Uses the project's local LLM (Qwen3.5 via llama-cpp-python).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from ila.config import LlmSettings
from ila.llm.llama_cpp import LlamaCppProvider

PROJECT_ROOT = Path(__file__).resolve().parent.parent
NCERT_DIR = PROJECT_ROOT / "ncert_books"
NOTES_DIR = PROJECT_ROOT / "notes"
MODELS_DIR = PROJECT_ROOT / "models" / "llm"


def get_default_model_path() -> Path:
    # Prefer 0.8B for fast generation or 2B if specified
    m08 = MODELS_DIR / "Qwen3.5-0.8B-Q4_K_M.gguf"
    m2 = MODELS_DIR / "Qwen3.5-2B-Q4_K_M.gguf"
    if m08.exists():
        return m08
    if m2.exists():
        return m2
    raise FileNotFoundError(f"No GGUF models found in {MODELS_DIR}")


# System prompt ensuring high academic density, rigor, and conciseness
SYSTEM_PROMPT = (
    "You are an elite mathematics professor and textbook author creating master-level study notes "
    "for NCERT Class 10 Mathematics. "
    "Your writing must be concise, high-density, rigorous, and directly pedagogical. "
    "Format strictly with GitHub-flavored markdown and LaTeX for all mathematical expressions ($...$ and $$...$$). "
    "Do NOT output conversational filler, greetings, or meta-commentary (such as 'Here are the notes'). "
    "Include precise mathematical definitions, theorems, detailed step-by-step proofs, formulas, "
    "worked examples with full algebraic derivations, common student traps, and structured review drills."
)


UNIT_DEFINITIONS = {
    1: {
        "title": "Unit 1: Real Numbers",
        "chapter_code": "jemh101",
        "output_filename": "Unit_1_Real_Numbers_Notes.md",
        "text_file": PROJECT_ROOT / "scratch" / "jemh101.pdf.txt",
        "sections": [
            {
                "id": "1.1",
                "title": "Chapter Blueprint, Syllabus Scope & Learning Objectives",
                "prompt": (
                    "Generate a comprehensive, high-density 'Chapter Blueprint & Syllabus Scope' for Unit 1: Real Numbers (NCERT Class 10).\n"
                    "Include:\n"
                    "1. Pedagogical Scope & CBSE/NCERT Curriculum Alignment.\n"
                    "2. Prerequisite Knowledge (from Class 9 Number Systems).\n"
                    "3. Core Competencies & Key Learning Objectives (Fundamental Theorem of Arithmetic, irrationality proofs, HCF/LCM relations).\n"
                    "4. Concept Mindmap / Architecture Table listing all modules, key ideas, and weightage hints.\n"
                    "Use precise LaTeX math where relevant. Be concise, academic, and detailed."
                ),
                "max_tokens": 750,
            },
            {
                "id": "1.2",
                "title": "Core Number Systems & Foundational Definitions",
                "prompt": (
                    "Generate 'Core Number Systems & Foundational Definitions' for Unit 1: Real Numbers.\n"
                    "Cover in depth:\n"
                    "1. Set-theoretic hierarchy of Real Numbers: Natural ($\mathbb{N}$), Whole ($\mathbb{W}$), Integers ($\mathbb{Z}$), "
                    "Rational ($\mathbb{Q}$ where $q \\neq 0$), Irrational ($\mathbb{I}$), and Real Numbers ($\mathbb{R} = \mathbb{Q} \cup \mathbb{I}$).\n"
                    "2. Prime vs Composite numbers: formal definitions, why 1 is neither prime nor composite, coprime numbers definition.\n"
                    "3. Factor Trees: Definition, mechanics, and branching representation for large numbers (e.g., $32760$).\n"
                    "4. Decimal Expansions: Conditions on denominator $q = 2^m 5^n$ for terminating vs non-terminating repeating decimals.\n"
                    "Provide clear LaTeX definitions and concise markdown tables."
                ),
                "max_tokens": 750,
            },
            {
                "id": "1.3",
                "title": "The Fundamental Theorem of Arithmetic (Theorem 1.1)",
                "prompt": (
                    "Generate a rigorous, comprehensive section on 'The Fundamental Theorem of Arithmetic (Theorem 1.1)' for NCERT Class 10.\n"
                    "Include:\n"
                    "1. Historical background (Euclid's Elements Book IX Prop 14, Carl Friedrich Gauss in Disquisitiones Arithmeticae).\n"
                    "2. Formal Statement of Theorem 1.1: Every composite number can be uniquely expressed as a product of primes, "
                    "apart from the order of factors.\n"
                    "3. Canonical Prime Factorization: Form $x = p_1^{a_1} p_2^{a_2} \\cdots p_k^{a_k}$ with $p_1 < p_2 < \\dots < p_k$.\n"
                    "4. Prime Factorization Method for HCF and LCM:\n"
                    "   - $\\text{HCF}(a, b) = \\text{Product of smallest powers of each common prime factor}$.\n"
                    "   - $\\text{LCM}(a, b) = \\text{Product of greatest powers of each prime factor involved}$.\n"
                    "5. Fundamental Identity: $\\text{HCF}(a, b) \\times \\text{LCM}(a, b) = a \\times b$.\n"
                    "6. Vital Warning: Why $\\text{HCF}(p, q, r) \\times \\text{LCM}(p, q, r) \\neq p \\times q \\times r$ for three numbers, and state the correct 3-number formulas."
                ),
                "max_tokens": 750,
            },
            {
                "id": "1.4",
                "title": "Revisiting Irrational Numbers & Rigorous Proofs (Theorems 1.2 & 1.3)",
                "prompt": (
                    "Generate a thorough, rigorous section on 'Revisiting Irrational Numbers & Contradiction Proofs' for NCERT Class 10.\n"
                    "Include:\n"
                    "1. Theorem 1.2: If $p$ is prime and $p \\mid a^2$, then $p \\mid a$ (where $a \\in \\mathbb{Z}^+$). Provide the full, formal proof using prime factorisation of $a$.\n"
                    "2. Proof by Contradiction Technique: Logical framework ($P \\implies Q$ vs assuming $\\neg P$).\n"
                    "3. Complete Formal Proof that $\\sqrt{2}$ is irrational (Theorem 1.3): Step-by-step, assuming $a/b$ coprime, squaring, showing 2 divides $a$ and $b$, concluding contradiction.\n"
                    "4. Proof that $\\sqrt{3}$ and $\\sqrt{5}$ are irrational.\n"
                    "5. Properties of Arithmetic with Irrationals: Rational $\\pm$ Irrational = Irrational, Non-zero Rational $\\times$ Irrational = Irrational (with short proofs for $5 - \\sqrt{3}$ and $3\\sqrt{2}$)."
                ),
                "max_tokens": 750,
            },
            {
                "id": "1.5",
                "title": "Master Formula Repository & Quick-Reference Tables",
                "prompt": (
                    "Create a 'Master Formula Repository & Comparative Tables' for Unit 1: Real Numbers.\n"
                    "Include comprehensive tables for:\n"
                    "1. Number Classifications, Symbols, and Defining Conditions.\n"
                    "2. HCF and LCM Formulas for Two and Three Numbers.\n"
                    "3. Decimal Expansion Characterization Criteria ($q = 2^n 5^m$).\n"
                    "4. Divisibility and Prime Factorization Invariants (e.g. condition for $a^n$ ending in 0: must contain prime factors 2 and 5).\n"
                    "5. Summary of Key Theorems with formal conditions and mathematical consequences.\n"
                    "Format cleanly in Markdown tables and concise formula cheat-sheet cards."
                ),
                "max_tokens": 750,
            },
            {
                "id": "1.6",
                "title": "Standard Algorithmic Procedures & Step-by-Step Methodologies",
                "prompt": (
                    "Provide clear, numbered, step-by-step algorithmic workflows for Unit 1: Real Numbers:\n"
                    "1. Algorithm 1: Prime Factorisation of Large Composite Numbers using Factor Trees.\n"
                    "2. Algorithm 2: Finding HCF and LCM of Two Numbers and Verifying $\\text{HCF} \\times \\text{LCM} = a \\times b$.\n"
                    "3. Algorithm 3: Finding HCF and LCM of Three Numbers using Prime Powers.\n"
                    "4. Algorithm 4: Checking if $a^n$ (e.g. $4^n, 6^n$) can end with digit 0 for any $n \\in \\mathbb{N}$.\n"
                    "5. Algorithm 5: Standard Contradiction Template for proving irrationality of $\\sqrt{p}$ and composite irrationals ($a + b\\sqrt{p}$)."
                ),
                "max_tokens": 750,
            },
            {
                "id": "1.7",
                "title": "Foundational & Concept-Building Worked Examples",
                "prompt": (
                    "Generate fully worked, mathematically rigorous foundational examples for Unit 1: Real Numbers:\n"
                    "1. Example 1: Check whether $4^n$ can end with digit zero for any natural number $n$ (detailed solution using Fundamental Theorem of Arithmetic).\n"
                    "2. Example 2: Check whether $6^n$ can end with digit zero for any natural number $n$.\n"
                    "3. Example 3: Find HCF and LCM of 6 and 20 using prime factorisation; verify the product rule.\n"
                    "4. Example 4: Find HCF of 96 and 404 by prime factorisation; hence find their LCM.\n"
                    "5. Example 5: Find HCF and LCM of 6, 72, and 120; explicitly demonstrate why the 2-number product rule fails here.\n"
                    "Provide complete mathematical steps, explanations, and key takeaways for each."
                ),
                "max_tokens": 750,
            },
            {
                "id": "1.8",
                "title": "NCERT Standard, Application-Level & HOTS Problems",
                "prompt": (
                    "Generate advanced, application-level, and HOTS (Higher Order Thinking Skills) worked problems for Unit 1: Real Numbers:\n"
                    "1. Problem 1: Prove that $7 \\times 11 \\times 13 + 13$ and $7 \\times 6 \\times 5 \\times 4 \\times 3 \\times 2 \\times 1 + 5$ are composite numbers (step-by-step factorization).\n"
                    "2. Problem 2: Circular track word problem: Sonia takes 18 minutes and Ravi takes 12 minutes to complete one lap. If they start together, after how many minutes will they meet at the starting point? (Modeling with LCM, full explanation).\n"
                    "3. Problem 3: Given $\\text{HCF}(306, 657) = 9$, find $\\text{LCM}(306, 657)$ using the algebraic relation.\n"
                    "4. Problem 4: Prove that $3 + 2\\sqrt{5}$ is irrational, given that $\\sqrt{5}$ is irrational.\n"
                    "5. Problem 5: Prove that $\\frac{1}{\\sqrt{2}}$ is irrational.\n"
                    "Include complete algebraic derivations and formal concluding statements."
                ),
                "max_tokens": 750,
            },
            {
                "id": "1.9",
                "title": "Common Misconceptions, Pitfalls & Critical Exam Traps",
                "prompt": (
                    "Detail the top common misconceptions, student pitfalls, and exam traps for NCERT Class 10 Real Numbers:\n"
                    "1. Trap 1: Assuming $\\text{HCF}(a, b, c) \\times \\text{LCM}(a, b, c) = a \\times b \\times c$ (Explain the fallacy with counterexamples).\n"
                    "2. Trap 2: Incomplete coprime declaration in contradiction proofs (why omitting 'a and b are coprime' invalidates the proof).\n"
                    "3. Trap 3: Confusion between HCF and LCM in real-world word problems (How to recognize minimum time / common meeting = LCM vs dividing items into equal piles = HCF).\n"
                    "4. Trap 4: Misapplying Theorem 1.2 when $p$ is not prime (e.g. 4 divides $6^2 = 36$, but 4 does not divide 6; why prime condition is essential).\n"
                    "5. Trap 5: Proving $a + \\sqrt{b}$ irrational by starting from scratch vs using given irrationality of $\\sqrt{b}$.\n"
                    "Provide explicit 'Incorrect Method' vs 'Correct Method' comparisons."
                ),
                "max_tokens": 750,
            },
            {
                "id": "1.10",
                "title": "NCERT Exercise Walkthrough, Summary Checklist & Practice Drill",
                "prompt": (
                    "Provide the concluding review module for Unit 1: Real Numbers:\n"
                    "1. Complete Breakdown and Mapping of NCERT Exercises 1.1 and 1.2.\n"
                    "2. Rapid-Fire Revision Checklist (10 bullet points every student must memorize before exams).\n"
                    "3. Self-Assessment Practice Drill:\n"
                    "   - 4 Multiple Choice Questions (with tricky distractors)\n"
                    "   - 2 Short Answer Questions (2 marks each)\n"
                    "   - 2 Long Answer Questions (Proof-based, 3-5 marks each)\n"
                    "4. Complete Answer Key and Detailed Solutions for all practice drill questions."
                ),
                "max_tokens": 750,
            },
        ],
    },
    2: {
        "title": "Unit 2: Polynomials",
        "chapter_code": "jemh102",
        "output_filename": "Unit_2_Polynomials_Notes.md",
        "text_file": PROJECT_ROOT / "scratch" / "jemh102.pdf.txt",
        "sections": [
            {
                "id": "2.1",
                "title": "Chapter Blueprint, Syllabus Scope & Prerequisites",
                "prompt": (
                    "Generate a comprehensive 'Chapter Blueprint & Syllabus Scope' for Unit 2: Polynomials (NCERT Class 10).\n"
                    "Include:\n"
                    "1. Pedagogical Scope & CBSE/NCERT Curriculum Alignment.\n"
                    "2. Prerequisites from Class 9: Polynomial definition in one variable, non-polynomial expressions ($1/x, \\sqrt{x}$), terms, coefficients.\n"
                    "3. Classification by Degree: Linear ($n=1$), Quadratic ($n=2$, etymology from 'quadrate'), Cubic ($n=3$).\n"
                    "4. Value of a polynomial at $x = k$ ($p(k)$) and formal definition of a Zero of a polynomial ($p(k) = 0$).\n"
                    "Use precise LaTeX math and structured markdown tables."
                ),
                "max_tokens": 750,
            },
            {
                "id": "2.2",
                "title": "Geometrical Meaning of the Zeroes of a Polynomial",
                "prompt": (
                    "Generate a thorough, rigorous section on 'Geometrical Meaning of the Zeroes of a Polynomial' for NCERT Class 10.\n"
                    "Cover:\n"
                    "1. Fundamental Geometric Principle: The zeroes of $y = p(x)$ are the exact $x$-coordinates of the points where the graph intersects the $x$-axis.\n"
                    "2. Linear Polynomial $y = ax + b$ ($a \\neq 0$): Straight line graph, intersects $x$-axis at exactly one point $(-b/a, 0)$.\n"
                    "3. Quadratic Polynomial $y = ax^2 + bx + c$ ($a \\neq 0$): Parabolic curve.\n"
                    "   - Direction: Opens upwards if $a > 0$, opens downwards if $a < 0$.\n"
                    "   - Three Geometric Cases:\n"
                    "     * Case 1: Intersects $x$-axis at 2 distinct points $\\implies 2$ distinct real zeroes.\n"
                    "     * Case 2: Touches $x$-axis at 1 point (coincident points) $\\implies 1$ real zero (two equal zeroes).\n"
                    "     * Case 3: Completely above or below $x$-axis (no intersection) $\\implies 0$ real zeroes.\n"
                    "   - Fundamental Theorem: A polynomial of degree $n$ has at most $n$ real zeroes.\n"
                    "4. Cubic Polynomials: Shape of $y = x^3 - 4x$, $y = x^3$, $y = x^3 - x^2$; can have 1, 2, or 3 real zeroes (at most 3)."
                ),
                "max_tokens": 750,
            },
            {
                "id": "2.3",
                "title": "Relationship Between Zeroes and Coefficients (Quadratic Polynomials)",
                "prompt": (
                    "Generate a rigorous mathematical exposition on 'Relationship Between Zeroes and Coefficients of a Quadratic Polynomial' for NCERT Class 10.\n"
                    "Cover:\n"
                    "1. Derivation: Let $\\alpha, \\beta$ be zeroes of $p(x) = ax^2 + bx + c$ ($a \\neq 0$). Then $(x - \\alpha)$ and $(x - \\beta)$ are factors.\n"
                    "   $ax^2 + bx + c = k(x - \\alpha)(x - \\beta) = k[x^2 - (\\alpha + \\beta)x + \\alpha\\beta]$.\n"
                    "   Equating coefficients of $x^2, x$, and constant term to obtain:\n"
                    "   - $\\alpha + \\beta = -\\frac{b}{a} = -\\frac{\\text{Coefficient of } x}{\\text{Coefficient of } x^2}$\n"
                    "   - $\\alpha\\beta = \\frac{c}{a} = \\frac{\\text{Constant term}}{\\text{Coefficient of } x^2}$\n"
                    "2. Forming a Quadratic Polynomial given sum ($S$) and product ($P$) of zeroes:\n"
                    "   $p(x) = k[x^2 - Sx + P] = k[x^2 - (\\alpha + \\beta)x + \\alpha\\beta]$, where $k \\in \\mathbb{R}, k \\neq 0$.\n"
                    "3. Method of Splitting the Middle Term: Step-by-step logic ($ac$ product and sum $b$)."
                ),
                "max_tokens": 750,
            },
            {
                "id": "2.4",
                "title": "Relationship Between Zeroes and Coefficients (Cubic Polynomials)",
                "prompt": (
                    "Generate a detailed, rigorous section on 'Relationship Between Zeroes and Coefficients of a Cubic Polynomial' for NCERT Class 10.\n"
                    "Cover:\n"
                    "1. General cubic polynomial: $p(x) = ax^3 + bx^2 + cx + d$ ($a \\neq 0$).\n"
                    "2. If $\\alpha, \\beta, \\gamma$ are zeroes, then:\n"
                    "   - Sum of zeroes: $\\alpha + \\beta + \\gamma = -\\frac{b}{a} = -\\frac{\\text{Coefficient of } x^2}{\\text{Coefficient of } x^3}$\n"
                    "   - Sum of products taken two at a time: $\\alpha\\beta + \\beta\\gamma + \\gamma\\alpha = \\frac{c}{a} = \\frac{\\text{Coefficient of } x}{\\text{Coefficient of } x^3}$\n"
                    "   - Product of zeroes: $\\alpha\\beta\\gamma = -\\frac{d}{a} = -\\frac{\\text{Constant term}}{\\text{Coefficient of } x^3}$\n"
                    "3. Constructing a cubic polynomial: $p(x) = k[x^3 - (\\alpha+\\beta+\\gamma)x^2 + (\\alpha\\beta+\\beta\\gamma+\\gamma\\alpha)x - \\alpha\\beta\\gamma]$.\n"
                    "4. Fully worked verification example: $p(x) = 3x^3 - 5x^2 - 11x - 3$ with zeroes $3, -1, -1/3$."
                ),
                "max_tokens": 750,
            },
            {
                "id": "2.5",
                "title": "Master Formula Repository & Symmetric Functions of Zeroes",
                "prompt": (
                    "Create a comprehensive 'Master Formula Repository & Symmetric Functions of Zeroes' for Unit 2: Polynomials.\n"
                    "Include:\n"
                    "1. Master Table of Relations between zeroes and coefficients for Linear, Quadratic, and Cubic polynomials.\n"
                    "2. Useful Symmetric Algebraic Identities expressed in terms of $(\\alpha+\\beta)$ and $\\alpha\\beta$:\n"
                    "   - $\\alpha^2 + \\beta^2 = (\\alpha + \\beta)^2 - 2\\alpha\\beta$\n"
                    "   - $(\\alpha - \\beta)^2 = (\\alpha + \\beta)^2 - 4\\alpha\\beta \\implies |\\alpha - \\beta| = \\sqrt{(\\alpha + \\beta)^2 - 4\\alpha\\beta}$\n"
                    "   - $\\alpha^3 + \\beta^3 = (\\alpha + \\beta)^3 - 3\\alpha\\beta(\\alpha + \\beta)$\n"
                    "   - $\\frac{1}{\\alpha} + \\frac{1}{\\beta} = \\frac{\\alpha + \\beta}{\\alpha\\beta}$\n"
                    "   - $\\frac{\\alpha}{\\beta} + \\frac{\\beta}{\\alpha} = \\frac{\\alpha^2 + \\beta^2}{\\alpha\\beta} = \\frac{(\\alpha + \\beta)^2 - 2\\alpha\\beta}{\\alpha\\beta}$\n"
                    "   - $\\alpha^4 + \\beta^4 = [(\\alpha + \\beta)^2 - 2\\alpha\\beta]^2 - 2(\\alpha\\beta)^2$\n"
                    "Format in clean markdown reference cards and LaTeX tables."
                ),
                "max_tokens": 750,
            },
            {
                "id": "2.6",
                "title": "Standard Algorithmic Procedures & Step-by-Step Methods",
                "prompt": (
                    "Provide structured, numbered algorithmic recipes for Unit 2: Polynomials:\n"
                    "1. Algorithm 1: Finding Zeroes of a Quadratic Polynomial by Splitting the Middle Term.\n"
                    "2. Algorithm 2: Finding Zeroes using Difference of Squares identity ($a^2 - b^2$, e.g. $x^2 - 3, t^2 - 15$).\n"
                    "3. Algorithm 3: Verifying the Relationship between Zeroes and Coefficients step-by-step.\n"
                    "4. Algorithm 4: Constructing a Quadratic Polynomial when Sum and Product of zeroes are given (handling fractions/denominators cleanly).\n"
                    "5. Algorithm 5: Determining the Number of Zeroes from Any Given Graph."
                ),
                "max_tokens": 750,
            },
            {
                "id": "2.7",
                "title": "Foundational & Concept-Building Worked Examples",
                "prompt": (
                    "Generate fully worked foundational examples with complete algebraic derivations for Unit 2: Polynomials:\n"
                    "1. Example 1: Find zeroes of $p(x) = x^2 + 7x + 10$ and verify the relationship with coefficients.\n"
                    "2. Example 2: Find zeroes of $p(x) = x^2 - 3$ and verify the relationship with coefficients.\n"
                    "3. Example 3: Find zeroes of $p(x) = 6x^2 - 3 - 7x$ (emphasizing standard form arrangement $ax^2 + bx + c$).\n"
                    "4. Example 4: Find zeroes of $p(u) = 4u^2 + 8u$ (taking common factors where $c = 0$).\n"
                    "5. Example 5: Find zeroes of $p(t) = t^2 - 15$ and verify relations.\n"
                    "Include complete intermediate steps and verification tables."
                ),
                "max_tokens": 750,
            },
            {
                "id": "2.8",
                "title": "NCERT Standard, Application-Level & HOTS Problems",
                "prompt": (
                    "Generate advanced, application-level, and HOTS worked problems for Unit 2: Polynomials:\n"
                    "1. Problem 1: Find a quadratic polynomial where sum of zeroes is $\\sqrt{2}$ and product is $1/3$.\n"
                    "2. Problem 2: Find a quadratic polynomial where sum of zeroes is $-1/4$ and product is $1/4$.\n"
                    "3. Problem 3: If $\\alpha, \\beta$ are zeroes of $p(x) = 2x^2 - 5x + 7$, find the value of (i) $\\alpha^2 + \\beta^2$, (ii) $\\frac{1}{\\alpha} + \\frac{1}{\\beta}$.\n"
                    "4. Problem 4: If one zero of the polynomial $(k-1)x^2 + kx + 1$ is $-3$, find the value of $k$.\n"
                    "5. Problem 5: If the sum of zeroes of quadratic polynomial $kx^2 + 2x + 3k$ is equal to their product, find the value of $k$.\n"
                    "Provide rigorous, line-by-line solutions."
                ),
                "max_tokens": 750,
            },
            {
                "id": "2.9",
                "title": "Common Misconceptions, Graphical Traps & Error Analysis",
                "prompt": (
                    "Detail the top common misconceptions, graphical traps, and student pitfalls for Unit 2: Polynomials:\n"
                    "1. Trap 1: Counting $y$-axis intersections as zeroes instead of $x$-axis intersections.\n"
                    "2. Trap 2: Forgetting to rearrange terms into standard form $ax^2 + bx + c$ before extracting coefficients (e.g., $6x^2 - 3 - 7x \\implies b = -7$, not $-3$).\n"
                    "3. Trap 3: Sign error in the sum of zeroes formula: $\\alpha + \\beta = -b/a$, forgetting the negative sign.\n"
                    "4. Trap 4: Confusing a zero of a polynomial ($x=k$) with the value of the polynomial at zero ($p(0)$).\n"
                    "5. Trap 5: Omitting the arbitrary constant $k$ when forming polynomials, or failing to clear fractional denominators.\n"
                    "Provide explicit 'Incorrect Approach' vs 'Correct Approach' comparisons."
                ),
                "max_tokens": 750,
            },
            {
                "id": "2.10",
                "title": "NCERT Exercise Walkthrough, Summary Checklist & Practice Drill",
                "prompt": (
                    "Provide the concluding review module for Unit 2: Polynomials:\n"
                    "1. Complete Walkthrough and Mapping of NCERT Exercises 2.1 and 2.2.\n"
                    "2. Rapid-Fire Revision Checklist (10 bullet points for high-yield exam recall).\n"
                    "3. Self-Assessment Practice Drill:\n"
                    "   - 4 Multiple Choice Questions (with graphical and coefficient questions)\n"
                    "   - 2 Short Answer Questions (2 marks each)\n"
                    "   - 2 Long Answer Questions (3-5 marks each, including symmetric function evaluation)\n"
                    "4. Complete Answer Key and Detailed Solutions for all practice drill questions."
                ),
                "max_tokens": 750,
            },
        ],
    },
    3: {
        "title": "Unit 3: Pair of Linear Equations in Two Variables",
        "chapter_code": "jemh103",
        "output_filename": "Unit_3_Pair_of_Linear_Equations_Notes.md",
        "text_file": PROJECT_ROOT / "scratch" / "jemh103.pdf.txt",
        "sections": [
            {
                "id": "3.1",
                "title": "Chapter Blueprint, Syllabus Scope & Real-Life Modeling",
                "prompt": (
                    "Generate a comprehensive 'Chapter Blueprint & Real-Life Modeling' section for Unit 3: Pair of Linear Equations in Two Variables (NCERT Class 10).\n"
                    "Cover:\n"
                    "1. Pedagogical Scope & CBSE/NCERT Curriculum Alignment.\n"
                    "2. Definition of a Linear Equation in Two Variables: $ax + by + c = 0$ ($a, b, c \\in \\mathbb{R}$, $a^2 + b^2 \\neq 0$).\n"
                    "3. Geometric Meaning of a Solution: Any point $(x_0, y_0)$ lying on the straight line satisfies the equation.\n"
                    "4. General Form of a Pair of Linear Equations in Two Variables:\n"
                    "   $a_1 x + b_1 y + c_1 = 0$\n"
                    "   $a_2 x + b_2 y + c_2 = 0$\n"
                    "5. Real-World Modeling: Translating word problems into algebraic systems (e.g. Akhila's Giant Wheel and Hoopla example, fares, ages)."
                ),
                "max_tokens": 750,
            },
            {
                "id": "3.2",
                "title": "Graphical Method & The Ratio Consistency Criteria",
                "prompt": (
                    "Generate a thorough, rigorous section on 'Graphical Method & Ratio Comparison Criteria' for Unit 3.\n"
                    "Cover:\n"
                    "1. Geometric Behaviour of Two Lines in a Plane: Intersecting, Parallel, Coincident.\n"
                    "2. Consistency Definitions: Consistent (at least one solution), Inconsistent (no solution), Dependent (infinitely many solutions, always consistent).\n"
                    "3. Master Coefficient Ratio Comparison Criteria:\n"
                    "   - Case 1: $\\frac{a_1}{a_2} \\neq \\frac{b_1}{b_2} \\implies$ Intersecting lines, Exactly 1 unique solution, Consistent system.\n"
                    "   - Case 2: $\\frac{a_1}{a_2} = \\frac{b_1}{b_2} = \\frac{c_1}{c_2} \\implies$ Coincident lines, Infinitely many solutions, Consistent (dependent).\n"
                    "   - Case 3: $\\frac{a_1}{a_2} = \\frac{b_1}{b_2} \\neq \\frac{c_1}{c_2} \\implies$ Parallel lines, No solution, Inconsistent system.\n"
                    "4. Tabular Summary with examples illustrating each case."
                ),
                "max_tokens": 750,
            },
            {
                "id": "3.3",
                "title": "Algebraic Method I: The Method of Substitution",
                "prompt": (
                    "Generate an in-depth mathematical section on 'The Method of Substitution' for Unit 3.\n"
                    "Include:\n"
                    "1. Rationale: Why algebraic methods supersede graphical approximations for fractional/decimal coordinates.\n"
                    "2. Formal 3-Step Algorithmic Protocol:\n"
                    "   - Step 1: Express one variable in terms of the other from the more convenient equation.\n"
                    "   - Step 2: Substitute into the OTHER equation to obtain a linear equation in a single variable.\n"
                    "   - Step 3: Solve and back-substitute to find the second variable.\n"
                    "3. Handling Singularities in Substitution:\n"
                    "   - True identity without variable (e.g. $18 = 18$) $\\implies$ Infinitely many solutions (Coincident lines).\n"
                    "   - False identity without variable (e.g. $-4 = 0$) $\\implies$ No solution (Parallel lines).\n"
                    "4. Fully worked textbook example: $7x - 15y = 2$ and $x + 2y = 3$ with step-by-step verification."
                ),
                "max_tokens": 750,
            },
            {
                "id": "3.4",
                "title": "Algebraic Method II: The Method of Elimination",
                "prompt": (
                    "Generate an in-depth mathematical section on 'The Method of Elimination' for Unit 3.\n"
                    "Include:\n"
                    "1. Fundamental Concept: Scaling equations by LCM of coefficients to eliminate one variable via addition or subtraction.\n"
                    "2. Formal Step-by-Step Protocol:\n"
                    "   - Step 1: Multiply equations by non-zero constants to equalize coefficients of $x$ or $y$.\n"
                    "   - Step 2: Add (if opposite signs) or subtract (if identical signs) to eliminate the variable.\n"
                    "   - Step 3: Solve the resulting single-variable equation.\n"
                    "   - Step 4: Back-substitute to find the eliminated variable.\n"
                    "3. Identifying Inconsistency & Dependency in Elimination:\n"
                    "   - $0 = 0 \\implies$ Dependent / Infinitely many solutions.\n"
                    "   - $0 = k$ ($k \\neq 0$) $\\implies$ Inconsistent / No solution.\n"
                    "4. Fully worked textbook example: $9x - 4y = 2000$ and $7x - 3y = 2000$ (Income-expenditure problem)."
                ),
                "max_tokens": 750,
            },
            {
                "id": "3.5",
                "title": "Master Formula Repository & Consistency Decision Matrix",
                "prompt": (
                    "Create a comprehensive 'Master Formula Repository & Consistency Decision Matrix' for Unit 3.\n"
                    "Include:\n"
                    "1. Master Decision Matrix: Ratios $\\frac{a_1}{a_2}, \\frac{b_1}{b_2}, \\frac{c_1}{c_2}$ mapped to Graphical Representation, Algebraic Nature, Consistency, and Determinant interpretation.\n"
                    "2. Comparison between Substitution and Elimination methods: Computational efficiency, best use cases.\n"
                    "3. Standard Forms and Sign Conventions (ensuring $c_1, c_2$ are both on LHS or both on RHS).\n"
                    "4. Formula table for standard geometric shapes formed by linear lines and axes (Area of triangle $=\\frac{1}{2} \\times \\text{base} \\times \\text{height}$)."
                ),
                "max_tokens": 750,
            },
            {
                "id": "3.6",
                "title": "Step-by-Step Algorithmic Problem Solving Procedures",
                "prompt": (
                    "Provide detailed, structured algorithms for Unit 3:\n"
                    "1. Algorithm 1: Graphical Solution of a Linear Pair (Finding coordinate tables, plotting, finding vertex intersection).\n"
                    "2. Algorithm 2: Determining Consistency without Drawing Graphs using Ratio Tests.\n"
                    "3. Algorithm 3: Solving Fractional / Decimal Linear Systems (Clearing denominators via LCM, multiplying decimals by powers of 10).\n"
                    "4. Algorithm 4: Finding the Value of an Unknown Parameter (e.g. $k$) for Unique, Infinite, or No Solution conditions.\n"
                    "5. Algorithm 5: Finding Vertices and Area of the Triangle formed by two lines and the $x$-axis or $y$-axis."
                ),
                "max_tokens": 750,
            },
            {
                "id": "3.7",
                "title": "Foundational & Concept-Building Worked Examples",
                "prompt": (
                    "Generate fully worked foundational examples with complete algebraic steps for Unit 3:\n"
                    "1. Example 1: Check graphically whether $x + 3y = 6$ and $2x - 3y = 12$ is consistent; find the solution.\n"
                    "2. Example 2: Solve by Substitution: $\\sqrt{2}x + \\sqrt{3}y = 0$ and $\\sqrt{3}x - \\sqrt{8}y = 0$.\n"
                    "3. Example 3: Solve by Elimination: $2x + 3y = 11$ and $2x - 4y = -24$; hence find the value of $m$ for which $y = mx + 3$.\n"
                    "4. Example 4: Solve by Elimination: $\\frac{x}{2} + \\frac{2y}{3} = -1$ and $x - \\frac{y}{3} = 3$.\n"
                    "5. Example 5: Find the value of $k$ for which the pair $kx + 3y - (k-3) = 0$ and $12x + ky - k = 0$ has infinitely many solutions."
                ),
                "max_tokens": 750,
            },
            {
                "id": "3.8",
                "title": "Word Problems & Real-World Mathematical Modeling (HOTS)",
                "prompt": (
                    "Generate comprehensive, structured solutions for the 5 classic types of word problems in Unit 3:\n"
                    "1. Category 1 (Two-Digit Number Problem): Sum of a two-digit number and its reversal is 66; digits differ by 2. Find the number.\n"
                    "2. Category 2 (Age Problem): Five years hence, Jacob's age will be 3 times his son; 5 years ago, Jacob was 7 times his son. Find present ages.\n"
                    "3. Category 3 (Fraction Problem): A fraction becomes $9/11$ if 2 is added to numerator and denominator; becomes $5/6$ if 3 is added to both. Find the fraction.\n"
                    "4. Category 4 (Fixed & Variable Charges): Taxi charges: 10 km costs Rs 105, 15 km costs Rs 155. Find fixed charge and rate per km; calculate cost for 25 km.\n"
                    "5. Category 5 (Currency Denomination): Meena withdraws Rs 2000, receives 25 notes in total of Rs 50 and Rs 100. Find the number of each note."
                ),
                "max_tokens": 750,
            },
            {
                "id": "3.9",
                "title": "Common Misconceptions, Degenerate Cases & Exam Traps",
                "prompt": (
                    "Detail the top common misconceptions, algebraic pitfalls, and exam traps for Unit 3:\n"
                    "1. Trap 1: Inconsistent constant placement ($c_1$ on LHS while $c_2$ on RHS), causing flipped signs in ratio tests $\\frac{c_1}{c_2}$.\n"
                    "2. Trap 2: Sign errors during subtraction in the Elimination method (failing to distribute minus sign across all terms).\n"
                    "3. Trap 3: Two-digit number formulation: Writing the number as $xy$ instead of $10x + y$ and reversed as $10y + x$.\n"
                    "4. Trap 4: Forgetting the dual case when $|x - y| = 2$ in digit difference problems ($x - y = 2$ or $y - x = 2$).\n"
                    "5. Trap 5: Identifying the wrong triangle in graphical shading problems (e.g. formed with $x$-axis vs $y$-axis).\n"
                    "Provide explicit 'Wrong Step' vs 'Correct Step' tables."
                ),
                "max_tokens": 750,
            },
            {
                "id": "3.10",
                "title": "NCERT Exercise Walkthrough, Summary Checklist & Practice Drill",
                "prompt": (
                    "Provide the concluding review module for Unit 3: Pair of Linear Equations:\n"
                    "1. Comprehensive Breakdown and Mapping of NCERT Exercises 3.1, 3.2, and 3.3.\n"
                    "2. Rapid-Fire Revision Checklist (10 bullet points for rapid board exam revision).\n"
                    "3. Self-Assessment Practice Drill:\n"
                    "   - 4 Multiple Choice Questions (ratio conditions, solution counts, geometric properties)\n"
                    "   - 2 Short Answer Questions (algebraic solution)\n"
                    "   - 2 Long Answer Questions (HOTS word problem, 5 marks each)\n"
                    "4. Complete Answer Key and Step-by-Step Solutions for all drill questions."
                ),
                "max_tokens": 750,
            },
        ],
    },
}


def generate_unit_notes(
    unit_num: int,
    provider: LlamaCppProvider,
    output_dir: Path,
) -> Path:
    unit_info = UNIT_DEFINITIONS[unit_num]
    title = unit_info["title"]
    output_path = output_dir / unit_info["output_filename"]
    print(f"\n{'='*70}\nStarting Generation for {title}\nOutput: {output_path}\n{'='*70}")

    sections_content = []
    total_words = 0
    start_unit_time = time.perf_counter()

    # Read extracted textbook text if available for grounding context
    text_path = unit_info["text_file"]
    book_excerpt = ""
    if text_path.exists():
        raw_text = text_path.read_text(encoding="utf-8")
        book_excerpt = raw_text[:3000]  # noqa: F841 - kept as a grounding seed for future prompts

    for idx, sec in enumerate(unit_info["sections"], 1):
        sec_id = sec["id"]
        sec_title = sec["title"]
        sec_prompt = sec["prompt"]
        max_tokens = sec.get("max_tokens", 750)

        print(f"\n[{idx}/10] Generating Section {sec_id}: {sec_title}...")
        sec_start = time.perf_counter()

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Unit: {title}\n"
                    f"Section {sec_id}: {sec_title}\n\n"
                    f"Task Instructions:\n{sec_prompt}\n\n"
                    f"Grounding Note: Strictly align with NCERT Class 10 Mathematics standard and curriculum.\n"
                    f"Important: Conclude all points cleanly without truncation. Do not output conversational filler."
                ),
            },
        ]

        try:
            content = provider.complete(
                messages,
                max_tokens=max_tokens,
                temperature=0.2,
            )
        except Exception as e:
            print(f"Error during LLM completion: {e}, retrying with shorter tokens...")
            content = provider.complete(
                messages,
                max_tokens=500,
                temperature=0.2,
            )

        sec_duration = time.perf_counter() - sec_start
        word_count = len(content.split())
        total_words += word_count

        print(f"    Done in {sec_duration:.1f}s | {word_count} words")
        sections_content.append(f"\n\n---\n\n## Section {sec_id}: {sec_title}\n\n{content.strip()}")

    unit_duration = time.perf_counter() - start_unit_time
    est_pages = round(total_words / 380, 1)

    header = (
        f"# {title}\n\n"
        f"**Course:** NCERT / CBSE Class 10 Mathematics  \n"
        f"**Textbook Source:** `{unit_info['chapter_code']}.pdf`  \n"
        f"**Engine:** Local On-Device LLM (`{provider.info.model}`)  \n"
        f"**Total Word Count:** ~{total_words:,} words  \n"
        f"**Estimated Document Length:** ~{est_pages} pages (Standard academic print @ ~380 words/page)  \n"
        f"**Generation Latency:** {unit_duration:.1f} seconds  \n\n"
        f"> **Document Purpose:** This document provides a comprehensive, rigorous, and concise 10-page "
        f"master study guide for {title}. It contains exhaustive theoretical proofs, complete formula tables, "
        f"step-by-step algorithms, fully worked foundational and HOTS examples, common error analyses, and "
        f"self-assessment practice drills with complete answer keys.\n"
    )

    full_document = header + "".join(sections_content) + "\n"
    output_path.write_text(full_document, encoding="utf-8")

    print(f"\n>>> Successfully wrote {output_path}")
    print(f">>> Total Words: {total_words} (~{est_pages} pages) in {unit_duration:.1f}s")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate 10-page NCERT study notes using local LLM")
    parser.add_argument("--unit", type=int, choices=[1, 2, 3], help="Specific unit to generate (1, 2, or 3)")
    parser.add_argument("--model", type=str, help="Path to specific GGUF model")
    parser.add_argument("--threads", type=int, default=6, help="CPU threads to use")
    parser.add_argument("--ctx", type=int, default=4096, help="Context window size")
    args = parser.parse_args()

    model_path = Path(args.model).resolve() if args.model else get_default_model_path()
    print(f"Initializing local LLM from {model_path} with {args.threads} threads...")

    settings = LlmSettings(
        model_path=str(model_path),
        n_ctx=args.ctx,
        n_threads=args.threads,
    )
    provider = LlamaCppProvider(settings)

    if not provider.available:
        print(f"Error: Model provider not available for {model_path}")
        sys.exit(1)

    NOTES_DIR.mkdir(parents=True, exist_ok=True)

    units_to_run = [args.unit] if args.unit else [1, 2, 3]

    grand_start = time.perf_counter()
    generated_files = []

    for u in units_to_run:
        out_file = generate_unit_notes(u, provider, NOTES_DIR)
        generated_files.append(out_file)

    grand_total_time = time.perf_counter() - grand_start
    print(f"\n{'='*70}\nAll requested units generated in {grand_total_time:.1f}s!\nFiles:")
    for f in generated_files:
        print(f"  - {f}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()

