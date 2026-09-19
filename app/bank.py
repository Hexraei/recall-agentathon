"""The question bank: two departments, five topics each, four questions a topic.

Pitched at a second-year student
--------------------------------
An earlier version of this bank was written at final-year level - Kalman filter
update steps, Jacobian rank deficiency, RRT probabilistic completeness. The
first real tester scored 14/20 on his own department and every miss landed in
the hardest material, which tells you about the questions rather than about him.
A diagnostic that ambushes people measures their nerve, not their understanding.

These are written for someone midway through second year: one idea per question,
no trick options, and plain wording. A student who has been to the lectures
should get most of them. The target is roughly 70-80% for a typical student -
high enough that nobody feels caught out, low enough that the misses are real
and the report has something true to say.

Concepts, and why they repeat
-----------------------------
Each `concept` is the unit the report reasons over, and every concept here has
THREE OR FOUR questions behind it, deliberately spread across different topics.

Both halves of that matter. Two questions cannot separate a gap from a slip, so
a concept with only two behind it can never be called strong or weak - the first
bank had several, and the resulting report said "mixed" seven times in a row and
found no pattern at all. And a concept confined to one topic can never show that
one cause is behind trouble in several places, which is the whole point:

    "This is not a gap in sorting, it is a gap in counting nested work."

Concept names are written the way a student would say them, because they appear
in the report that student reads.

Why the bank is fixed rather than generated
-------------------------------------------
Every wrong option is pre-mapped, here, to the misconception picking it reveals.
If a model invented both the question AND the diagnosis, a wrong report could
always be blamed on a bad question and the two failures would be indistinguish-
able. Fixing the diagnosis makes the report falsifiable.
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
    """The idea under test. Shared across topics on purpose."""
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
    """Build a question, rotating the options so the answer key is not always B.

    Every question below is written with the correct option second, because
    that keeps the source readable - the right answer sits next to the
    misconception it corrects. Shipped as written, that made B correct on all
    40 questions, which the first end-to-end run found by scoring 20/20 with B
    on everything. A tester who spots that has a perfect score and the data is
    worthless.

    So the options are rotated here by a hash of the question id: fixed per
    question (the same student always sees the same layout, and a rerun of the
    same quiz is comparable), spread across A-D, and requiring no edit to the
    bank itself.
    """
    built = [Option(key=k, text=t, correct=c, misconception=m)
             for k, t, c, m in options]
    shift = sum(ord(ch) for ch in qid) % len(built)
    rotated = built[shift:] + built[:shift]
    for key, opt in zip("ABCD", rotated):
        opt.key = key
    return Question(id=qid, department=dept, topic=topic, concept=concept,
                    prompt=prompt, options=rotated)


# ============================================================ COMPUTER SCIENCE
# Five topics, four concepts, each concept spread over three or four questions
# in different topics:
#
#   working out how long code takes   4 questions, 3 topics
#   picking the right data structure  4 questions, 3 topics
#   knowing when a loop or function stops   4 questions, 3 topics
#   understanding what a variable holds     4 questions, 3 topics
#   backing up a claim with evidence        4 questions, 3 topics

CS: list[Question] = [
    # -------------------------------------------------- Topic 1: How Code Runs
    _q("cs_t1_q1", "computer_science", "How Code Runs",
       "working out how long code takes",
       "A loop runs through a list of n items once. How does the time it takes "
       "grow as the list gets bigger?",
       [("A", "It stays the same no matter how big the list is", False,
         "treated the work as fixed; a loop that visits every item must do more "
         "work when there are more items"),
        ("B", "It grows in step with n — twice the items, twice the time", True, None),
        ("C", "It grows much faster than n, like n × n", False,
         "expected the cost of nested loops from a single loop"),
        ("D", "It gets smaller as the list grows", False,
         "reversed the relationship; more items cannot mean less work")]),

    _q("cs_t1_q2", "computer_science", "How Code Runs",
       "working out how long code takes",
       "A loop inside another loop, each running n times. Roughly how many "
       "steps in total?",
       [("A", "About n steps", False,
         "counted only the outer loop and missed that the inner loop restarts "
         "on every single pass"),
        ("B", "About n × n steps", True, None),
        ("C", "About n + n steps", False,
         "added the two loops instead of multiplying; the inner one runs once "
         "per outer pass, not once overall"),
        ("D", "Exactly 2 steps", False,
         "counted the loops themselves rather than the work they do")]),

    _q("cs_t1_q3", "computer_science", "How Code Runs",
       "backing up a claim with evidence",
       "Your program ran fast on a list of 10 items. What does that tell you "
       "about a list of 10,000?",
       [("A", "It will definitely still be fast", False,
         "generalised from a tiny input; slow growth and fast growth look the "
         "same at small sizes"),
        ("B", "Not much — you would need to test a bigger list", True, None),
        ("C", "It will definitely be slow", False,
         "drew the opposite conclusion, equally unsupported by one small test"),
        ("D", "Nothing at all can ever be learned from timing", False,
         "dismissed measurement entirely rather than noting its limits")]),

    _q("cs_t1_q4", "computer_science", "How Code Runs",
       "understanding what a variable holds",
       "`x = 5` then `y = x` then `x = 10`. What is `y`?",
       [("A", "10, because y follows x", False,
         "treated `y = x` as a permanent link; it copies the value at that "
         "moment and nothing after"),
        ("B", "5 — y kept the value x had at the time", True, None),
        ("C", "15, both values added", False,
         "read assignment as accumulating rather than replacing"),
        ("D", "Nothing — y is undefined", False,
         "assumed the assignment did not happen")]),

    # ------------------------------------------------ Topic 2: Lists and Loops
    _q("cs_t2_q1", "computer_science", "Lists and Loops",
       "working out how long code takes",
       "To check if a name is in an unsorted list of n names, how many do you "
       "have to look at in the worst case?",
       [("A", "Just one", False,
         "assumed the answer is found immediately; with no ordering there is "
         "no way to jump to it"),
        ("B", "All n of them", True, None),
        ("C", "About half of n, always", False,
         "gave the average rather than the worst case, which the question asked "
         "for"),
        ("D", "None — the computer just knows", False,
         "treated lookup as free rather than as work that has to happen")]),

    _q("cs_t2_q2", "computer_science", "Lists and Loops",
       "picking the right data structure",
       "You need to check 'have I seen this before?' thousands of times. What "
       "should you store the seen items in?",
       [("A", "A list, checking each item every time", False,
         "chose a structure that must be scanned end to end for a question "
         "asked thousands of times"),
        ("B", "A set — it can answer that almost instantly", True, None),
        ("C", "A single variable holding the last item", False,
         "kept only the most recent item for a question about everything seen "
         "so far"),
        ("D", "A text file, read from disk each time", False,
         "chose the slowest possible option for the most repeated operation")]),

    _q("cs_t2_q3", "computer_science", "Lists and Loops",
       "picking the right data structure",
       "You need to keep items in the order they arrived and take them out "
       "oldest first. Which fits?",
       [("A", "A stack — it takes the newest out first", False,
         "chose last-in-first-out where the question asked for oldest first"),
        ("B", "A queue", True, None),
        ("C", "A set — it keeps things tidy", False,
         "chose a structure that keeps no order at all"),
        ("D", "A single variable", False,
         "chose something that holds one item where a collection is needed")]),

    _q("cs_t2_q4", "computer_science", "Lists and Loops",
       "knowing when a loop or function stops",
       "`while count < 10:` — and nothing inside ever changes `count`. What "
       "happens?",
       [("A", "It runs 10 times and stops", False,
         "assumed the loop counts by itself; nothing increases `count` here"),
        ("B", "It never stops", True, None),
        ("C", "It runs once", False,
         "expected the condition to be checked only at the start"),
        ("D", "It refuses to run", False,
         "expected an error where the condition is true and stays true")]),

    # -------------------------------------------- Topic 3: Functions & Repeats
    _q("cs_t3_q1", "computer_science", "Functions and Repeats",
       "knowing when a loop or function stops",
       "A function calls itself every time, with no condition to stop. What "
       "happens?",
       [("A", "It returns 0", False,
         "assumed it stops on its own; nothing in it checks whether to stop"),
        ("B", "It keeps calling itself until the program crashes", True, None),
        ("C", "It runs exactly once", False,
         "missed that the call inside triggers another call, and another"),
        ("D", "The computer skips the call", False,
         "assumed the call is ignored rather than carried out")]),

    _q("cs_t3_q2", "computer_science", "Functions and Repeats",
       "knowing when a loop or function stops",
       "What does a function that calls itself need, to be sure it finishes?",
       [("A", "A comment explaining what it does", False,
         "named documentation, which does not affect what the code does"),
        ("B", "A case where it returns an answer without calling itself again", True, None),
        ("C", "At least two inputs", False,
         "named a detail of the signature, unrelated to stopping"),
        ("D", "To be short", False,
         "named length, which has no bearing on whether it terminates")]),

    _q("cs_t3_q3", "computer_science", "Functions and Repeats",
       "understanding what a variable holds",
       "A function changes a variable that was created inside it. After the "
       "function ends, the outside variable of the same name is:",
       [("A", "Changed to match", False,
         "assumed a name inside a function refers to the one outside; it is a "
         "separate variable"),
        ("B", "Unchanged", True, None),
        ("C", "Deleted", False,
         "expected the outer variable to be destroyed by an unrelated one"),
        ("D", "Doubled", False,
         "expected an arithmetic effect where there is no connection at all")]),

    _q("cs_t3_q4", "computer_science", "Functions and Repeats",
       "backing up a claim with evidence",
       "Your function works on the three examples you tried. Is it correct?",
       [("A", "Yes, definitely", False,
         "treated three passing examples as proof; they show those three work "
         "and nothing more"),
        ("B", "Those three work — others might not", True, None),
        ("C", "No, three examples prove it is broken", False,
         "read passing tests as evidence of failure"),
        ("D", "Examples tell you nothing whatsoever", False,
         "discarded real if limited evidence entirely")]),

    # ------------------------------------------ Topic 4: Storing Things (state)
    _q("cs_t4_q1", "computer_science", "Storing Things",
       "understanding what a variable holds",
       "`a = [1, 2]` then `b = a` then `b.append(3)`. What is `a` now?",
       [("A", "Still [1, 2] — b was a copy", False,
         "treated `b = a` as making a copy; both names point at the same list"),
        ("B", "[1, 2, 3] — both names point at the same list", True, None),
        ("C", "An error, lists cannot be shared", False,
         "assumed a restriction that does not exist"),
        ("D", "[1, 2, [3]]", False,
         "confused adding an item with nesting a list inside another")]),

    _q("cs_t4_q2", "computer_science", "Storing Things",
       "understanding what a variable holds",
       "To make a list you can change without affecting the original, you "
       "should:",
       [("A", "Just assign it to a new name", False,
         "assumed a new name means new data; it does not"),
        ("B", "Make an actual copy of it", True, None),
        ("C", "Rename the original", False,
         "changed what the data is called rather than making a second one"),
        ("D", "Delete the original first", False,
         "removed the data instead of duplicating it")]),

    _q("cs_t4_q3", "computer_science", "Storing Things",
       "picking the right data structure",
       "You want to look something up by name — like a phone book. Best fit?",
       [("A", "A list of names only", False,
         "stored the keys with nowhere to put the values they map to"),
        ("B", "A dictionary, mapping each name to its number", True, None),
        ("C", "Two separate lists you keep in the same order", False,
         "chose a structure that works until one list is edited and the two "
         "silently fall out of step"),
        ("D", "One long piece of text", False,
         "chose a format with no lookup structure at all")]),

    _q("cs_t4_q4", "computer_science", "Storing Things",
       "picking the right data structure",
       "Why is looking something up in a dictionary usually faster than "
       "searching a list?",
       [("A", "Dictionaries are always smaller", False,
         "explained the speed by size; it holds whatever the size"),
        ("B", "It can jump straight to the right place instead of checking "
              "each item", True, None),
        ("C", "Dictionaries are sorted alphabetically", False,
         "attributed the speed to ordering, which a dictionary does not "
         "maintain"),
        ("D", "Lists are broken", False,
         "treated a list as faulty rather than as suited to a different job")]),

    # --------------------------------------------- Topic 5: Getting It Right
    _q("cs_t5_q1", "computer_science", "Getting It Right",
       "backing up a claim with evidence",
       "Someone says 'my code is fast'. What would actually back that up?",
       [("A", "It felt quick when they ran it", False,
         "offered an impression where a timing claim needs a measurement"),
        ("B", "A measured time, on a stated input size", True, None),
        ("C", "It is short code", False,
         "used length as a proxy for speed; they are unrelated"),
        ("D", "It has no comments", False,
         "named a style detail with no bearing on speed")]),

    _q("cs_t5_q2", "computer_science", "Getting It Right",
       "backing up a claim with evidence",
       "Your code crashes only sometimes. The most useful next step is:",
       [("A", "Run it again and hope", False,
         "repeated the action without gathering anything new"),
        ("B", "Find out exactly what input makes it crash", True, None),
        ("C", "Rewrite the whole thing", False,
         "discarded working code before knowing what was wrong with it"),
        ("D", "Add more comments", False,
         "changed documentation, which cannot affect behaviour")]),

    _q("cs_t5_q3", "computer_science", "Getting It Right",
       "working out how long code takes",
       "Your program is too slow. Where should you look first?",
       [("A", "The shortest function, it is easiest to read", False,
         "chose by convenience rather than by where the time is going"),
        ("B", "The part that runs the most times", True, None),
        ("C", "The first line of the file", False,
         "chose by position in the file, which says nothing about cost"),
        ("D", "The comments", False,
         "looked at text the computer never runs")]),

    _q("cs_t5_q4", "computer_science", "Getting It Right",
       "knowing when a loop or function stops",
       "A loop is meant to stop when it finds an item, but never does. Most "
       "likely:",
       [("A", "The list is too long", False,
         "blamed the data size; a loop that finds its item stops whatever the "
         "length"),
        ("B", "The stopping condition is never actually true", True, None),
        ("C", "The computer is slow", False,
         "attributed a logic problem to hardware"),
        ("D", "Loops cannot stop early", False,
         "assumed a limitation that does not exist")]),
]


# ==================================================================== ROBOTICS
# Same design. Five topics, five concepts, each spread across three or four
# questions in different topics. Theory a second-year has met, no postgraduate
# material.

ROBO: list[Question] = [
    # --------------------------------------------------- Topic 1: How It Moves
    _q("rb_t1_q1", "robotics", "How It Moves",
       "working out where the robot ends up",
       "You know every joint angle of a robot arm. Can you work out where the "
       "hand ends up?",
       [("A", "No, that is impossible to calculate", False,
         "treated a direct calculation as impossible; the angles and link "
         "lengths fully determine the position"),
        ("B", "Yes — the angles and link lengths give exactly one answer", True, None),
        ("C", "Only if the arm has two joints", False,
         "imposed a limit on joint count that does not exist"),
        ("D", "Only by measuring it with a camera", False,
         "required a sensor for something the geometry already answers")]),

    _q("rb_t1_q2", "robotics", "How It Moves",
       "working out where the robot ends up",
       "You know where you WANT the hand to be, and need the joint angles. "
       "This is usually:",
       [("A", "Easier than the other direction", False,
         "reversed the difficulty; going backwards from a position is the "
         "harder problem"),
        ("B", "Harder — there can be several ways to reach the same spot", True, None),
        ("C", "Impossible", False,
         "treated a solvable problem as having no answer"),
        ("D", "The same calculation, run backwards", False,
         "assumed the forward calculation simply reverses; it does not")]),

    _q("rb_t1_q3", "robotics", "How It Moves",
       "combining movements in the right order",
       "Turn 90° then walk forward 1m, versus walk forward 1m then turn 90°. "
       "Same end position?",
       [("A", "Yes, always the same", False,
         "assumed order does not matter; turning first points the walk in a "
         "different direction"),
        ("B", "No — the order changes where you end up", True, None),
        ("C", "Only if the robot is small", False,
         "made the outcome depend on size, which is irrelevant"),
        ("D", "Only for wheeled robots", False,
         "restricted to one robot type a rule that applies generally")]),

    _q("rb_t1_q4", "robotics", "How It Moves",
       "combining movements in the right order",
       "A robot's position is given in the map's frame. To use it in the "
       "robot's own frame you need:",
       [("A", "Nothing, they are the same thing", False,
         "treated two different frames as interchangeable"),
        ("B", "To convert between the two frames", True, None),
        ("C", "To restart the robot", False,
         "proposed an action unrelated to the coordinate question"),
        ("D", "A bigger map", False,
         "changed the map size rather than converting between frames")]),

    # ------------------------------------------------- Topic 2: Keeping Steady
    _q("rb_t2_q1", "robotics", "Keeping Steady",
       "matching a fix to what went wrong",
       "A robot arm keeps stopping just short of where you told it to go. "
       "This means:",
       [("A", "It is moving too fast", False,
         "named speed, which does not explain a consistent shortfall at rest"),
        ("B", "There is a small leftover error the controller is not "
              "correcting", True, None),
        ("C", "The target is wrong", False,
         "blamed the goal rather than the response falling short of it"),
        ("D", "The battery is flat", False,
         "named a power fault where the arm is moving, just not far enough")]),

    _q("rb_t2_q2", "robotics", "Keeping Steady",
       "matching a fix to what went wrong",
       "A robot overshoots its target, comes back, overshoots again, and wobbles. "
       "Most likely:",
       [("A", "It is not trying hard enough", False,
         "read overshoot as too little effort; it is a sign of too much"),
        ("B", "It is correcting too strongly", True, None),
        ("C", "The target moved", False,
         "blamed the goal for a pattern caused by the response"),
        ("D", "The sensors are too accurate", False,
         "treated good measurement as a cause of wobble")]),

    _q("rb_t2_q3", "robotics", "Keeping Steady",
       "backing a claim with a measurement",
       "A robot reacts slowly because its sensor readings arrive late. This "
       "delay makes control:",
       [("A", "Easier — it has more time to think", False,
         "treated delay as helpful; corrections based on old information arrive "
         "too late to fit the situation"),
        ("B", "Harder — it is correcting based on out-of-date information", True, None),
        ("C", "Unaffected", False,
         "assumed timing does not matter to a feedback loop"),
        ("D", "Perfect", False,
         "treated a known problem as an improvement")]),

    _q("rb_t2_q4", "robotics", "Keeping Steady",
       "backing a claim with a measurement",
       "'The robot is well tuned.' What would actually show that?",
       [("A", "It looked smooth once", False,
         "offered a single impression where a tuning claim needs numbers"),
        ("B", "Measured overshoot and settling time against a target", True, None),
        ("C", "The settings match a textbook", False,
         "cited values chosen for a different machine instead of this one's "
         "measured behaviour"),
        ("D", "It has not broken yet", False,
         "offered absence of failure as evidence of good performance")]),

    # ------------------------------------------------- Topic 3: Knowing Where
    _q("rb_t3_q1", "robotics", "Knowing Where It Is",
       "choosing a method for the job",
       "Wheel counters say the robot travelled 10m; GPS says 9m. The best "
       "approach is:",
       [("A", "Always believe the wheels", False,
         "trusted one source completely; wheels slip and the error builds up"),
        ("B", "Combine both, leaning on whichever is more reliable here", True, None),
        ("C", "Always believe GPS", False,
         "trusted one source completely in the other direction"),
        ("D", "Ignore both and guess", False,
         "discarded two imperfect but real measurements")]),

    _q("rb_t3_q2", "robotics", "Knowing Where It Is",
       "backing a claim with a measurement",
       "Counting wheel turns to track position goes wrong over time mainly "
       "because:",
       [("A", "The wheels get tired", False,
         "gave a non-physical reason"),
        ("B", "Small errors from slipping add up and never get corrected", True, None),
        ("C", "The robot forgets", False,
         "described memory loss rather than accumulating measurement error"),
        ("D", "It only works indoors", False,
         "named a location limit rather than the drift mechanism")]),

    _q("rb_t3_q3", "robotics", "Knowing Where It Is",
       "working out where the robot ends up",
       "A robot knows it is exactly 5m from one landmark. Does it know where "
       "it is?",
       [("A", "Yes, precisely", False,
         "treated one distance as fixing a position; it leaves a whole circle "
         "of possibilities"),
        ("B", "No — it could be anywhere on a circle around that landmark", True, None),
        ("C", "It knows nothing at all", False,
         "discarded a real constraint as worthless"),
        ("D", "Only if the landmark is moving", False,
         "made the answer depend on something that would make it harder")]),

    _q("rb_t3_q4", "robotics", "Knowing Where It Is",
       "backing a claim with a measurement",
       "The strongest evidence that a robot's position estimate is drifting:",
       [("A", "It looks a bit off", False,
         "offered an impression where the claim is about error growing over "
         "time"),
        ("B", "The gap from a known reference grows the further it travels", True, None),
        ("C", "The wheels look worn", False,
         "named a possible cause and offered it in place of the observation"),
        ("D", "The map is old", False,
         "named a property of the map rather than of the estimate")]),

    # ------------------------------------------------- Topic 4: Finding a Path
    _q("rb_t4_q1", "robotics", "Finding a Path",
       "choosing a method for the job",
       "A path-finding method that always gives the shortest route, if one "
       "exists, is described as:",
       [("A", "Fast", False,
         "named speed, which is a separate property from what it guarantees"),
        ("B", "Guaranteed to find the best path", True, None),
        ("C", "Random", False,
         "named an approach that gives no such guarantee"),
        ("D", "Simple", False,
         "named ease of writing rather than what it promises")]),

    _q("rb_t4_q2", "robotics", "Finding a Path",
       "choosing a method for the job",
       "A method that tries random points and usually finds a path eventually:",
       [("A", "Always finds the shortest path", False,
         "confused finding a path with finding the best one"),
        ("B", "May find a path, but not necessarily the shortest", True, None),
        ("C", "Never works", False,
         "dismissed a method that does work, just without an optimality "
         "guarantee"),
        ("D", "Is the same as checking every option", False,
         "equated sampling with exhaustive search")]),

    _q("rb_t4_q3", "robotics", "Finding a Path",
       "accounting for weight and force",
       "You split a map into squares to search it. If you halve the square "
       "size, the number of squares:",
       [("A", "Halves", False,
         "reversed the relationship; smaller squares means more of them"),
        ("B", "Goes up a lot — roughly four times, on a flat map", True, None),
        ("C", "Stays the same", False,
         "treated the count as independent of the square size"),
        ("D", "Doubles", False,
         "applied the factor once, though it applies along both width and "
         "height")]),

    _q("rb_t4_q4", "robotics", "Finding a Path",
       "combining movements in the right order",
       "A planned path is a list of points in the map. To follow it, the robot "
       "must:",
       [("A", "Ignore its own position", False,
         "dropped the information needed to know where to go next"),
        ("B", "Work out where each point is relative to itself", True, None),
        ("C", "Plan a completely new path", False,
         "discarded a valid plan instead of using it"),
        ("D", "Drive in a straight line regardless", False,
         "ignored the path that was just planned")]),

    # ------------------------------------------- Topic 5: Weight and Force
    _q("rb_t5_q1", "robotics", "Weight and Force",
       "accounting for weight and force",
       "Planning a robot arm's path using only geometry ignores:",
       [("A", "The joint angles", False,
         "named the very thing geometry is built from"),
        ("B", "Its weight, and the force needed to move it", True, None),
        ("C", "The link lengths", False,
         "named another geometric quantity that is included"),
        ("D", "Time completely", False,
         "overstated it; geometry handles positions over time, just not the "
         "forces behind them")]),

    _q("rb_t5_q2", "robotics", "Weight and Force",
       "matching a fix to what went wrong",
       "A robot arm follows a slow path well but a fast one badly. Most likely "
       "because:",
       [("A", "The path is the wrong shape", False,
         "blamed the geometry, though the same path worked slowly"),
        ("B", "Moving fast needs more force than was planned for", True, None),
        ("C", "The motors switch off at speed", False,
         "described a fault rather than the effect of speed on the force needed"),
        ("D", "Fast paths are always impossible", False,
         "treated a tuning and modelling problem as a hard limit")]),

    _q("rb_t5_q3", "robotics", "Weight and Force",
       "accounting for weight and force",
       "Holding a heavy arm still against gravity needs:",
       [("A", "No effort, it just stays there", False,
         "assumed a held position is free; gravity pulls on it continuously"),
        ("B", "A constant push from the motors", True, None),
        ("C", "Effort only while it is moving", False,
         "assumed force is needed only for motion, not for holding"),
        ("D", "The arm to be switched off", False,
         "removed the force that is holding it up")]),

    _q("rb_t5_q4", "robotics", "Weight and Force",
       "backing a claim with a measurement",
       "Your model says the arm needs 5 units of force; in reality it needs 7. "
       "The sensible response:",
       [("A", "Insist the model is right", False,
         "kept the model over the measurement, which is how a wrong model "
         "survives"),
        ("B", "Treat the model as approximate and correct for the difference", True, None),
        ("C", "Ignore the reading", False,
         "discarded the measurement that revealed the gap"),
        ("D", "Never use models again", False,
         "abandoned a useful approximation over one known error")]),
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
