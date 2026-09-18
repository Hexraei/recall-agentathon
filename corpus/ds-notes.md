# Data Structures — Complexity Analysis (course notes)

## Counting work in a loop

The running time of a loop is not the number of times the loop header runs. It
is the number of times the loop header runs multiplied by the work done in the
body on each pass. A loop that runs n times and does constant work each pass is
O(n). A loop that runs n times and does work proportional to n each pass is
O(n^2).

The most common error in this topic is to count only the outer loop and report
its count as the growth rate, without asking what the body costs. Always ask two
questions, in this order: how many times does this run, and what does it cost
each time.

## Nested loops

When one loop sits inside another, multiply. An outer loop running n times
around an inner loop running n times is n * n passes through the inner body.

Insertion sort is the standard example. The outer loop visits each of the n
elements once. For each of those, the inner loop shifts elements to the right
until the correct position is found, and in the worst case that is up to n
shifts. The worst case is therefore O(n^2). On an already-sorted input the inner
loop does no shifting at all and the cost falls to O(n); insertion sort is
therefore O(n) in the best case and O(n^2) in the worst.

Insertion sort is not the fastest sorting algorithm in general. It is
competitive on small or nearly-sorted inputs, and worse than merge sort or
quicksort on large unsorted ones. Any claim that one algorithm is fastest "for
all inputs" should be treated as false until the input distribution is stated.

## Hidden work inside library operations

A loop body that calls another operation costs whatever that operation costs.
The expression `x not in result` is not constant time on a list: it scans the
list until it finds a match or reaches the end, which is O(k) for a list of
length k.

Removing duplicates by building a result list and testing `if x not in result`
for each of n elements therefore costs O(n^2) in the worst case, not O(n), even
though only one loop is visible in the code. The second loop is inside the
membership test. Using a set for the membership test makes each test O(1) on
average and brings the whole operation down to O(n).

## Halving, and logarithmic growth

Not every loop is linear. What decides the growth rate is how the remaining
problem changes on each pass.

Binary search examines the middle element of a sorted array and discards half of
the remaining range each time. Starting from n elements the range becomes n/2,
then n/4, then n/8, and the loop ends when one element is left. The number of
passes is therefore the number of times n can be halved before reaching 1, which
is log base 2 of n. Binary search is O(log n).

The presence of a loop tells you nothing about the growth rate on its own. A
loop that removes one element per pass is O(n); a loop that removes half the
remaining elements per pass is O(log n). The question is always how much of the
problem is eliminated on each pass, not whether a loop is present.
