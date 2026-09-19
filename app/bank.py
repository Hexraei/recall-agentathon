"""The question bank: two departments, five topics each, four questions a topic.

Why the bank is fixed rather than generated live
------------------------------------------------
The report at the end is the agentic artifact - it reads a student's whole
answer history, compares it against the class, and writes a judgement. For that
judgement to be worth anything, the thing being judged has to be solid. A model
inventing both the question AND the diagnosis means a wrong report can always be
blamed on a bad question, and nobody can tell the two failures apart.

So every wrong option is pre-mapped, here, at authoring time, to the specific
misconception picking it reveals. Deterministic, instant, free. The model's work
stays where it earns its keep: reading twenty of these mappings together and
saying what they add up to.

Departments
-----------
robotics          - theoretical, slightly harder. Kinematics, control, state
                    estimation, planning, dynamics.
computer_science  - conceptual, kept simple. Complexity, data structures,
                    recursion, memory, correctness.

Each `concept` string is the unit the report reasons over, and the same concept
deliberately appears across MORE THAN ONE topic where the underlying idea is
shared - that is what lets the agent say "this is not a gap in sorting, it is a
gap in counting nested work" rather than just listing topics with low scores.
"""
from __future__ import annotations

from pydantic import BaseModel

DEPARTMENTS = {
    "robotics": "Robotics",
    "computer_science": "Computer Science",
}


class Option(BaseModel):
    key: str
    text: str
    correct: bool
    misconception: str | None = None
    """What picking this reveals, phrased about the work and never the person.
    None on the correct option - there is nothing to diagnose."""


class Question(BaseModel):
    id: str
    department: str
    topic: str
    concept: str
    """The reasoning skill under test. Shared across topics on purpose."""
    prompt: str
    options: list[Option]

    def option(self, key: str) -> Option:
        for o in self.options:
            if o.key == key:
                return o
        raise KeyError(f"no option {key!r} on {self.id}")

    @property
    def answer_key(self) -> str:
        return next(o.key for o in self.options if o.correct)


def _q(qid, dept, topic, concept, prompt, options) -> Question:
    return Question(id=qid, department=dept, topic=topic, concept=concept,
                    prompt=prompt,
                    options=[Option(key=k, text=t, correct=c, misconception=m)
                             for k, t, c, m in options])


# ============================================================ COMPUTER SCIENCE
# Conceptual and simple. Four concepts recur across the five topics so the
# report can cut across topic boundaries.

CS: list[Question] = [
    # ---------------------------------------------------- Topic 1: Complexity
    _q("cs_t1_q1", "computer_science", "Time Complexity",
       "counting work inside loops",
       "What is the worst-case time complexity of insertion sort?",
       [("A", "O(n) — the outer loop runs n times", False,
         "counted only the outer loop and did not account for the shifting "
         "work the inner loop does on each pass"),
        ("B", "O(n²) — each of the n passes may shift up to n elements", True, None),
        ("C", "O(log n) — the array is searched, not scanned", False,
         "applied logarithmic growth to a linear scan; nothing in insertion "
         "sort halves the remaining work"),
        ("D", "O(1) — sorting does not depend on input size", False,
         "treated cost as constant with no relationship stated between input "
         "size and work done")]),

    _q("cs_t1_q2", "computer_science", "Time Complexity",
       "counting work inside loops",
       "Removing duplicates with `if x not in result` for each of n elements "
       "costs:",
       [("A", "O(n) — the loop goes through the list once", False,
         "counted only the visible loop and missed the work hidden inside the "
         "membership test, which itself scans the result list"),
        ("B", "O(n²) — each element may trigger a scan of the growing result", True, None),
        ("C", "O(n log n) — membership checking is like a sorted search", False,
         "assumed the membership check is a sorted search; `not in` on a list "
         "scans linearly"),
        ("D", "O(1) — membership checking is instant", False,
         "assumed constant-time membership with no basis; a list is not a hash "
         "table")]),

    _q("cs_t1_q3", "computer_science", "Time Complexity",
       "relating loop structure to growth rate",
       "Binary search on a sorted array of n elements costs:",
       [("A", "O(n) — there is still a loop running until it finds the answer", False,
         "treated the presence of a loop as evidence of linear growth, without "
         "asking how much of the problem each pass eliminates"),
        ("B", "O(log n) — each comparison halves the remaining search space", True, None),
        ("C", "O(n²) — comparing the middle element takes n steps", False,
         "claimed a single index-and-compare costs n steps, with no argument"),
        ("D", "O(1) — sorted arrays are searched instantly", False,
         "asserted constant time with no argument for why sorting would remove "
         "the search entirely")]),

    _q("cs_t1_q4", "computer_science", "Time Complexity",
       "relating loop structure to growth rate",
       "A loop that halves `n` each pass, with O(n) work inside each pass, is:",
       [("A", "O(log n) — the halving dominates", False,
         "tracked how many passes happen but not how much each pass costs"),
        ("B", "O(n) — the linear work dominates the halving", True, None),
        ("C", "O(n²) — a loop inside a loop is always quadratic", False,
         "applied 'nested loops means quadratic' as a rule without checking how "
         "the inner bound shrinks"),
        ("D", "O(n log n) — multiply the two together", False,
         "multiplied the passes by the largest inner cost, ignoring that the "
         "inner cost halves alongside them")]),

    # ------------------------------------------------ Topic 2: Data Structures
    _q("cs_t2_q1", "computer_science", "Data Structures",
       "choosing a structure from its access pattern",
       "You need to repeatedly get the smallest item from a changing set. Best "
       "structure?",
       [("A", "A sorted list, re-sorted after each insert", False,
         "chose a structure whose ordering must be rebuilt on every change, "
         "paying O(n log n) repeatedly for a property only needed at one end"),
        ("B", "A min-heap", True, None),
        ("C", "A hash table", False,
         "chose a structure with no ordering at all for a task defined entirely "
         "by order"),
        ("D", "A plain array, scanned each time", False,
         "accepted a full O(n) scan per query where a structure maintaining the "
         "minimum would answer in O(log n)")]),

    _q("cs_t2_q2", "computer_science", "Data Structures",
       "choosing a structure from its access pattern",
       "Checking 'have I seen this value before?' a million times is fastest with:",
       [("A", "A list, using `in`", False,
         "chose linear scanning for a membership question, the exact pattern a "
         "hash structure exists to eliminate"),
        ("B", "A set", True, None),
        ("C", "A sorted list with binary search", False,
         "chose O(log n) lookups where O(1) is available, and pays to keep the "
         "list sorted on every insert"),
        ("D", "A stack", False,
         "chose a structure that only exposes its most recent item for a "
         "question about all items seen")]),

    _q("cs_t2_q3", "computer_science", "Data Structures",
       "counting work inside loops",
       "Appending n items to a Python list, one at a time, costs in total:",
       [("A", "O(n²) — the list is copied on every append", False,
         "assumed every append reallocates; amortised growth means copies "
         "happen rarely, not every time"),
        ("B", "O(n) amortised — growth doubles, so copies are rare", True, None),
        ("C", "O(n log n) — the list is re-sorted as it grows", False,
         "assumed appending maintains sort order; a list preserves insertion "
         "order and sorts nothing"),
        ("D", "O(1) — appending is constant", False,
         "gave the cost of ONE append where the question asked for n of them")]),

    _q("cs_t2_q4", "computer_science", "Data Structures",
       "reasoning about references and copies",
       "`b = a` where `a` is a list, then `b.append(1)`. What is `a`?",
       [("A", "Unchanged — `b` is a copy", False,
         "treated assignment as copying; it binds a second name to the same "
         "object"),
        ("B", "Also has the new element — both names refer to one list", True, None),
        ("C", "Raises an error — lists cannot be shared", False,
         "assumed a restriction that does not exist; shared references are the "
         "default"),
        ("D", "Becomes a nested list", False,
         "confused appending to a shared list with nesting one list inside "
         "another")]),

    # ------------------------------------------------------ Topic 3: Recursion
    _q("cs_t3_q1", "computer_science", "Recursion",
       "identifying a terminating base case",
       "`def f(n): return f(n-1) + 1` called with n=5 will:",
       [("A", "Return 5", False,
         "traced the intended arithmetic but not the termination; nothing in "
         "this function ever stops the descent"),
        ("B", "Recurse forever until the stack overflows — there is no base case", True, None),
        ("C", "Return 0", False,
         "assumed the recursion bottoms out at zero on its own; no condition "
         "in the code checks for it"),
        ("D", "Raise a TypeError", False,
         "expected a type failure where the actual failure is unbounded depth")]),

    _q("cs_t3_q2", "computer_science", "Recursion",
       "identifying a terminating base case",
       "A base case must guarantee that:",
       [("A", "The function returns the right answer", False,
         "described correctness, which is a separate property from termination"),
        ("B", "Some call eventually returns without recursing further", True, None),
        ("C", "The function is called at least once", False,
         "described entry into the recursion rather than its exit"),
        ("D", "The input is a number", False,
         "named a type constraint, which has no bearing on whether recursion "
         "stops")]),

    _q("cs_t3_q3", "computer_science", "Recursion",
       "relating loop structure to growth rate",
       "Naive recursive Fibonacci, `fib(n-1) + fib(n-2)`, costs roughly:",
       [("A", "O(n) — it counts down from n", False,
         "counted the depth of the recursion but not its branching; each call "
         "spawns two more"),
        ("B", "Exponential — each call branches into two more", True, None),
        ("C", "O(log n) — the problem shrinks each call", False,
         "treated a shrinking argument as halving; subtracting one is not "
         "dividing by two"),
        ("D", "O(n²) — two recursive calls means squared", False,
         "read 'two calls' as a squaring factor rather than a branching factor "
         "compounding at every level")]),

    _q("cs_t3_q4", "computer_science", "Recursion",
       "counting work inside loops",
       "Merge sort's recursion splits in half; each level does O(n) merging. "
       "Total:",
       [("A", "O(n) — one pass of merging", False,
         "counted the merging at a single level and not the log n levels that "
         "each pay it"),
        ("B", "O(n log n) — log n levels, O(n) work per level", True, None),
        ("C", "O(log n) — halving dominates", False,
         "counted the levels but dropped the per-level merging cost entirely"),
        ("D", "O(n²) — recursion plus a loop", False,
         "applied a nested-structure rule without checking how much each level "
         "actually costs")]),

    # --------------------------------------------------------- Topic 4: Memory
    _q("cs_t4_q1", "computer_science", "Memory & State",
       "reasoning about references and copies",
       "A mutable default argument `def f(x, acc=[])` across two calls:",
       [("A", "Starts fresh each call", False,
         "assumed the default is re-evaluated per call; it is created once when "
         "the function is defined"),
        ("B", "Keeps whatever the first call left in it", True, None),
        ("C", "Raises an error on the second call", False,
         "expected a failure where the actual behaviour is silent sharing"),
        ("D", "Copies itself automatically", False,
         "assumed an implicit copy that the language does not perform")]),

    _q("cs_t4_q2", "computer_science", "Memory & State",
       "reasoning about references and copies",
       "A shallow copy of a list of lists means:",
       [("A", "Everything is fully independent", False,
         "treated shallow as deep; only the outer list is new"),
        ("B", "The outer list is new, but the inner lists are shared", True, None),
        ("C", "Nothing is copied at all", False,
         "treated shallow copy as plain assignment; the outer container really "
         "is duplicated"),
        ("D", "Only the first element is copied", False,
         "described a partial copy of elements, which is not what either copy "
         "depth means")]),

    _q("cs_t4_q3", "computer_science", "Memory & State",
       "choosing a structure from its access pattern",
       "Why is a dictionary lookup usually O(1)?",
       [("A", "Dictionaries are stored sorted", False,
         "attributed the speed to ordering; a hash table maintains no order at "
         "all"),
        ("B", "The key is hashed straight to a slot, skipping the search", True, None),
        ("C", "Dictionaries are small", False,
         "explained the cost by size rather than by the mechanism, which holds "
         "regardless of size"),
        ("D", "Python caches the last lookup", False,
         "attributed general behaviour to a caching special case")]),

    _q("cs_t4_q4", "computer_science", "Memory & State",
       "justifying claims with a concrete argument",
       "'This code is fast' is a weak claim mainly because:",
       [("A", "It does not say which language", False,
         "named a detail that would not settle the question either way"),
        ("B", "It states no input size and no measurement", True, None),
        ("C", "Fast is a subjective word", False,
         "objected to the wording rather than to the missing evidence"),
        ("D", "Code speed cannot be measured", False,
         "denied that measurement is possible, which abandons the standard "
         "rather than meeting it")]),

    # ---------------------------------------------------- Topic 5: Correctness
    _q("cs_t5_q1", "computer_science", "Correctness",
       "justifying claims with a concrete argument",
       "Your function passed all 12 tests. This shows:",
       [("A", "The function is correct", False,
         "treated passing tests as proof of correctness; tests show absence of "
         "the failures you thought to check for"),
        ("B", "It handles those 12 cases — nothing beyond them", True, None),
        ("C", "Nothing at all", False,
         "discarded real evidence entirely; passing tests is weak evidence, not "
         "zero evidence"),
        ("D", "The tests are too easy", False,
         "drew a conclusion about the tests that the result does not support")]),

    _q("cs_t5_q2", "computer_science", "Correctness",
       "identifying a terminating base case",
       "A `while` loop whose condition never becomes false is missing:",
       [("A", "A return statement", False,
         "named how a function exits rather than how a loop does"),
        ("B", "Something inside it that moves toward the condition failing", True, None),
        ("C", "An else branch", False,
         "named an optional construct with no bearing on termination"),
        ("D", "A counter variable", False,
         "named one common mechanism as if it were the requirement; the "
         "requirement is progress, however achieved")]),

    _q("cs_t5_q3", "computer_science", "Correctness",
       "justifying claims with a concrete argument",
       "The strongest evidence that a sort is stable is:",
       [("A", "It sorted the example correctly", False,
         "used an output that a stable and unstable sort would both produce"),
        ("B", "Equal keys came out in their original relative order", True, None),
        ("C", "The documentation says so", False,
         "cited an authority rather than an observation, when the property is "
         "directly testable"),
        ("D", "It ran quickly", False,
         "offered a performance observation as evidence about ordering")]),

    _q("cs_t5_q4", "computer_science", "Correctness",
       "counting work inside loops",
       "Checking if any pair in a list sums to k, with two nested loops, is:",
       [("A", "O(n) — each element is visited once", False,
         "counted the outer loop's visits only, missing that each one runs the "
         "inner loop again"),
        ("B", "O(n²) — every element is paired against every other", True, None),
        ("C", "O(log n) — pairs can be found by halving", False,
         "assumed a halving structure that nested scanning does not have"),
        ("D", "O(1) — it stops as soon as it finds a pair", False,
         "gave the best case where the question asks for the cost in general")]),
]


# ==================================================================== ROBOTICS
# Theoretical and a step harder. Same design: concepts shared across topics.

ROBO: list[Question] = [
    # --------------------------------------------------- Topic 1: Kinematics
    _q("rb_t1_q1", "robotics", "Kinematics",
       "distinguishing forward from inverse problems",
       "Inverse kinematics for a 6-DOF arm generally has:",
       [("A", "Exactly one solution", False,
         "assumed uniqueness; multiple joint configurations commonly reach the "
         "same pose"),
        ("B", "Possibly many solutions, possibly none", True, None),
        ("C", "Always infinitely many", False,
         "generalised the redundant case to all cases; a 6-DOF arm is not "
         "redundant for a 6-DOF pose"),
        ("D", "No solution unless the arm is redundant", False,
         "treated redundancy as a precondition for solvability rather than as "
         "a cause of extra solutions")]),

    _q("rb_t1_q2", "robotics", "Kinematics",
       "reasoning about singularities and degeneracy",
       "At a kinematic singularity, the Jacobian:",
       [("A", "Becomes the identity matrix", False,
         "described a well-conditioned mapping where the defining feature is "
         "loss of rank"),
        ("B", "Loses rank — some end-effector direction becomes unreachable", True, None),
        ("C", "Becomes undefined", False,
         "treated the Jacobian as failing to exist; it exists, it is simply "
         "rank-deficient"),
        ("D", "Grows without bound", False,
         "confused the Jacobian with its inverse, which is what blows up")]),

    _q("rb_t1_q3", "robotics", "Kinematics",
       "distinguishing forward from inverse problems",
       "Forward kinematics, compared to inverse kinematics, is:",
       [("A", "Harder, because it composes many transforms", False,
         "equated the number of transforms with difficulty; composition is "
         "mechanical, inversion is not"),
        ("B", "A direct computation with a unique answer", True, None),
        ("C", "Also multi-solution", False,
         "carried the ambiguity of the inverse problem over to the forward one, "
         "where joint angles determine the pose exactly"),
        ("D", "Only defined for planar arms", False,
         "imposed a dimensional restriction that does not exist")]),

    _q("rb_t1_q4", "robotics", "Kinematics",
       "composing rigid-body transforms in order",
       "Rotating then translating is not the same as translating then rotating "
       "because:",
       [("A", "Rotation matrices are not invertible", False,
         "denied a property rotations do have; they are orthogonal and always "
         "invertible"),
        ("B", "Transform composition does not commute", True, None),
        ("C", "Translation changes the object's scale", False,
         "attributed a scaling effect to a rigid motion, which preserves size"),
        ("D", "Only one of the two is a valid transform", False,
         "treated one ordering as illegal; both are valid, they simply differ")]),

    # ------------------------------------------------------- Topic 2: Control
    _q("rb_t2_q1", "robotics", "Control",
       "relating controller terms to observed error behaviour",
       "A system settles near but never reaches its setpoint. The term to add:",
       [("A", "Proportional", False,
         "added gain to a term already producing too little force at small "
         "error, which is exactly where the steady-state offset lives"),
        ("B", "Integral — it accumulates the standing error", True, None),
        ("C", "Derivative", False,
         "added damping, which responds to rate of change; a constant offset "
         "has no rate of change"),
        ("D", "A deadband", False,
         "proposed ignoring small errors, which entrenches the offset rather "
         "than removing it")]),

    _q("rb_t2_q2", "robotics", "Control",
       "relating controller terms to observed error behaviour",
       "A system oscillates around its setpoint with growing amplitude. Most "
       "likely:",
       [("A", "Integral gain is too low", False,
         "identified a term that affects standing offset, not oscillation "
         "amplitude"),
        ("B", "Proportional gain is too high for the damping present", True, None),
        ("C", "The setpoint is wrong", False,
         "located the fault in the target rather than in the response, though "
         "the response is what is unstable"),
        ("D", "The sensor is too accurate", False,
         "treated measurement quality as a cause of instability")]),

    _q("rb_t2_q3", "robotics", "Control",
       "reasoning about feedback delay and stability",
       "Adding delay into a feedback loop tends to:",
       [("A", "Improve stability by smoothing the response", False,
         "treated delay as filtering; it shifts phase, which erodes the margin "
         "that keeps the loop stable"),
        ("B", "Reduce the stability margin — corrections arrive late", True, None),
        ("C", "Have no effect if the gain is unchanged", False,
         "treated stability as a function of gain alone, independent of timing"),
        ("D", "Eliminate steady-state error", False,
         "attributed to delay an effect that belongs to integral action")]),

    _q("rb_t2_q4", "robotics", "Control",
       "justifying claims with a concrete argument",
       "'The controller is tuned' is best supported by:",
       [("A", "It looked smooth on the demo run", False,
         "offered a single unmeasured observation where a tuning claim needs "
         "quantities"),
        ("B", "Measured overshoot and settling time against a stated target", True, None),
        ("C", "The gains match a textbook table", False,
         "cited values chosen for a different plant rather than behaviour "
         "measured on this one"),
        ("D", "It has not failed yet", False,
         "offered absence of observed failure as evidence of a performance "
         "property")]),

    # ---------------------------------------------- Topic 3: State Estimation
    _q("rb_t3_q1", "robotics", "State Estimation",
       "separating process noise from measurement noise",
       "A Kalman filter's measurement update mainly:",
       [("A", "Predicts where the robot will be next", False,
         "described the prediction step, which propagates the model forward "
         "before any measurement arrives"),
        ("B", "Corrects the prediction using a sensor reading, weighted by "
              "confidence", True, None),
        ("C", "Replaces the estimate with the sensor reading", False,
         "discarded the prediction entirely; the update blends the two by their "
         "relative certainty"),
        ("D", "Removes all noise from the measurement", False,
         "treated filtering as noise elimination rather than as weighted "
         "combination under uncertainty")]),

    _q("rb_t3_q2", "robotics", "State Estimation",
       "separating process noise from measurement noise",
       "A filter that trusts its model too much and its sensors too little "
       "shows:",
       [("A", "Jittery estimates that track noise", False,
         "described the opposite failure, which comes from over-trusting the "
         "sensor"),
        ("B", "Smooth estimates that lag reality and drift", True, None),
        ("C", "Divergence within one step", False,
         "described an immediate numerical failure; mis-weighting degrades the "
         "estimate gradually"),
        ("D", "No change in behaviour", False,
         "treated the noise covariances as having no effect on the outcome")]),

    _q("rb_t3_q3", "robotics", "State Estimation",
       "reasoning about singularities and degeneracy",
       "Localising with only one range beacon leaves the pose:",
       [("A", "Fully determined", False,
         "treated one constraint as sufficient for a multi-dimensional pose"),
        ("B", "Constrained to a circle — under-determined", True, None),
        ("C", "Over-determined", False,
         "inverted the relationship; over-determined means more constraints "
         "than unknowns"),
        ("D", "Undefined and unusable", False,
         "discarded a genuine partial constraint as worthless")]),

    _q("rb_t3_q4", "robotics", "State Estimation",
       "justifying claims with a concrete argument",
       "The strongest evidence that odometry is drifting is:",
       [("A", "The robot looks slightly off", False,
         "offered an impression where the claim is about accumulating error "
         "over time"),
        ("B", "Estimated pose diverges from a fixed reference, growing with "
              "distance travelled", True, None),
        ("C", "The wheels are worn", False,
         "named a plausible cause and offered it in place of the observation"),
        ("D", "The map is old", False,
         "named a property of the map rather than of the pose estimate")]),

    # -------------------------------------------------- Topic 4: Path Planning
    _q("rb_t4_q1", "robotics", "Path Planning",
       "relating search strategy to guarantees",
       "A* returns an optimal path provided the heuristic is:",
       [("A", "Fast to compute", False,
         "named a performance property where optimality depends on a bound"),
        ("B", "Admissible — never overestimates the true remaining cost", True, None),
        ("C", "Always zero", False,
         "named a heuristic that is admissible but reduces A* to Dijkstra; the "
         "requirement is the bound, not the value"),
        ("D", "Equal to the true cost", False,
         "named the ideal case as the requirement; it is sufficient, not "
         "necessary")]),

    _q("rb_t4_q2", "robotics", "Path Planning",
       "relating search strategy to guarantees",
       "RRT is described as probabilistically complete, which means:",
       [("A", "It always finds the shortest path", False,
         "confused completeness with optimality; RRT gives no optimality "
         "guarantee"),
        ("B", "Given enough samples it will find a path if one exists", True, None),
        ("C", "It finds a path in bounded time", False,
         "read a limiting guarantee as a time bound"),
        ("D", "It never fails", False,
         "read a probabilistic guarantee as a deterministic one")]),

    _q("rb_t4_q3", "robotics", "Path Planning",
       "counting work inside loops",
       "Grid search cost when resolution doubles in each of 3 dimensions:",
       [("A", "Doubles", False,
         "scaled the cost by the resolution factor once, though it applies "
         "along every dimension"),
        ("B", "Grows 8× — the factor applies per dimension", True, None),
        ("C", "Stays the same", False,
         "treated cell count as independent of resolution"),
        ("D", "Grows 3×", False,
         "added the dimensions rather than compounding across them")]),

    _q("rb_t4_q4", "robotics", "Path Planning",
       "composing rigid-body transforms in order",
       "A path planned in map frame, executed in robot frame, needs:",
       [("A", "No transform — frames are interchangeable", False,
         "treated distinct frames as equivalent, which discards the pose "
         "relating them"),
        ("B", "The map-to-robot transform applied to each waypoint", True, None),
        ("C", "Only a rotation", False,
         "kept the orientation change and dropped the translation between "
         "frame origins"),
        ("D", "Re-planning from scratch", False,
         "discarded a valid plan that a transform would have reused")]),

    # ------------------------------------------------------- Topic 5: Dynamics
    _q("rb_t5_q1", "robotics", "Dynamics",
       "distinguishing kinematic from dynamic models",
       "A kinematic model, unlike a dynamic one, ignores:",
       [("A", "Joint angles", False,
         "named the quantity a kinematic model is built from"),
        ("B", "Mass, inertia and the forces producing the motion", True, None),
        ("C", "Link lengths", False,
         "named a geometric parameter kinematics depends on directly"),
        ("D", "Time entirely", False,
         "overstated the omission; kinematics handles velocities, just not "
         "their causes")]),

    _q("rb_t5_q2", "robotics", "Dynamics",
       "distinguishing kinematic from dynamic models",
       "A fast arm tracks a kinematically-planned path poorly mainly because:",
       [("A", "The path was geometrically wrong", False,
         "located the fault in the geometry, though the path is reachable; the "
         "problem is the force needed to follow it at speed"),
        ("B", "Inertial forces at speed were never accounted for", True, None),
        ("C", "The controller gain is too low", False,
         "offered a tuning symptom in place of the modelling gap causing it"),
        ("D", "Encoders are too slow", False,
         "named a sensing limit where the omission is in the model")]),

    _q("rb_t5_q3", "robotics", "Dynamics",
       "reasoning about feedback delay and stability",
       "Gravity compensation helps mainly by:",
       [("A", "Making the arm lighter", False,
         "treated compensation as changing the physical mass rather than "
         "cancelling a known torque"),
        ("B", "Removing a predictable standing torque the feedback would "
              "otherwise fight", True, None),
        ("C", "Reducing sensor noise", False,
         "attributed a measurement benefit to a feed-forward torque term"),
        ("D", "Increasing the maximum speed", False,
         "named a performance outcome rather than the mechanism")]),

    _q("rb_t5_q4", "robotics", "Dynamics",
       "reasoning about singularities and degeneracy",
       "Near a singularity, commanding a small end-effector motion can require:",
       [("A", "Smaller joint velocities than usual", False,
         "inverted the relationship; the mapping degrades, it does not become "
         "more efficient"),
        ("B", "Very large joint velocities", True, None),
        ("C", "Exactly the same joint velocities", False,
         "treated the joint-to-task mapping as uniform across the workspace"),
        ("D", "No joint motion at all", False,
         "described a frozen arm where the actual risk is a violent one")]),
]


ALL: list[Question] = CS + ROBO


def by_id(qid: str) -> Question:
    for q in ALL:
        if q.id == qid:
            return q
    raise KeyError(f"no question {qid!r}")


def for_department(department: str) -> list[Question]:
    """The 20 questions for one department, in topic order."""
    return [q for q in ALL if q.department == department]


def topics(department: str) -> list[str]:
    seen: list[str] = []
    for q in for_department(department):
        if q.topic not in seen:
            seen.append(q.topic)
    return seen
