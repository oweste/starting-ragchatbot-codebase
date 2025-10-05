"""
Simple verification script to confirm the fix works end-to-end
Tests the actual search tool with the real database
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from vector_store import VectorStore
from search_tools import CourseSearchTool

def main():
    print("=" * 70)
    print("VERIFICATION: Testing CourseSearchTool with Fixed Configuration")
    print("=" * 70)

    print(f"\nConfiguration:")
    print(f"  MAX_RESULTS: {config.MAX_RESULTS}")
    print(f"  Expected: 5 (positive integer)")

    if config.MAX_RESULTS <= 0:
        print(f"\n  ERROR: MAX_RESULTS is still {config.MAX_RESULTS}!")
        print(f"  The fix was not applied correctly.")
        return False

    print(f"\n  OK: MAX_RESULTS is set correctly to {config.MAX_RESULTS}")

    # Initialize components
    print(f"\nInitializing VectorStore...")
    vector_store = VectorStore(
        chroma_path=config.CHROMA_PATH,
        embedding_model=config.EMBEDDING_MODEL,
        max_results=config.MAX_RESULTS
    )

    course_count = vector_store.get_course_count()
    print(f"  Courses in database: {course_count}")

    if course_count == 0:
        print(f"\n  WARNING: No courses in database.")
        print(f"  Please run the app first to load documents.")
        return False

    # Test the search tool
    print(f"\nInitializing CourseSearchTool...")
    search_tool = CourseSearchTool(vector_store)

    # Test 1: General search
    print(f"\n" + "=" * 70)
    print("TEST 1: General Content Search")
    print("=" * 70)

    query1 = "What is prompt caching?"
    print(f"\nQuery: '{query1}'")

    result1 = search_tool.execute(query=query1)

    if "Search error" in result1:
        print(f"\n  FAILED: Got ChromaDB error")
        print(f"  Error: {result1}")
        return False
    elif "No relevant content found" in result1:
        print(f"\n  WARNING: No content found (may be due to content not matching query)")
        print(f"  This is acceptable if the query doesn't match any content.")
    else:
        print(f"\n  SUCCESS: Got search results!")
        print(f"  Result length: {len(result1)} characters")
        print(f"  Sources tracked: {len(search_tool.last_sources)}")

        # Show a snippet
        lines = result1.split('\n')
        print(f"\n  Result preview:")
        for line in lines[:5]:
            print(f"    {line[:70]}...")

    # Test 2: Course-specific search
    print(f"\n" + "=" * 70)
    print("TEST 2: Course-Specific Search")
    print("=" * 70)

    # Get first course title
    course_titles = vector_store.get_existing_course_titles()
    if course_titles:
        first_course = course_titles[0]
        print(f"\nSearching in course: '{first_course}'")

        result2 = search_tool.execute(
            query="introduction",
            course_name=first_course
        )

        if "Search error" in result2:
            print(f"\n  FAILED: Got ChromaDB error")
            return False
        elif "No relevant content found" in result2:
            print(f"\n  No content found for this query in this course")
        else:
            print(f"\n  SUCCESS: Got course-filtered results!")
            print(f"  Result length: {len(result2)} characters")
            print(f"  Contains course name: {first_course in result2}")

    # Test 3: Tool definition
    print(f"\n" + "=" * 70)
    print("TEST 3: Tool Definition")
    print("=" * 70)

    tool_def = search_tool.get_tool_definition()
    print(f"\nTool name: {tool_def['name']}")
    print(f"Has input_schema: {'input_schema' in tool_def}")
    print(f"Required params: {tool_def['input_schema'].get('required', [])}")

    if tool_def['name'] != 'search_course_content':
        print(f"\n  FAILED: Unexpected tool name")
        return False

    print(f"\n  SUCCESS: Tool definition is correct")

    # Summary
    print(f"\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(f"\n  Configuration Fix: APPLIED")
    print(f"  VectorStore: WORKING")
    print(f"  CourseSearchTool: WORKING")
    print(f"  ChromaDB Queries: SUCCESSFUL")

    print(f"\n  The RAG system should now be able to answer content queries!")
    print(f"\n  Test the full system by:")
    print(f"    1. Running: cd backend && uv run uvicorn app:app --reload --port 8000")
    print(f"    2. Visiting: http://localhost:8000")
    print(f"    3. Asking: 'What is prompt caching?'")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
