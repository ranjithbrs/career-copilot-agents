"""
Standard High-Yield Curricula for Software Engineering Placements.
Covers DSA, Python Internals, and SQL.
"""

CURRICULUM = {
    "DSA": [
        {
            "topic": "Arrays & Hashing",
            "problems": ["Two Sum (LeetCode #1)", "Group Anagrams (LeetCode #49)", "Top K Frequent Elements (LeetCode #347)"]
        },
        {
            "topic": "Two Pointers & Sliding Window",
            "problems": ["3Sum (LeetCode #15)", "Longest Substring Without Repeating Characters (LeetCode #3)", "Trapping Rain Water (LeetCode #42)"]
        },
        {
            "topic": "Binary Search",
            "problems": ["Binary Search (LeetCode #704)", "Search in Rotated Sorted Array (LeetCode #33)", "Koko Eating Bananas (LeetCode #875)"]
        },
        {
            "topic": "Trees & Binary Search Trees",
            "problems": ["Lowest Common Ancestor of a BST (LeetCode #235)", "Binary Tree Level Order Traversal (LeetCode #102)", "Serialize and Deserialize Binary Tree (LeetCode #297)"]
        },
        {
            "topic": "Graphs (BFS, DFS, TopoSort)",
            "problems": ["Number of Islands (LeetCode #200)", "Course Schedule (LeetCode #207)", "Rotting Oranges (LeetCode #994)"]
        },
        {
            "topic": "Dynamic Programming",
            "problems": ["Climbing Stairs (LeetCode #70)", "Coin Change (LeetCode #322)", "Longest Increasing Subsequence (LeetCode #300)"]
        }
    ],
    "PYTHON": [
        {
            "topic": "Decorators, Closures, and Wrappers",
            "problems": ["Build a timing & logging decorator", "Build a memoization cache decorator with TTL"]
        },
        {
            "topic": "Generators, Iterators, and Yield",
            "problems": ["Implement custom chunking generator for large files", "Write an infinite Fibonacci generator"]
        },
        {
            "topic": "Asyncio & Event Loops",
            "problems": ["Build an async concurrent HTTP fetcher with semaphore rate limiting", "Explain asyncio vs threading"]
        },
        {
            "topic": "Concurrency: Multiprocessing, Threading & GIL",
            "problems": ["Implement CPU-bound parallel processing with ProcessPoolExecutor", "Thread synchronization with Lock"]
        }
    ],
    "SQL": [
        {
            "topic": "Window Functions (ROW_NUMBER, RANK, DENSE_RANK)",
            "problems": ["Find the top 3 highest-earning employees per department", "Calculate month-over-month revenue growth using LAG()"]
        },
        {
            "topic": "Common Table Expressions (CTEs) & Recursive Queries",
            "problems": ["Generate organizational hierarchy tree using RECURSIVE CTE", "Multi-stage data transformation with chained CTEs"]
        },
        {
            "topic": "Indexing & Query Optimization",
            "problems": ["Explain B+ Tree vs Hash indexes", "Analyze query bottleneck using EXPLAIN plan"]
        }
    ]
}
