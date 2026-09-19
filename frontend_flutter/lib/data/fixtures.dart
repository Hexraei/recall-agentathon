import '../models/models.dart';

/// Placeholder content matching what the canvas draws.
///
/// Two inconsistencies in the artboards are corrected here rather than
/// copied: the canvas listed six questions for a fifteen-question quiz, and
/// screen 8's topic mean did not reconcile with its score distribution. The
/// fixtures below are internally consistent so the screens that share data
/// agree with each other.
class Fixtures {
  Fixtures._();

  static const teacher = AppUser(
    id: 't1',
    name: 'Anita Raghavan',
    role: UserRole.teacher,
  );

  static const student = AppUser(
    id: 's1',
    name: 'Nithya Prasad',
    role: UserRole.student,
    rollNumber: '2021CS042',
  );

  static const classSize = 42;

  static const roster = <AppUser>[
    AppUser(
      id: 's1',
      name: 'Nithya Prasad',
      role: UserRole.student,
      rollNumber: '2021CS042',
    ),
    AppUser(
      id: 's2',
      name: 'Divya Krishnan',
      role: UserRole.student,
      rollNumber: '2021CS011',
    ),
    AppUser(
      id: 's3',
      name: 'Arjun Menon',
      role: UserRole.student,
      rollNumber: '2021CS004',
    ),
    AppUser(
      id: 's4',
      name: 'Kavya Rao',
      role: UserRole.student,
      rollNumber: '2021CS023',
    ),
    AppUser(
      id: 's5',
      name: 'Rahul Iyer',
      role: UserRole.student,
      rollNumber: '2021CS051',
    ),
    AppUser(
      id: 's6',
      name: 'Sneha Balaji',
      role: UserRole.student,
      rollNumber: '2021CS058',
    ),
    AppUser(
      id: 's7',
      name: 'Vikram Shetty',
      role: UserRole.student,
      rollNumber: '2021CS067',
    ),
    AppUser(
      id: 's8',
      name: 'Meera Nair',
      role: UserRole.student,
      rollNumber: '2021CS036',
    ),
    AppUser(
      id: 's9',
      name: 'Karthik Subramanian',
      role: UserRole.student,
      rollNumber: '2021CS029',
    ),
    AppUser(
      id: 's10',
      name: 'Priya Venkat',
      role: UserRole.student,
      rollNumber: '2021CS047',
    ),
  ];

  /// The topic vocabulary the builder combobox filters against.
  static const knownTopics = <String>[
    'Hashing',
    'Collisions',
    'Load factor',
    'Traversal',
    'Representation',
    'Shortest paths',
    'Base cases',
    'Call stack',
    'Recurrence',
    'Complexity',
  ];

  // ------------------------------------------------------------ hash tables
  static final hashTables = Quiz(
    id: 'q-hash',
    title: 'Hash tables',
    week: 'Week 8',
    timeLimitMinutes: 20,
    lastRun: DateTime(2025, 9, 16, 10, 42),
    closedAt: DateTime(2025, 9, 16, 11, 2),
    pin: '408 217',
    questions: _hashQuestions,
  );

  static final _hashQuestions = <Question>[
    const Question(
      id: 'h1',
      text: 'What does a hash function map a key to?',
      topic: 'Hashing',
      options: [
        'A slot index in the table',
        'A sorted position in an array',
        'A pointer to the previous key',
        'A unique memory address',
      ],
      correctIndex: 0,
    ),
    const Question(
      id: 'h2',
      text: 'Two distinct keys hash to the same slot. What has happened?',
      topic: 'Collisions',
      options: [
        'The table has overflowed',
        'A collision',
        'The hash function has failed',
        'The load factor has exceeded one',
      ],
      correctIndex: 1,
    ),
    const Question(
      id: 'h3',
      text: 'In separate chaining, what does each slot hold?',
      topic: 'Collisions',
      options: [
        'Exactly one key',
        'A list of the keys that hashed there',
        'The next free slot index',
        'A copy of the hash function',
      ],
      correctIndex: 1,
    ),
    const Question(
      id: 'h4',
      text: 'What is the load factor of a hash table?',
      topic: 'Load factor',
      options: [
        'Keys divided by slots',
        'Slots divided by keys',
        'Collisions divided by keys',
        'The longest chain length',
      ],
      correctIndex: 0,
    ),
    const Question(
      id: 'h5',
      text:
          'Lookup in a chained hash table degrades to linear time when what is true?',
      topic: 'Collisions',
      options: [
        'The table is more than half empty',
        'The keys are already sorted',
        'Every key hashes to the same slot',
        'The hash function is deterministic',
      ],
      correctIndex: 2,
    ),
    const Question(
      id: 'h6',
      text:
          'Why is a table resized once the load factor grows past a threshold?',
      topic: 'Load factor',
      options: [
        'To keep the average chain short',
        'To free unused memory',
        'To re-sort the keys',
        'To change the hash function',
      ],
      correctIndex: 0,
    ),
    const Question(
      id: 'h7',
      text: 'What must happen to every existing key when a table is resized?',
      topic: 'Load factor',
      options: [
        'Nothing; the slots are copied across',
        'It is rehashed against the new table size',
        'It is discarded and reinserted by the caller',
        'It is moved to an overflow table',
      ],
      correctIndex: 1,
    ),
    const Question(
      id: 'h8',
      text:
          'In open addressing with linear probing, where does a key go if its slot is taken?',
      topic: 'Collisions',
      options: [
        'Into a chain hanging off that slot',
        'Into the next slot along, wrapping at the end',
        'Back to the caller as an error',
        'Into a second table',
      ],
      correctIndex: 1,
    ),
    const Question(
      id: 'h9',
      text: 'What makes a hash function good for a hash table?',
      topic: 'Hashing',
      options: [
        'It spreads keys evenly across the slots',
        'It never produces the same value twice',
        'It preserves the order of the keys',
        'It is slow enough to be secure',
      ],
      correctIndex: 0,
    ),
    const Question(
      id: 'h10',
      text:
          'What is the average-case cost of a lookup in a well-sized hash table?',
      topic: 'Complexity',
      options: ['O(1)', 'O(log n)', 'O(n)', 'O(n log n)'],
      correctIndex: 0,
    ),
    const Question(
      id: 'h11',
      text: 'What is the worst-case cost of a lookup in a chained hash table?',
      topic: 'Complexity',
      options: ['O(1)', 'O(log n)', 'O(n)', 'O(n squared)'],
      correctIndex: 2,
    ),
    const Question(
      id: 'h12',
      text:
          'Why can a hash table not answer "give me the smallest key" quickly?',
      topic: 'Hashing',
      options: [
        'It stores no ordering between keys',
        'It only stores values, not keys',
        'It would need to rehash first',
        'Its keys are immutable',
      ],
      correctIndex: 0,
    ),
    const Question(
      id: 'h13',
      text: 'Deleting from an open-addressed table needs what, and why?',
      topic: 'Collisions',
      options: [
        'Nothing special; the slot is cleared',
        'A tombstone, so probe sequences are not cut short',
        'A full rehash on every delete',
        'The chain to be reversed',
      ],
      correctIndex: 1,
    ),
    const Question(
      id: 'h14',
      text: 'A table has 100 slots and 75 keys. What is its load factor?',
      topic: 'Load factor',
      options: ['0.25', '0.75', '1.33', '75'],
      correctIndex: 1,
    ),
    const Question(
      id: 'h15',
      text: 'Which claim about a hash table is false?',
      topic: 'Hashing',
      options: [
        'Lookup is constant time on average',
        'Keys are stored in sorted order',
        'Collisions must be handled somehow',
        'Resizing rehashes every key',
      ],
      correctIndex: 1,
    ),
  ];

  // ----------------------------------------------------------------- graphs
  static final graphs = Quiz(
    id: 'q-graphs',
    title: 'Graphs',
    week: 'Week 9',
    timeLimitMinutes: 20,
    lastRun: DateTime(2025, 9, 16, 11, 4),
    closedAt: DateTime(2025, 9, 16, 11, 24),
    questions: _graphQuestions,
  );

  static final _graphQuestions = <Question>[
    const Question(
      id: 'g1',
      text: 'Which traversal of a graph uses a queue?',
      topic: 'Traversal',
      options: [
        'Depth-first search',
        'Breadth-first search',
        'Topological sort',
        'Prim to the minimum spanning tree',
      ],
      correctIndex: 1,
    ),
    const Question(
      id: 'g2',
      text:
          'A graph with 8 vertices has 7 edges and no cycles. What must be true of it?',
      topic: 'Representation',
      options: [
        'It is a tree',
        'It is a complete graph',
        'It has exactly one vertex of degree 7',
        'It is disconnected',
      ],
      correctIndex: 0,
    ),
    const Question(
      id: 'g3',
      text: 'What does a topological sort require of the graph?',
      topic: 'Traversal',
      options: [
        'That it is undirected',
        'That it is connected',
        'That every edge has a weight',
        'That it is directed and acyclic',
      ],
      correctIndex: 3,
    ),
    const Question(
      id: 'g4',
      text: 'In an adjacency list, what does each entry hold?',
      topic: 'Representation',
      options: [
        'A row of the adjacency matrix',
        'The neighbours of one vertex',
        'The weight of one edge',
        'The degree of one vertex',
      ],
      correctIndex: 1,
    ),
    const Question(
      id: 'g5',
      text: 'Which algorithm finds shortest paths with non-negative weights?',
      topic: 'Shortest paths',
      options: [
        'Bellman-Ford',
        'Kruskal',
        "Dijkstra's algorithm",
        'Depth-first search',
      ],
      correctIndex: 2,
    ),
    const Question(
      id: 'g6',
      text: 'When is Bellman-Ford preferred over Dijkstra?',
      topic: 'Shortest paths',
      options: [
        'When the graph is very dense',
        'When some edge weights are negative',
        'When the graph is a tree',
        'When only one source is needed',
      ],
      correctIndex: 1,
    ),
    const Question(
      id: 'g7',
      text: 'How much space does an adjacency matrix take for n vertices?',
      topic: 'Representation',
      options: ['O(n)', 'O(n log n)', 'O(n squared)', 'O(edges)'],
      correctIndex: 2,
    ),
    const Question(
      id: 'g8',
      text:
          'Which traversal naturally finds the fewest-edge path in an unweighted graph?',
      topic: 'Traversal',
      options: [
        'Breadth-first search',
        'Depth-first search',
        'Either, they agree',
        'Neither, a shortest-path algorithm is needed',
      ],
      correctIndex: 0,
    ),
    const Question(
      id: 'g9',
      text: 'What does it mean for a directed graph to be strongly connected?',
      topic: 'Representation',
      options: [
        'Every vertex has the same degree',
        'Every pair of vertices is reachable from the other',
        'It has no cycles',
        'It has exactly one component when edges are ignored',
      ],
      correctIndex: 1,
    ),
    const Question(
      id: 'g10',
      text: 'Dijkstra visits vertices in what order?',
      topic: 'Shortest paths',
      options: [
        'In the order they were inserted',
        'By increasing distance from the source',
        'By decreasing degree',
        'In depth-first order',
      ],
      correctIndex: 1,
    ),
    const Question(
      id: 'g11',
      text:
          'How is a cycle detected during a depth-first search of a directed graph?',
      topic: 'Traversal',
      options: [
        'By finding an edge back to a vertex still on the stack',
        'By counting the edges',
        'By finding any visited vertex',
        'By comparing in-degree to out-degree',
      ],
      correctIndex: 0,
    ),
    const Question(
      id: 'g12',
      text: 'What is the sum of all vertex degrees in an undirected graph?',
      topic: 'Representation',
      options: [
        'The number of edges',
        'Twice the number of edges',
        'The number of vertices',
        'The number of components',
      ],
      correctIndex: 1,
    ),
    const Question(
      id: 'g13',
      text: 'Which structure does Dijkstra use to pick the next vertex?',
      topic: 'Shortest paths',
      options: ['A stack', 'A queue', 'A priority queue', 'A hash table'],
      correctIndex: 2,
    ),
    const Question(
      id: 'g14',
      text: 'A depth-first search on a disconnected graph reaches what?',
      topic: 'Traversal',
      options: [
        'Every vertex',
        'Only the component it started in',
        'Only the vertices with even degree',
        'Nothing, it fails',
      ],
      correctIndex: 1,
    ),
    const Question(
      id: 'g15',
      text: 'Which pair of weights would make a shortest path undefined?',
      topic: 'Shortest paths',
      options: [
        'All weights zero',
        'All weights equal',
        'A negative cycle on the path',
        'Weights larger than the vertex count',
      ],
      correctIndex: 2,
    ),
  ];

  // -------------------------------------------------------------- recursion
  static final recursion = Quiz(
    id: 'q-recursion',
    title: 'Recursion',
    week: 'Week 6',
    timeLimitMinutes: 15,
    lastRun: DateTime(2025, 9, 16, 9, 10),
    closedAt: DateTime(2025, 9, 16, 9, 25),
    questions: _recursionQuestions,
  );

  static final _recursionQuestions = <Question>[
    const Question(
      id: 'r1',
      text: 'What does every terminating recursion need?',
      topic: 'Base cases',
      options: [
        'A base case',
        'A loop',
        'A global counter',
        'A return type of void',
      ],
      correctIndex: 0,
    ),
    const Question(
      id: 'r2',
      text: 'What happens when a recursive call never reaches its base case?',
      topic: 'Call stack',
      options: [
        'The compiler rejects it',
        'The call stack overflows',
        'It returns null',
        'It silently returns the last value',
      ],
      correctIndex: 1,
    ),
    const Question(
      id: 'r3',
      text: 'A frame is pushed onto the call stack when what happens?',
      topic: 'Call stack',
      options: [
        'A function returns',
        'A function is called',
        'A variable is declared',
        'The base case is reached',
      ],
      correctIndex: 1,
    ),
    const Question(
      id: 'r4',
      text: 'What recurrence describes the naive Fibonacci definition?',
      topic: 'Recurrence',
      options: [
        'T(n) = T(n-1) + 1',
        'T(n) = 2T(n/2) + n',
        'T(n) = T(n-1) + T(n-2) + 1',
        'T(n) = T(n/2) + 1',
      ],
      correctIndex: 2,
    ),
    const Question(
      id: 'r5',
      text: 'Tracing a recursive call stack, which frame returns first?',
      topic: 'Call stack',
      options: [
        'The outermost call',
        'The deepest call',
        'Whichever was called first',
        'They all return together',
      ],
      correctIndex: 1,
    ),
    const Question(
      id: 'r6',
      text: 'What is the cost of naive recursive Fibonacci?',
      topic: 'Recurrence',
      options: ['O(n)', 'O(n log n)', 'Exponential in n', 'O(1)'],
      correctIndex: 2,
    ),
    const Question(
      id: 'r7',
      text: 'What does tail recursion allow a compiler to do?',
      topic: 'Call stack',
      options: [
        'Reuse the current stack frame',
        'Skip the base case',
        'Run the calls in parallel',
        'Cache every result',
      ],
      correctIndex: 0,
    ),
    const Question(
      id: 'r8',
      text: 'Why does memoisation speed up recursive Fibonacci?',
      topic: 'Recurrence',
      options: [
        'It removes the base case',
        'It computes each subproblem once',
        'It makes the stack shallower than one frame',
        'It converts the code to a loop',
      ],
      correctIndex: 1,
    ),
    const Question(
      id: 'r9',
      text:
          'How many base cases does a recursion over two shrinking arguments usually need?',
      topic: 'Base cases',
      options: [
        'Exactly one',
        'One per argument that can bottom out',
        'None, if the arguments shrink',
        'One per recursive call',
      ],
      correctIndex: 1,
    ),
    const Question(
      id: 'r10',
      text: 'Which of these is not a valid base case for a factorial?',
      topic: 'Base cases',
      options: [
        'n equals 0 returns 1',
        'n equals 1 returns 1',
        'n less than 0 raises an error',
        'n equals n returns n',
      ],
      correctIndex: 3,
    ),
  ];

  static final allQuizzes = <Quiz>[graphs, hashTables, recursion];
}
