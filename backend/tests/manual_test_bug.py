"""
Manual test script to demonstrate the MAX_RESULTS=0 bug

This script tests the vector store search functionality with the current configuration
and demonstrates how MAX_RESULTS=0 causes "No relevant content found" errors.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from vector_store import VectorStore

def test_max_results_bug():
    """Test that demonstrates the MAX_RESULTS=0 bug"""

    print("="* 60)
    print("TESTING MAX_RESULTS BUG")
    print("="* 60)

    # Show current configuration
    print(f"\nCurrent MAX_RESULTS setting: {config.MAX_RESULTS}")
    print(f"ChromaDB path: {config.CHROMA_PATH}")

    # Create vector store with current config
    vector_store = VectorStore(
        chroma_path=config.CHROMA_PATH,
        embedding_model=config.EMBEDDING_MODEL,
        max_results=config.MAX_RESULTS
    )

    print(f"\nVector store max_results: {vector_store.max_results}")

    # Check if any courses exist
    course_count = vector_store.get_course_count()
    print(f"Number of courses in database: {course_count}")

    if course_count == 0:
        print("\n⚠️  No courses found in database. Please run the app first to load documents.")
        return

    course_titles = vector_store.get_existing_course_titles()
    print(f"\nCourses in database:")
    for title in course_titles:
        print(f"  - {title}")

    # Try a search that should return results
    print(f"\n{'='* 60}")
    print("TEST 1: Searching for 'artificial intelligence'")
    print(f"{'='* 60}")

    results = vector_store.search(query="artificial intelligence")

    print(f"\nSearch completed:")
    print(f"  - Error: {results.error}")
    print(f"  - Number of results: {len(results.documents)}")
    print(f"  - Is empty: {results.is_empty()}")

    if results.error:
        print(f"\n❌ ERROR: {results.error}")
    elif results.is_empty():
        print(f"\n❌ BUG CONFIRMED: Got 0 results even though {course_count} courses exist!")
        print(f"\n🔍 ROOT CAUSE: MAX_RESULTS is set to {config.MAX_RESULTS}")
        print(f"   This causes ChromaDB query to request n_results={vector_store.max_results}")
        print(f"   which returns zero documents.")
    else:
        print(f"\n✅ Search returned {len(results.documents)} results:")
        for i, (doc, meta) in enumerate(zip(results.documents[:2], results.metadata[:2])):
            print(f"\n  Result {i+1}:")
            print(f"    Course: {meta.get('course_title', 'unknown')}")
            print(f"    Lesson: {meta.get('lesson_number', 'N/A')}")
            print(f"    Content: {doc[:100]}...")

    # Test with explicit limit
    print(f"\n{'='* 60}")
    print("TEST 2: Searching with explicit limit=5")
    print(f"{'='* 60}")

    results2 = vector_store.search(query="artificial intelligence", limit=5)

    print(f"\nSearch completed:")
    print(f"  - Number of results: {len(results2.documents)}")

    if results2.is_empty():
        print(f"\n⚠️  Still got 0 results even with explicit limit")
    else:
        print(f"\n✅ With explicit limit, got {len(results2.documents)} results!")
        print(f"   This confirms the bug is in the default MAX_RESULTS=0 value.")

    print(f"\n{'='* 60}")
    print("CONCLUSION")
    print(f"{'='* 60}")

    if config.MAX_RESULTS == 0:
        print("\n❌ BUG CONFIRMED:")
        print(f"   config.MAX_RESULTS = {config.MAX_RESULTS}")
        print(f"   This causes all searches without explicit limits to return 0 results.")
        print(f"\n💡 FIX: Change MAX_RESULTS in config.py from 0 to 5 (or any positive integer)")
    else:
        print(f"\n✅ MAX_RESULTS is set to {config.MAX_RESULTS} - this should work correctly")

    print()

if __name__ == "__main__":
    test_max_results_bug()
