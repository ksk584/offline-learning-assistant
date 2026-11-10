# Unit 3: Pair of Linear Equations in Two Variables

**Course:** NCERT / CBSE Class 10 Mathematics  
**Textbook Source:** `jemh103.pdf`  
**Engine:** Local On-Device LLM (`Qwen3.5-0.8B-Q4_K_M.gguf`)  
**Total Word Count:** ~3,684 words  
**Estimated Document Length:** ~9.7 pages (Standard academic print @ ~380 words/page)  
**Generation Latency:** 168.6 seconds  

> **Document Purpose:** This document provides a comprehensive, rigorous, and concise 10-page master study guide for Unit 3: Pair of Linear Equations in Two Variables. It contains exhaustive theoretical proofs, complete formula tables, step-by-step algorithms, fully worked foundational and HOTS examples, common error analyses, and self-assessment practice drills with complete answer keys.


---

## Section 3.1: Chapter Blueprint, Syllabus Scope & Real-Life Modeling

# Unit 3: Pair of Linear Equations in Two Variables
## Section 3.1: Chapter Blueprint & Real-Life Modeling

### 1. Pedagogical Scope & Curriculum Alignment
**Curriculum Alignment:**
*   **Grade Level:** Class 10 (NCERT Standard 10).
*   **Core Concept:** Linear Equations in Two Variables ($ax + by + c = 0$).
*   **Key Objective:** Students will learn to model real-world scenarios using systems of linear equations, specifically focusing on the geometric interpretation of solutions.
*   **Pedagogical Goal:** To move students from abstract algebraic manipulation to concrete geometric understanding, emphasizing the relationship between the solution set and the line defined by the equation.

### 2. Definition of a Linear Equation in Two Variables
**Formal Definition:**
A linear equation in two variables $x$ and $y$ is a polynomial equation of degree 1 where the coefficients of $x$ and $y$ are non-zero constants.
*   **General Form:** $ax + by + c = 0$
*   **Parameters:**
    *   $a, b, c \in \mathbb{R}$ (Real numbers).
    *   $a^2 + b^2 \neq 0$ (Ensures the line is not a point or undefined).
*   **Geometric Interpretation:**
    *   The set of all points $(x, y)$ that satisfy the equation lie on a straight line.
    *   **Slope ($m$):** $m = -\frac{b}{a}$ (if $a \neq 0$).
    *   **Intercepts:** $x$-intercept ($x_0$) and $y$-intercept ($y_0$).

### 3. Geometric Meaning of a Solution
**Concept:**
A solution to a system of linear equations is a point $(x_0, y_0)$ in the Cartesian plane.
*   **Condition:** If $(x_0, y_0)$ is a solution, then substituting $x_0$ and $y_0$ into the equation yields $0$.
*   **Linearity:** The solution set forms a straight line.
*   **Contrast:** If the system has no solution (inconsistent equations), the line is parallel to the given line but does not intersect it.

### 4. General Form of a Pair of Linear Equations
**Formulation:**
Two equations representing a system are written in the general form:
$$a_1 x + b_1 y + c_1 = 0$$
$$a_2 x + b_2 y + c_2 = 0$$
*   **Note:** The coefficients $a_1, b_1, c_1$ and $a_2, b_2, c_2$ are real numbers.
*   **System Type:**
    *   **Consistent & Unique:** Two distinct lines intersect at a single point.
    *   **Consistent & Infinite:** Lines are identical (parallel).
    *   **Inconsistent:** Lines are parallel but distinct (no solution).

### 5. Real-World Modeling: Translating Word Problems
**Example 1: Akhila's Giant Wheel**
*   **Problem:** A giant wheel has a circumference of $4\pi$ meters. If it is cut into two equal pieces, each piece has a circumference of $\frac{1

---

## Section 3.2: Graphical Method & The Ratio Consistency Criteria

# Unit 3: Pair of Linear Equations in Two Variables
## Section 3.2: Graphical Method & Ratio Consistency Criteria

### 1. Geometric Behaviour of Two Lines in a Plane

Consider two lines $L_1$ and $L_2$ in the Cartesian plane. Their relationship is determined by the slopes and y-intercepts.

**Case A: Intersecting Lines**
*   **Condition:** $m_1 \neq m_2$ (Slopes are distinct).
*   **Geometric Behavior:** The lines intersect at a single point.
*   **Equation:** $y = m_1x + b_1$ and $y = m_2x + b_2$.
*   **Solution:** Exactly 1 unique solution.

**Case B: Parallel Lines**
*   **Condition:** $m_1 = m_2$ (Slopes are identical).
*   **Geometric Behavior:** The lines are parallel and distinct.
*   **Equation:** $y = m_1x + b_1$ and $y = m_1x + b_2$ ($b_1 \neq b_2$).
*   **Solution:** No solution.

**Case C: Coincident Lines**
*   **Condition:** $m_1 = m_2$ and $b_1 = b_2$.
*   **Geometric Behavior:** The lines are identical and lie on the same line.
*   **Equation:** $y = m_1x + b_1$ and $y = m_1x + b_1$.
*   **Solution:** Infinitely many solutions.

---

### 2. Consistency Criteria

A system of linear equations is consistent if it has at least one solution. It is inconsistent if it has no solution.

| Consistency Type | Condition | Geometric Interpretation | Solution Set |
| :--- | :--- | :--- | :--- |
| **Consistent** | At least one solution exists | Lines intersect or are coincident. | Finite set of solutions |
| **Inconsistent** | No solution exists | Lines are parallel and distinct. | Empty set ($\emptyset$) |
| **Dependent** | Infinitely many solutions | Lines are coincident. | Infinite set of solutions |

---

### 3. Master Coefficient Ratio Comparison Criteria

The consistency of the system is determined by the relationship between the ratios of the coefficients of $x$ and $y$.

#### Case 1: Intersecting Lines
$$ \frac{a_1}{a_2} \neq \frac{b_1}{b_2} $$
*   **Geometric:** Intersecting lines.
*   **Solution:** Exactly 1 unique solution.
*   **Ratio Condition:** $\frac{a_1}{a_2} \neq \frac{b_1}{b_2}$

#### Case 2: Coincident Lines
$$ \frac{a_1}{a_2} = \frac{b_1}{b_2} = \frac{c_1}{c_2} $$
*   **Geometric:** Coincident lines.
*   **Solution:** Infinitely many solutions.
*   **Ratio Condition:** $\frac{a_1}{a_2} = \frac{b_1}{b_2} = \frac{c_1}{c_2}$

#### Case

---

## Section 3.3: Algebraic Method I: The Method of Substitution

# Unit 3: Pair of Linear Equations in Two Variables
## Section 3.3: Algebraic Method I: The Method of Substitution

### 1. Rationale: Why Algebraic Methods Supersede Graphical Approximations
In the context of NCERT Class 10 Mathematics, the transition from graphical approximation to algebraic solution is critical for fractional and decimal coordinates.

*   **Precision and Exactness**: Graphical methods rely on visual estimation, which introduces significant error, especially when coordinates are fractions or decimals. Algebraic methods provide exact solutions derived from symbolic manipulation, ensuring accuracy regardless of the input values.
*   **Efficiency**: Graphical methods require plotting multiple points and drawing a line, a process that is computationally expensive and prone to human error. Algebraic substitution reduces the problem to a single linear equation, allowing for immediate and precise solution.
*   **Curriculum Alignment**: The NCERT curriculum emphasizes algebraic manipulation as the primary tool for solving systems of equations. Mastery of substitution is a prerequisite for understanding the concept of parallel lines (no solution) and coincident lines (infinitely many solutions), which are essential for graphing and solving systems of equations.

---

### 2. Formal 3-Step Algorithmic Protocol

To solve a system of two linear equations using the Method of Substitution, follow this strict protocol:

#### Step 1: Express One Variable in Terms of the Other
Identify the equation with the **more convenient** (simpler) form. Solve it for one variable ($x$ or $y$) and express it in terms of the other variable ($z$ or $w$).
*   *Example*: From $7x - 15y = 2$, solve for $x$:
    $$7x = 15y + 2 \implies x = \frac{15y + 2}{7}$$

#### Step 2: Substitute into the Other Equation
Substitute the expression for the first variable into the second equation. This results in a **linear equation in a single variable**.
*   *Example*: Substitute $x = \frac{15y + 2}{7}$ into $x + 2y = 3$:
    $$\frac{15y + 2}{7} + 2y = 3$$

#### Step 3: Solve and Back-Substitute
Solve the resulting single linear equation for the variable. Once the value is found, **back-substitute** the expression back into the first equation to find the second variable.
*   *Example*: Substitute $y = 1$ into $x = \frac{15(1) + 2}{7}$:
    $$x = \frac{17}{7}$$

---

### 3. Handling Singularities in Substitution

The validity of the substitution method depends on the resulting equation being linear in the single variable.

#### True Identity: Infinitely Many Solutions (Coincident Lines)
*   **Condition**: The substituted equation must be an **identity** (an equation that holds true for all values of the variable).
*   **Example**: If substituting $x = 1$ into $x + 2y = 3$ yields $1 + 2y = 3$, then $2y = 2 \implies y = 1$.
*   **Result**: Since $y = 1$ is a constant, the system represents **Coincident Lines**. There are infinitely many solutions.
*   **Note**: In the

---

## Section 3.4: Algebraic Method II: The Method of Elimination

# Unit 3: Pair of Linear Equations in Two Variables
## Section 3.4: Algebraic Method II: The Method of Elimination

### 1. Fundamental Concept: Scaling Equations by LCM of Coefficients
To eliminate a variable, we must scale the original equations by non-zero constants $k$ such that the coefficients of the eliminated variable become identical.
*   **Rule:** Multiply Equation 1 by $k_1$ and Equation 2 by $k_2$ where $k_1, k_2 \in \mathbb{R}^*$ and $k_1 k_2 \neq 0$.
*   **Result:** The new system is $k_1 E_1 + k_2 E_2 = k_1 k_2 E_1 + k_2 k_2 E_2$.
*   **Logic:** This ensures that the coefficient of the eliminated variable is $k_1 k_2$. If $k_1 k_2 = 0$, the operation is invalid.

### 2. Formal Step-by-Step Protocol
1.  **Multiply:** Multiply Equation 1 by $k_1$ and Equation 2 by $k_2$ to equalize coefficients of $x$ (or $y$).
2.  **Add/Subtract:**
    *   **Opposite Signs:** Add the equations to eliminate $x$ (or $y$).
    *   **Identical Signs:** Subtract the equations to eliminate $x$ (or $y$).
    *   *Note:* If the resulting equation is $0 = 0$, proceed to Step 3. If it is $0 = k$ ($k \neq 0$), proceed to Step 4.
3.  **Solve:** Solve the resulting single-variable equation for the eliminated variable.
4.  **Back-Substitute:** Substitute the value of the eliminated variable back into one of the original equations to find the other variable.

---

### 3. Identifying Inconsistency & Dependency
*   **$0 = 0 \implies$ Dependent / Infinitely many solutions:**
    *   This occurs when the system represents a line.
    *   *Example:* $2x + 3y = 6$ and $4x + 6y = 12$.
    *   *Check:* $4x + 6y = 2(2x + 3y)$. Since $2x + 3y = 6$, then $4x + 6y = 12$. The system is dependent.

*   **$0 = k \implies$ Inconsistent / No solution:**
    *   This occurs when the system represents a point (no solution).
    *   *Example:* $2x + 3y = 6$ and $4x + 6y = 12$.
    *   *Check:* $4x + 6y = 2(2x + 3y) = 2(6) = 12$. The system is inconsistent.

---

### 4. Worked Example: Income-Expenditure Problem
**Given:**
1.  $9x - 4y = 2000$
2.  $7x - 3y = 2000$

**Solution:**

**Step 1: Multiply equations by non-zero constants to equalize coefficients.**
To eliminate $

---

## Section 3.5: Master Formula Repository & Consistency Decision Matrix

# Unit 3: Pair of Linear Equations in Two Variables
## Master Formula Repository & Consistency Decision Matrix

### 1. Master Decision Matrix

| Property | Ratio $\frac{a_1}{a_2}$ | Ratio $\frac{b_1}{b_2}$ | Ratio $\frac{c_1}{c_2}$ | Algebraic Nature | Consistency | Determinant Interpretation |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Graphical** | Slope of line 1 ($m_1$) | Slope of line 2 ($m_2$) | Slope of line 1 ($m_1$) | $y = mx + c$ | $m_1 = m_2$ | $m_1 = m_2$ |
| **Algebraic** | $y = mx + c$ | $y = mx + c$ | $y = mx + c$ | $y = mx + c$ | $c_1 = c_2$ | $c_1 = c_2$ |
| **Consistency** | $c_1 = c_2$ | $c_1 = c_2$ | $c_1 = c_2$ | $c_1 = c_2$ | $c_1 = c_2$ | $c_1 = c_2$ |
| **Determinant** | $\Delta_1 = 0$ | $\Delta_2 = 0$ | $\Delta_1 = 0$ | $\Delta_1 = 0$ | $\Delta_1 = \Delta_2$ | $c_1 = c_2$ |

---

### 2. Comparison: Substitution vs. Elimination

| Feature | Substitution Method | Elimination Method |
| :--- | :--- | :--- |
| **Computational Efficiency** | **High.** Requires solving one equation for one variable. | **Low.** Requires solving two equations for two variables. |
| **Best Use Cases** | When one variable is already isolated or easy to isolate. | When both variables are isolated or when substitution leads to a complex system. |
| **Risk of Error** | High. Requires careful substitution of values. | Low. Systematic application of rules. |
| **Time Required** | Shorter per step. | Longer per step. |
| **Verdict** | Preferred for simpler systems. | Preferred for complex systems requiring symmetry. |

---

### 3. Standard Forms and Sign Conventions

**Rule:** $c_1$ and $c_2$ must be on the **Left Hand Side (LHS)** of the equation.
$$ \frac{a_1 x + b_1}{c_1} = \frac{a_2 x + b_2}{c_2} $$

**Sign Convention:**
*   **Positive $c$:** $x$ is on the LHS.
*   **Negative $c$:** $x$ is on the RHS.
*   **Zero $c$:** $x$ is on the LHS (or RHS).

**Example:**
$$ \frac{2x - 3}{1} = \frac{4x - 5}{2} $$
*   $c_1 = 1$ (LHS)
*   $c_2 = 2$ (LHS

---

## Section 3.6: Step-by-Step Algorithmic Problem Solving Procedures

# Unit 3: Pair of Linear Equations in Two Variables
## Section 3.6: Step-by-Step Algorithmic Problem Solving Procedures

### 1. Algorithm 1: Graphical Solution of a Linear Pair
**Objective:** Find the coordinate table $(x, y)$ and the vertex intersection point.

**Procedure:**
1.  **Formulate Equations:** Write the two linear equations in the form $Ax + By = C$.
2.  **Solve for $x$ and $y$ (Coordinate Tables):**
    *   Isolate $x$ in one equation and $y$ in the other.
    *   Solve the system using substitution or elimination to find the exact coordinates $(x_1, y_1)$ and $(x_2, y_2)$.
3.  **Plot the Lines:**
    *   Plot point $(x_1, y_1)$ on the $x$-axis.
    *   Plot point $(x_2, y_2)$ on the $y$-axis.
    *   Draw the full lines extending through these points.
4.  **Find the Intersection:**
    *   Identify the point where the two lines cross. This is the vertex of the linear pair.
    *   Verify that the intersection point satisfies both original equations.

---

### 2. Algorithm 2: Determining Consistency without Drawing Graphs (Ratio Tests)
**Objective:** Determine if a system of equations represents a consistent, inconsistent, or inconsistent system.

**Procedure:**
1.  **Formulate Equations:** Write the two linear equations in the form $Ax + By = C$.
2.  **Calculate the Ratio of Coefficients:**
    *   Let $A_1 = A$ and $B_1 = B$.
    *   Let $A_2 = A$ and $B_2 = B$.
    *   Calculate the ratio $R = \frac{A_1}{A_2}$ and $S = \frac{B_1}{B_2}$.
3.  **Apply Ratio Test:**
    *   **Case A (Consistent):** If $R = S$, the system is **consistent**. The lines are parallel (or coincident).
    *   **Case B (Inconsistent):** If $R \neq S$, the system is **inconsistent**. The lines are perpendicular (or coincident).
    *   **Case C (No Solution):** If $R = S$ but $A_1 \neq A_2$ (or $B_1 \neq B_2$), the system is **no solution**.

---

### 3. Algorithm 3: Solving Fractional / Decimal Linear Systems (LCM & Powers of 10)
**Objective:** Clear denominators and solve for $x$ and $y$ using standard arithmetic.

**Procedure:**
1.  **Identify Fractions:** Check if the system contains fractions. If so, identify the Least Common Multiple (LCM) of the denominators.
2.  **Clear Denominators:** Multiply every term in both equations by the LCM to eliminate fractions.
    *   *Note:* If the LCM is not an integer, multiply by the reciprocal of the LCM.
3.  **Solve for $x$ and $y$:**
    *   Rearrange the system to isolate $x$ and $y$.
    *   Solve the resulting linear system

---

## Section 3.7: Foundational & Concept-Building Worked Examples

# Unit 3: Pair of Linear Equations in Two Variables
## Section 3.7: Foundational & Concept-Building Worked Examples

### **Task 1: Graphical Consistency and Solution**
**Equations:**
1. $x + 3y = 6$
2. $2x - 3y = 12$

**Analysis:**
- Slope of Eq 1: $m_1 = -3$
- Slope of Eq 2: $m_2 = 2$
- Since $m_1 \neq m_2$, the lines are **parallel**.
- **Check:** Substitute $x = 6 - 3y$ into Eq 2:
  $2(6 - 3y) - 3y = 12 \implies 12 - 6y - 3y = 12 \implies -9y = 0 \implies y = 0$.
  If $y=0$, $x=6$.
- **Solution:** $(6, 0)$.
- **Conclusion:** The system is **consistent**.

---

### **Task 2: Substitution Method**
**Equations:**
1. $\sqrt{2}x + \sqrt{3}y = 0$
2. $\sqrt{3}x - \sqrt{8}y = 0$

**Step 1: Simplify Coefficients**
- Eq 1: $\sqrt{2}x + \sqrt{3}y = 0$
- Eq 2: $\sqrt{3}x - 2\sqrt{2}y = 0$ (Note: $\sqrt{8} = \sqrt{4 \times 2} = 2\sqrt{2}$)

**Step 2: Eliminate $x$**
Multiply Eq 1 by $\sqrt{3}$ and Eq 2 by $\sqrt{2}$:
- $m_1 \cdot \text{Eq 1} \implies \sqrt{2} \cdot \sqrt{3}x + \sqrt{2} \cdot \sqrt{3}y = 0 \implies \sqrt{6}x + \sqrt{6}y = 0$
- $m_2 \cdot \text{Eq 2} \implies \sqrt{3} \cdot \sqrt{3}x - \sqrt{3} \cdot 2\sqrt{2}y = 0 \implies 3x - 2\sqrt{6}y = 0$

**Step 3: Solve for $y$**
From Eq 1: $\sqrt{6}y = -\sqrt{6}x \implies y = -\sqrt{6}x / \sqrt{6} = -x$.
Substitute $y = -x$ into Eq 2:
$3x - 2\sqrt{6}(-x) = 0 \implies 3x + 2\sqrt{6}x = 0 \implies x(3 + 2\sqrt{6}) = 0$.
Since $3 + 2\sqrt{6} \neq 0$, $x = 0$.
Then $y = -0 = 0$.
**Solution:** $(0, 0)$.

---

### **Task 3: Elimination Method**
**Equations:**

---

## Section 3.8: Word Problems & Real-World Mathematical Modeling (HOTS)

# Unit 3: Pair of Linear Equations in Two Variables
## Section 3.8: Word Problems & Real-World Mathematical Modeling (HOTS)

### **Task Instructions**
Generate comprehensive, structured solutions for the 5 classic types of word problems in Unit 3:
1.  **Category 1**: Sum of a two-digit number and its reversal is 66; digits differ by 2. Find the number.
2.  **Category 2**: Five years hence, Jacob's age will be 3 times his son; 5 years ago, Jacob was 7 times his son. Find present ages.
3.  **Category 3**: A fraction becomes $9/11$ if 2 is added to numerator and denominator; becomes $5/6$ if 3 is added to both. Find the fraction.
4.  **Category 4**: Taxi charges: 10 km costs Rs 105, 15 km costs Rs 155. Find fixed charge and rate per km; calculate cost for 25 km.
5.  **Category 5**: Meena withdraws Rs 2000, receives 25 notes in total of Rs 50 and Rs 100. Find the number of each note.

---

### **1. Category 1: Two-Digit Number Problem**

**Problem Statement:**
Sum of a two-digit number and its reversal is 66; digits differ by 2. Find the number.

**Solution:**
Let the two-digit number be $x$.
The digits of $x$ are $d_1$ and $d_2$, where $10d_1 + d_2 = x$.
The reversal of $x$ is $10d_2 + d_1$.
The given condition is:
$$ (10d_1 + d_2) + (10d_2 + d_1) = 66 $$
$$ 11(d_1 + d_2) = 66 $$
$$ d_1 + d_2 = 6 $$
Since $x$ is a two-digit number, $10 \le x \le 99$.
Also, the digits differ by 2: $|d_1 - d_2| = 2$.
Possible pairs $(d_1, d_2)$ satisfying $d_1 + d_2 = 6$ and $|d_1 - d_2| = 2$:
1.  $(3, 3)$: $3+3=6$, $|3-3|=0 \neq 2$ (Invalid)
2.  $(4, 2)$: $4+2=6$, $|4-2|=2$ (Valid)
3.  $(2, 4)$: $2+4=6$, $|2-4|=2$ (Valid)
4.  $(5, 1)$: $5+1=6$, $|5-1|=4 \neq 2$ (Invalid)

Let $x$ be the number.
If $d_1 = 4, d_2 = 2$, then $x = 42$.
If $d_1 = 2, d_2 = 4$, then $x = 24$.

**Answer:**
The number is either **42** or **24**.

---

### **

---

## Section 3.9: Common Misconceptions, Degenerate Cases & Exam Traps

# Unit 3: Pair of Linear Equations in Two Variables
## Section 3.9: Common Misconceptions, Degenerate Cases & Exam Traps

### 1. Trap 1: Inconsistent Constant Placement ($c_1$ on LHS while $c_2$ on RHS)
**Misconception:** Students incorrectly place $c_1$ on the left-hand side (LHS) and $c_2$ on the right-hand side (RHS) of the equation, leading to a flipped ratio test $\frac{c_1}{c_2}$.
**Correct Step:**
$$
\begin{aligned}
c_1 x + c_1 y &= c_1 \\
c_2 x + c_2 y &= c_2 \\
\frac{c_1 x + c_1 y}{c_2 x + c_2 y} &= \frac{c_1}{c_2}
\end{aligned}
$$
**Why it fails:** The ratio $\frac{c_1}{c_2}$ is valid only when $c_1 \neq 0$ and $c_2 \neq 0$. If $c_1 = 0$ and $c_2 \neq 0$, the LHS is $0$ and the RHS is $c_2$, so the ratio is undefined. This causes the student to conclude the system is inconsistent.
**Exam Trap:** Students memorize $\frac{c_1}{c_2}$ blindly without checking if the numerator is zero.
**Correct Step:**
$$
\begin{aligned}
c_1 x + c_1 y &= c_1 \\
c_2 x + c_2 y &= c_2 \\
\frac{c_1 x + c_1 y}{c_2 x + c_2 y} &= \frac{c_1}{c_2} \quad \text{if } c_1 \neq 0, c_2 \neq 0
\end{aligned}
$$
**Common Trap:** $c_1 = 0$ and $c_2 \neq 0 \implies \frac{0}{c_2} = 0 \neq \frac{c_1}{c_2} = 0$.

---

### 2. Trap 2: Sign Errors during Subtraction in the Elimination Method
**Misconception:** Failing to distribute the minus sign across all terms when subtracting $c_2 x$ from $c_1 x$.
**Correct Step:**
$$
\begin{aligned}
c_1 x + c_1 y &= c_1 \\
c_2 x + c_2 y &= c_2 \\
\text{Subtracting } c_2 x \text{ from } c_1 x: \quad c_1 x - c_2 x &= c_1 - c_2 \\
\text{Subtracting } c_2 y \text{ from } c_1 y: \quad c_1 y - c_2 y &= c_1 - c_2
\end{aligned}
$$
**Why it fails:** Students forget that $-c_2 x$ becomes $-(c_2 x)$ and $-c_2 y$ becomes $-(c_2 y)$.
**Exam Trap:** Students write $c_1 x - c_2 x$ instead of

---

## Section 3.10: NCERT Exercise Walkthrough, Summary Checklist & Practice Drill

# Unit 3: Pair of Linear Equations in Two Variables
## Section 3.10: NCERT Exercise Walkthrough, Summary Checklist & Practice Drill

### 1. Comprehensive Breakdown of NCERT Exercises 3.1, 3.2, and 3.3

**Exercise 3.1: Solving Systems of Linear Equations**
*   **Problem:** Solve the system:
    $$ \begin{cases} x + y = 5 \\ 2x - y = 1 \end{cases} $$
*   **Method:** Elimination (Substitution).
    *   Add the two equations: $(x+y) + (2x-y) = 5+1 \Rightarrow 3x = 6 \Rightarrow x = 2$.
    *   Substitute $x=2$ into the first equation: $2+y=5 \Rightarrow y=3$.
    *   **Solution:** $(2, 3)$.
*   **Key Concept:** The system has a unique solution.

**Exercise 3.2: Solving Systems of Linear Equations (General Method)**
*   **Problem:** Solve the system:
    $$ \begin{cases} 3x + 2y = 12 \\ 2x - y = 4 \end{cases} $$
*   **Method:** Elimination.
    *   Multiply the second equation by 2: $4x - 2y = 8$.
    *   Add to the first equation: $(3x+2y) + (4x-2y) = 12+8 \Rightarrow 7x = 20 \Rightarrow x = \frac{20}{7}$.
    *   Substitute $x$ into the first equation: $3(\frac{20}{7}) + 2y = 12 \Rightarrow \frac{60}{7} + 2y = \frac{84}{7} \Rightarrow 2y = \frac{24}{7} \Rightarrow y = \frac{12}{7}$.
    *   **Solution:** $(\frac{20}{7}, \frac{12}{7})$.
*   **Key Concept:** Determinant of the coefficient matrix $\Delta = b_1a_2 - b_2a_1$. If $\Delta \neq 0$, unique solution exists.

**Exercise 3.3: Solving Systems of Linear Equations (HOTS)**
*   **Problem:** Solve the system:
    $$ \begin{cases} 3x + 2y = 12 \\ 2x - y = 4 \end{cases} $$
    *   *Note: This is the same system as Exercise 3.2.*
*   **Method:** Elimination.
    *   As calculated above, $x = \frac{20}{7}$ and $y = \frac{12}{7}$.
*   **Key Concept:** HOTS requires identifying the system type and applying the appropriate elimination technique.

---

### 2. Rapid-Fire Revision Checklist (10 Bullet Points)

1.  **Identify the System Type:** Is it a system of 2 linear equations in 2 variables? (Yes/No).
2.  **Check for Consistency:** Does the system have a unique solution, no solution, or infinitely many solutions? (Use $\Delta$ test).
3.  **Apply Elimination
