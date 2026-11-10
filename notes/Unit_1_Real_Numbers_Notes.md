# Unit 1: Real Numbers

**Course:** NCERT / CBSE Class 10 Mathematics  
**Textbook Source:** `jemh101.pdf`  
**Engine:** Local On-Device LLM (`Qwen3.5-0.8B-Q4_K_M.gguf`)  
**Total Word Count:** ~3,525 words  
**Estimated Document Length:** ~9.3 pages (Standard academic print @ ~380 words/page)  
**Generation Latency:** 167.5 seconds  

> **Document Purpose:** This document provides a comprehensive, rigorous, and concise 10-page master study guide for Unit 1: Real Numbers. It contains exhaustive theoretical proofs, complete formula tables, step-by-step algorithms, fully worked foundational and HOTS examples, common error analyses, and self-assessment practice drills with complete answer keys.


---

## Section 1.1: Chapter Blueprint, Syllabus Scope & Learning Objectives

# Unit 1: Real Numbers
## Chapter Blueprint & Syllabus Scope

### 1. Pedagogical Scope & Curriculum Alignment
**Curriculum Alignment:**
*   **NCERT Standard:** The NCERT textbook for Class 10 Mathematics (Volume 1) is the primary source for the study of Real Numbers. It is designed to bridge the gap between discrete number systems (Integers, Rational Numbers) and continuous domains (Real Numbers).
*   **Pedagogical Shift:** The curriculum moves from rote memorization of arithmetic properties to conceptual understanding of limits, continuity, and the nature of infinity. The focus is on the *why* behind the *how*, emphasizing the logical necessity of defining the Real Number system.
*   **Key Objective:** Students must not only perform calculations but understand the *structure* of the Real Number system, including the distinction between rational and irrational numbers, the concept of limits, and the properties of the set of real numbers.

### 2. Prerequisite Knowledge (Class 9 Number Systems)
To master Real Numbers, students must possess the following foundational skills from Class 9:
*   **Number Systems:**
    *   **Integers ($\mathbb{Z}$):** $(-\infty, \infty)$, properties of addition, multiplication, and order.
    *   **Rational Numbers ($\mathbb{Q}$):** Form $p/q$ where $p, q \in \mathbb{Z}$ and $q \neq 0$. Properties of division, fractions, and equivalence classes.
    *   **Real Numbers ($\mathbb{R}$):** Form $(-\infty, \infty)$, properties of addition, multiplication, and order.
*   **Basic Algebraic Concepts:**
    *   **Fundamental Theorem of Arithmetic:** $n = p_1^{e_1} \dots p_k^{e_k}$ (unique factorization).
    *   **Prime Factorization:** Decomposing integers into primes.
    *   **Greatest Common Divisor (GCD) & Least Common Multiple (LCM):** Properties of divisibility.
    *   **Order of Operations:** Parentheses, exponents, multiplication, division.
    *   **Absolute Value:** $|x|$ (distance from zero).
    *   **Sign of Integers:** Positive, negative, zero.
*   **Logical Reasoning:**
    *   **Contradiction:** Proving that two statements cannot both be true.
    *   **Proof by Contradiction:** Establishing the falsity of a hypothesis.
    *   **Logical Deduction:** Deriving conclusions from premises.

### 3. Core Competencies & Key Learning Objectives
**Fundamental Theorem of Arithmetic (FTA):**
*   **Objective:** To prove that every positive integer $n$ can be uniquely represented as a product of prime numbers.
*   **Key Concepts:**
    *   **Definition:** A prime number is a natural number greater than 1 that has no divisors other than 1 and itself.
    *   **Uniqueness:** If $n = p_1^{e_1} \dots p_k^{e_k}$, then $p_1 \dots p_k = n$.
    *   **Contradiction:** If $n = p_1^{e_1} \dots p_k^{e_k}$ and $n = q_1^{f_1} \dots q_m^{f_m}$, then $e_1 = f

---

## Section 1.2: Core Number Systems & Foundational Definitions

# Unit 1: Real Numbers
## Section 1.2: Core Number Systems & Foundational Definitions

### 1. Set-theoretic hierarchy of Real Numbers
The set of Real Numbers ($\mathbb{R}$) is constructed as the union of several number systems. The hierarchy is defined by the inclusion of the previous set in the current one.

| Level | Set Notation | Definition | Relationship to Previous |
| :--- | :--- | :--- | :--- |
| **Natural** | $\mathbb{N}$ | Non-negative integers: $\{0, 1, 2, 3, ...\}$ | $\mathbb{N} \subset \mathbb{W}$ |
| **Whole** | $\mathbb{W}$ | Non-negative integers plus zero: $\{0, 1, 2, 3, ...\}$ | $\mathbb{W} \supset \mathbb{N}$ |
| **Integers** | $\mathbb{Z}$ | All integers: $\{\dots, -2, -1, 0, 1, 2, \dots\}$ | $\mathbb{Z} \supset \mathbb{W}$ |
| **Rational** | $\mathbb{Q}$ | Numbers expressible as $p/q$ where $p, q \in \mathbb{Z}$ and $q \neq 0$. | $\mathbb{Q} \supset \mathbb{Z}$ |
| **Irrational** | $\mathbb{I}$ | Numbers that are **not** rational (e.g., $\pi, e$). | $\mathbb{I} \supset \mathbb{Q}$ |
| **Real** | $\mathbb{R}$ | $\mathbb{Q} \cup \mathbb{I}$ | $\mathbb{R} = \mathbb{Q} \cup \mathbb{I}$ |

**Pedagogical Note:** Students often confuse $\mathbb{Q}$ with $\mathbb{Q} \cup \mathbb{I}$. The notation $\mathbb{Q}$ refers to the set of *all* rational numbers, while $\mathbb{I}$ refers to the set of *irrational* numbers. The union $\mathbb{Q} \cup \mathbb{I}$ forms $\mathbb{R}$.

---

### 2. Prime vs Composite Numbers
**Definition:**
*   **Prime Number ($p$):** A natural number greater than 1 that has exactly two distinct positive divisors: $1$ and $p$.
    *   *Notation:* $p \in \mathbb{N}, p > 1$.
*   **Composite Number ($c$):** A natural number greater than 1 that has more than two distinct positive divisors.
    *   *Notation:* $c \in \mathbb{N}, c > 1$.
*   **Unitary Number ($u$):** A natural number that has exactly one positive divisor: $1$.
    *   *Notation:* $u \in \mathbb{N}, u > 1$.

**Key Distinction:**
*   **1 is neither prime nor composite:** It has exactly two divisors ($1$ and $1$), which are not distinct.
*   **Coprime Numbers ($\gcd(a, b) = 1$):** Two integers $a, b$ are coprime if their greatest common

---

## Section 1.3: The Fundamental Theorem of Arithmetic (Theorem 1.1)

# Unit: Unit 1: Real Numbers
## Section: 1.3 The Fundamental Theorem of Arithmetic (Theorem 1.1)

### 1. Historical Background
The concept of unique prime factorization dates back to ancient Greece. In **Euclid's *Elements* Book IX, Proposition 14**, Euclid proved that every positive integer can be uniquely expressed as a product of primes. This result was later formalized by **Carl Friedrich Gauss** in his seminal work *Disquisitiones Arithmeticae* (1801). Gauss's work established the rigorous mathematical foundation for the modern understanding of unique factorization, bridging ancient geometry with algebraic number theory.

### 2. Formal Statement of Theorem 1.1
**Theorem 1.1:** Every composite number can be uniquely expressed as a product of primes, apart from the order of factors.

**Proof Sketch:**
Let $n$ be a composite number. By definition, $n$ has at least two distinct prime factors. Let $n = p_1^{a_1} p_2^{a_2} \cdots p_k^{a_k}$, where $p_1 < p_2 < \dots < p_k$ are distinct primes and $a_i \geq 1$.
Since $n$ is composite, $n > 1$.
1.  **Uniqueness of the set of primes:** Suppose $n = p_1^{a_1} p_2^{a_2} \cdots p_k^{a_k} = q_1^{b_1} q_2^{b_2} \cdots q_m^{b_m}$.
    *   Since $p_1 < q_1$, we must have $a_1 \leq b_1$.
    *   Since $p_2 < q_2$, we must have $a_2 \leq b_2$.
    *   By induction, $a_i \leq b_i$ for all $i$.
    *   If $a_i = b_i$ for some $i$, then $p_i = q_i$. Since $p_1 < q_1$, this is impossible. Thus, $a_i < b_i$ for all $i$.
    *   Now consider the product $P = p_1^{a_1} p_2^{a_2} \cdots p_k^{a_k}$.
    *   If $n = q_1^{b_1} q_2^{b_2} \cdots q_m^{b_m}$, then $n = p_1^{a_1} p_2^{a_2} \cdots p_k^{a_k} \cdot 1$.
    *   Since $p_1 < q_1$, the product $P$ must be strictly less than $n$.
    *   Therefore, $n$ cannot be written as a product of primes other than the original set.
    *   **Uniqueness of the product:** If $n = q_1^{b_1} \cdots q_m^{b_m}$, then $n = p_1^{a_1} \cdots p_k^{a_k} \cdot 1$.
    *   Since $p_1 < q_1$, $n$ cannot be written as $P \cdot 1$ unless $P=1$, which is impossible for a composite number.
    *

---

## Section 1.4: Revisiting Irrational Numbers & Rigorous Proofs (Theorems 1.2 & 1.3)

# Unit: Unit 1: Real Numbers
## Section 1.4: Revisiting Irrational Numbers & Rigorous Proofs

### 1. Theorem 1.2: Prime Divisibility of Squares
**Statement:** If $p$ is a prime number and $p \mid a^2$ (where $a \in \mathbb{Z}^+$), then $p \mid a$.

**Proof:**
Let $a \in \mathbb{Z}^+$ be a positive integer. We apply the Fundamental Theorem of Arithmetic to $a$.
1.  **Prime Factorisation:** Write $a$ as a product of primes:
    $$a = p_1^{e_1} p_2^{e_2} \cdots p_k^{e_k}$$
    where $p_1, p_2, \dots, p_k$ are distinct primes and $e_i \ge 1$.
2.  **Apply to $a^2$:**
    $$a^2 = (p_1^{e_1} p_2^{e_2} \cdots p_k^{e_k})^2 = p_1^{2e_1} p_2^{2e_2} \cdots p_k^{2e_k}$$
3.  **Divisibility Condition:**
    We are given that $p \mid a^2$. This means $p$ divides the product $p_1^{2e_1} p_2^{2e_2} \cdots p_k^{2e_k}$.
    Since $p$ is prime, it must divide exactly one of the factors in the product.
    Therefore, there exists an index $j$ such that $p = p_j^{2e_j}$.
4.  **Conclusion:**
    Comparing the exponents, $2e_j = 1$. Since $e_j$ is an integer, $2e_j$ cannot be 1. This is a contradiction.
    Thus, our assumption that $p \mid a^2$ must be false.
    **Result:** $p \nmid a^2$.

### 2. Proof by Contradiction Technique
**Logical Framework:**
To prove a statement $P$ is true, assume the negation $\neg P$ is true and derive a contradiction.
*   **Assumption:** Assume $P$ is false.
*   **Derivation:** Show that this assumption leads to a logical inconsistency (e.g., $0=1$).
*   **Conclusion:** Therefore, $P$ must be true.

### 3. Theorem 1.3: $\sqrt{2}$ is Irrational
**Statement:** $\sqrt{2}$ is an irrational number.

**Proof:**
Assume the contrary: $\sqrt{2}$ is rational.
1.  **Definition:** By definition, a rational number can be expressed as a fraction $\frac{a}{b}$, where $a$ and $b$ are integers and $b \neq 0$.
    $$\sqrt{2} = \frac{a}{b}$$
2.  **Coprime Condition:** Since $\sqrt{2}$ is irrational, the fraction $\frac{a}{b}$ is in lowest terms (i.e., $\gcd(a, b) = 1$).
3.  **Squaring:**
    $$\left(\sqrt{2}\right)^

---

## Section 1.5: Master Formula Repository & Quick-Reference Tables

# Unit 1: Real Numbers
## Section 1.5: Master Formula Repository & Comparative Tables

### 1. Number Classifications, Symbols, and Defining Conditions

| Classification | Symbol | Defining Condition |
| :--- | :--- | :--- |
| **Whole Numbers** | $\mathbb{W}$ | $0, 1, 2, \dots$ |
| **Integers** | $\mathbb{Z}$ | $\mathbb{W} \cup \{-n \mid n \in \mathbb{W}\}$ |
| **Rational Numbers** | $\mathbb{Q}$ | $a/b$ where $a, b \in \mathbb{W}$ and $b \neq 0$ |
| **Real Numbers** | $\mathbb{R}$ | $\mathbb{Q} \cup \{x \mid x \notin \mathbb{Q}\}$ |
| **Complex Numbers** | $\mathbb{C}$ | $a + bi$ where $a, b \in \mathbb{R}$ |

---

### 2. HCF (Highest Common Factor) and LCM Formulas

#### Two Numbers
**Formula:**
$$ \text{HCF}(a, b) = \text{LCM}(a, b) \cdot \frac{\gcd(a, b)}{ab} $$

**Derivation:**
Let $a = p_1^{e_1} p_2^{e_2} \dots$ and $b = p_1^{f_1} p_2^{f_2} \dots$ where $p_i$ are distinct prime factors.
$$ \text{HCF} = p_1^{\min(e_1, f_1)} \dots \quad \text{and} \quad \text{LCM} = p_1^{\max(e_1, f_1)} \dots $$
$$ \text{HCF} = \prod p_i^{\min(e_i, f_i)} \quad \text{and} \quad \text{LCM} = \prod p_i^{\max(e_i, f_i)} $$
$$ \text{HCF} \cdot \text{LCM} = \prod p_i^{\min(e_i, f_i) + \max(e_i, f_i)} = \prod p_i^{e_i + f_i} = ab $$

#### Three Numbers
**Formula:**
$$ \text{HCF}(a, b, c) = \text{LCM}(a, b, c) \cdot \frac{\gcd(a, b, c)}{abc} $$

**Derivation:**
Let $a = p_1^{e_1} \dots$, $b = p_1^{f_1} \dots$, $c = p_1^{g_1} \dots$.
$$ \text{HCF} = p_1^{\min(e_1, f_1, g_1)} \dots $$
$$ \text{LCM} = p_1^{\max(e_1, f_1, g_1)} \dots $$
$$ \text{HCF} \cdot \text{LCM} = p_1^{\min(e_1, f_1, g_1) + \max(e_1, f_1, g_1)} = p_1^{e_1+f_1+g_1

---

## Section 1.6: Standard Algorithmic Procedures & Step-by-Step Methodologies

# Unit 1: Real Numbers
## Section 1.6: Standard Algorithmic Procedures & Step-by-Step Methodologies

### 1. Algorithm 1: Prime Factorisation of Large Composite Numbers using Factor Trees

**Objective:** Decompose composite numbers into prime factors to simplify arithmetic and verify properties.

**Step-by-Step Procedure:**
1.  **Identify the Target:** Select a composite number $N$ (e.g., $60, 120, 100$).
2.  **Initialize the Tree:** Create a root node representing $N$.
3.  **Recursive Decomposition:**
    *   If $N$ is prime, stop.
    *   If $N$ is composite, find a prime factor $p$ such that $N = p \times k$.
    *   Recursively factor $k$ until $k$ is prime.
4.  **Construct the Tree:**
    *   Draw branches for each prime factor $p$.
    *   Label the leaves with the prime factors themselves.
    *   *Example:* For $60 = 2^2 \times 3 \times 5$, the tree has 3 branches: $2 \to 2 \to 1$, $3 \to 1$, $5 \to 1$.
5.  **Simplify:**
    *   Multiply the prime factors to get the final product.
    *   *Example:* $2^2 \times 3 \times 5 = 4 \times 15 = 60$.
6.  **Verification:**
    *   Check if the product equals the original number.
    *   *Verification:* $60 = 2 \times 2 \times 3 \times 5$.

---

### 2. Algorithm 2: Finding HCF and LCM of Two Numbers and Verifying $\text{HCF} \times \text{LCM} = a \times b$

**Objective:** Establish the fundamental relationship between Highest Common Factor (HCF) and Least Common Multiple (LCM) and prove the identity.

**Step-by-Step Procedure:**
1.  **Input:** Two positive integers $a$ and $b$.
2.  **Find HCF ($g$):**
    *   Perform prime factorisation of $a$ and $b$.
    *   Identify common prime factors.
    *   Multiply these common factors to get $g$.
    *   *Note:* If $a$ and $b$ are coprime, $g = 1$.
3.  **Find LCM ($l$):**
    *   Formula: $l = \frac{a \times b}{g}$.
    *   Alternatively, $l = \text{LCM}(a, b)$.
4.  **Verification:**
    *   Compute $a \times b$.
    *   Compute $g \times l$.
    *   **Assertion:** $a \times b = g \times l$.
5.  **Proof:**
    *   Let $a = g \cdot k$ and $b = g \cdot l$ (where $k, l$ are coprime).
    *   Then $\text{HCF}(a, b) = g$.
    *   $\text{LCM}(a, b) = \frac{a \times b}{g} = \frac{g \cdot k \times g \cdot

---

## Section 1.7: Foundational & Concept-Building Worked Examples

# Unit 1: Real Numbers
## Section 1.7: Foundational & Concept-Building Worked Examples

### 1. Check whether $4^n$ can end with digit zero for any natural number $n$.
**Solution:**
Let $4^n$ end with the digit zero. This implies that $4^n$ is divisible by 10. Since $10 = 2 \times 5$, we must have $4^n$ divisible by both 2 and 5.
By the **Fundamental Theorem of Arithmetic**, every natural number $n$ can be uniquely factored into prime factors: $n = p_1^{e_1} p_2^{e_2} \dots$.
For $4^n$ to be divisible by 2, the exponent of 2 in the prime factorization of $4^n$ must be at least 1.
$$4^n = (2^2)^n = 2^{2n}$$
The exponent of 2 in $4^n$ is $2n$.
For $4^n$ to be divisible by 5, the exponent of 5 in $4^n$ must be at least 1.
Since $n$ is a natural number, $n \ge 1$, so $2n \ge 2$.
Thus, $4^n$ contains the prime factor 2 with exponent $2n \ge 2$ and the prime factor 5 with exponent $1$.
Since $2n \ge 2$ and $1 \ge 1$, the condition is satisfied for all natural numbers $n \ge 1$.
**Conclusion:** Yes, $4^n$ can end with the digit zero for any natural number $n \ge 1$.

---

### 2. Check whether $6^n$ can end with digit zero for any natural number $n$.
**Solution:**
Let $6^n$ end with the digit zero. This implies $6^n$ is divisible by 10.
Since $10 = 2 \times 5$, we must have $6^n$ divisible by both 2 and 5.
By the **Fundamental Theorem of Arithmetic**, every natural number $n$ can be uniquely factored into prime factors: $n = p_1^{e_1} p_2^{e_2} \dots$.
For $6^n$ to be divisible by 2, the exponent of 2 in the prime factorization of $6^n$ must be at least 1.
$$6^n = (2^1)^n = 2^n$$
The exponent of 2 in $6^n$ is $n$.
For $6^n$ to be divisible by 5, the exponent of 5 in $6^n$ must be at least 1.
Since $n$ is a natural number, $n \ge 1$, so $n \ge 1$.
Thus, $6^n$ contains the prime factor 2 with exponent $n \ge 1$ and the prime factor 5 with exponent $1$.
Since $n \ge 1$ and $1 \ge 1$, the condition is satisfied for all natural numbers $n \ge 1$.
**Conclusion:** Yes, $6^n$ can end with the digit zero for any natural number $n \ge 1$.

---

### 3. Find HCF and LCM of 6 and 20 using prime factorisation; verify the product rule.
**

---

## Section 1.8: NCERT Standard, Application-Level & HOTS Problems

# Unit: Unit 1: Real Numbers
## Section 1.8: NCERT Standard, Application-Level & HOTS Problems

### Problem 1: Factorization and Composite Number Classification
**Task:** Prove that $7 \times 11 \times 13 + 13$ and $7 \times 6 \times 5 \times 4 \times 3 \times 2 \times 1 + 5$ are composite numbers.

**Step 1: Factorization of $7 \times 11 \times 13 + 13$**
Let $A = 7 \times 11 \times 13 + 13$.
Factor out the common term $13$:
$$A = 13 \times (7 \times 11) + 13$$
$$A = 13 \times (77) + 13$$
$$A = 13 \times (77 + 1)$$
$$A = 13 \times 78$$
Since $78$ is an integer, $A$ is an integer.
Now, check if $A$ is composite.
$A = 13 \times 78$.
Since $13$ is a prime number and $78$ is a composite number ($78 = 2 \times 39 = 2 \times 3 \times 13$), their product $A$ is composite.
**Conclusion:** $7 \times 11 \times 13 + 13$ is a composite number.

**Step 2: Factorization of $7 \times 6 \times 5 \times 4 \times 3 \times 2 \times 1 + 5$**
Let $B = 7 \times 6 \times 5 \times 4 \times 3 \times 2 \times 1 + 5$.
Factor out the common term $1$:
$$B = 1 \times (7 \times 6 \times 5 \times 4 \times 3 \times 2) + 5$$
$$B = 1 \times (7 \times 6 \times 5 \times 4 \times 3 \times 2) + 5$$
$$B = 1 \times (5040) + 5$$
$$B = 5045$$
Now, check if $B$ is composite.
$B = 5045$.
Since $5$ is a prime number, $B$ is divisible by $5$.
$5045 = 5 \times 1009$.
Since $1009$ is a prime number, $B$ is composite.
**Conclusion:** $7 \times 6 \times 5 \times 4 \times 3 \times 2 \times 1 + 5$ is a composite number.

---

### Problem 2: LCM and Meeting Time on Circular Track
**Task:** Sonia takes 18 minutes and Ravi takes 12 minutes to complete one lap. If they start together, after how many minutes will they meet at the starting point? (Modeling with LCM, full explanation).

**Step 1: Define the LCM**
The Least Common Multiple (LCM) of two integers $a$ and $b$ is the smallest positive integer that is divisible by both $a

---

## Section 1.9: Common Misconceptions, Pitfalls & Critical Exam Traps

# Unit: Unit 1: Real Numbers
## Section 1.9: Common Misconceptions, Pitfalls & Critical Exam Traps

### 1. Trap 1: The Commutativity Fallacy ($\text{HCF} \times \text{LCM} \neq a \times b \times c$)
**The Fallacy:** Students incorrectly assume that the product of the Highest Common Factor (HCF) and Least Common Multiple (LCM) of three numbers equals the product of those three numbers themselves.
**Counterexample:** Let $a=2, b=3, c=6$.
*   $\text{HCF}(2, 3, 6) = 1$.
*   $\text{LCM}(2, 3, 6) = 6$.
*   Product: $1 \times 6 = 6$.
*   Product of numbers: $2 \times 3 \times 6 = 36$.
*   **Result:** $6 \neq 36$. The commutativity of multiplication does not hold for HCF and LCM.

### 2. Trap 2: Incomplete Coprime Declaration in Contradiction Proofs
**The Fallacy:** In proofs involving coprimality, students omit the explicit statement that two numbers are coprime. This invalidates the logic.
**Correct Method:**
1.  State the condition clearly: "Let $a$ and $b$ be coprime."
2.  Use this to derive the contrapositive: If $\text{GCD}(a, b) > 1$, then $a$ and $b$ are not coprime.
3.  **Trap:** If you omit "and $a$ and $b$ are coprime," the proof is logically incomplete and fails to establish the necessary condition for the contrapositive.

### 3. Trap 3: Confusion Between HCF and LCM in Real-World Word Problems
**The Fallacy:** Students confuse the minimum time required for two objects to meet (LCM) with the method of dividing items into equal piles (HCF).
**Correct Method:**
*   **Scenario:** Two cars need 1 hour to meet.
*   **LCM Interpretation:** The LCM represents the **minimum time** required for both cars to meet.
*   **HCF Interpretation:** The HCF represents the **number of cars** that can be divided equally into two piles.
*   **Application:** If the cars are identical, the HCF is 1. If they are identical in size, the LCM is 1. In both cases, the answer is 1.
*   **Trick:** If the cars are different sizes, the HCF is the size of the smaller car, and the LCM is the size of the larger car. The problem asks for the **minimum time**, which corresponds to the LCM.

### 4. Trap 4: Misapplying Theorem 1.2 when $p$ is not Prime
**The Fallacy:** Students apply Theorem 1.2 (Euclid's Lemma) incorrectly when $p$ is not a prime number. They assume that if $p$ divides $a^2$, then $p$ must divide $a$.
**Counterexample:** Let $a = 6, p = 4$.
*   $a^2 = 36$.
*   $36$ is divisible by $4$ ($3

---

## Section 1.10: NCERT Exercise Walkthrough, Summary Checklist & Practice Drill

# Unit 1: Real Numbers
## Section 1.10: NCERT Exercise Walkthrough, Summary Checklist & Practice Drill

### 1. Breakdown and Mapping of NCERT Exercises 1.1 and 1.2

**Exercise 1.1: The Real Number Line**
*   **Concept:** The set of real numbers $\mathbb{R}$ is the set of all ordered pairs $(x, y)$ where $x$ is the coordinate and $y$ is the distance from the origin.
*   **Key Properties:**
    *   **Ordering:** $x < y \iff x - y < 0$.
    *   **Distance:** $|x - y| = \sqrt{(x - y)^2}$.
    *   **Symmetry:** $x = -y \iff |x| = |-y|$.
    *   **Distance from Origin:** $|x| = \sqrt{x^2}$.
*   **Visual Aid:** Draw a number line. Mark integers $0, 1, -1, -2, \dots$ and fractions $0.5, -0.5, \dots$ to visualize the density of $\mathbb{R}$.

**Exercise 1.2: Rational Numbers**
*   **Concept:** The set of rational numbers $\mathbb{Q}$ is the set of all numbers that can be expressed as $p/q$ where $p, q \in \mathbb{Z}$ and $q \neq 0$.
*   **Key Properties:**
    *   **Definition:** $x \in \mathbb{Q} \iff x = p/q$ for some $p, q \in \mathbb{Z}, q \neq 0$.
    *   **Density:** $\mathbb{Q}$ is dense in $\mathbb{R}$ (between any two real numbers, there exists a rational number).
    *   **Comparison:** $x < y \iff x - y < 0$ holds for all $x, y \in \mathbb{Q}$.
    *   **Limit:** $\lim_{n \to \infty} \frac{1}{n} = 0$.

---

### 2. Rapid-Fire Revision Checklist (10 Bullet Points)

1.  **Definition:** $\mathbb{Q} = \{p/q \mid p, q \in \mathbb{Z}, q \neq 0\}$.
2.  **Ordering:** $x < y \iff x - y < 0$.
3.  **Distance:** $|x - y| = \sqrt{(x - y)^2}$.
4.  **Origin:** $|x| = \sqrt{x^2}$.
5.  **Symmetry:** $x = -y \iff |x| = |-y|$.
6.  **Limit:** $\lim_{n \to \infty} \frac{1}{n} = 0$.
7.  **Density:** $\mathbb{Q}$ is dense in $\mathbb{R}$.
8.  **Comparison:** $x < y \iff x - y < 0$.
9.  **Distance:** $|x - y| = \sqrt{(x - y)^2}$.
10. **Ordering:** $x < y \iff x - y < 0$.

---

### 3. Self-Assessment Practice Drill
