"""Pytest configuration and shared fixtures for RAG system tests"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import List

from models import Course, Lesson, CourseChunk
from vector_store import VectorStore
from config import Config


@pytest.fixture
def temp_chroma_path():
    """Create a temporary directory for ChromaDB during tests"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup after test
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_config(temp_chroma_path):
    """Create a test configuration with temporary ChromaDB path"""
    config = Config()
    config.CHROMA_PATH = temp_chroma_path
    config.MAX_RESULTS = 5  # Override with proper value for testing
    return config


@pytest.fixture
def sample_course() -> Course:
    """Create a sample course for testing"""
    return Course(
        title="Test Course on AI",
        course_link="https://example.com/test-course",
        instructor="Test Instructor",
        lessons=[
            Lesson(
                lesson_number=0,
                title="Introduction to AI",
                lesson_link="https://example.com/test-course/lesson-0"
            ),
            Lesson(
                lesson_number=1,
                title="Machine Learning Basics",
                lesson_link="https://example.com/test-course/lesson-1"
            ),
            Lesson(
                lesson_number=2,
                title="Neural Networks",
                lesson_link="https://example.com/test-course/lesson-2"
            )
        ]
    )


@pytest.fixture
def sample_course_chunks(sample_course) -> List[CourseChunk]:
    """Create sample course chunks for testing"""
    return [
        CourseChunk(
            content="Course Test Course on AI Lesson 0 content: Artificial Intelligence is the simulation of human intelligence by machines. It includes learning, reasoning, and self-correction.",
            course_title=sample_course.title,
            lesson_number=0,
            chunk_index=0
        ),
        CourseChunk(
            content="AI systems can perform tasks that typically require human intelligence such as visual perception, speech recognition, and decision-making.",
            course_title=sample_course.title,
            lesson_number=0,
            chunk_index=1
        ),
        CourseChunk(
            content="Course Test Course on AI Lesson 1 content: Machine learning is a subset of AI that enables systems to learn from data without explicit programming. Supervised learning uses labeled data.",
            course_title=sample_course.title,
            lesson_number=1,
            chunk_index=2
        ),
        CourseChunk(
            content="Unsupervised learning finds patterns in unlabeled data. Reinforcement learning learns through trial and error using rewards.",
            course_title=sample_course.title,
            lesson_number=1,
            chunk_index=3
        ),
        CourseChunk(
            content="Course Test Course on AI Lesson 2 content: Neural networks are computing systems inspired by biological neural networks. They consist of interconnected nodes called neurons.",
            course_title=sample_course.title,
            lesson_number=2,
            chunk_index=4
        ),
        CourseChunk(
            content="Deep learning uses neural networks with multiple layers to learn hierarchical representations of data. Backpropagation is used to train these networks.",
            course_title=sample_course.title,
            lesson_number=2,
            chunk_index=5
        )
    ]


@pytest.fixture
def populated_vector_store(test_config, sample_course, sample_course_chunks):
    """Create a vector store populated with sample data"""
    vector_store = VectorStore(
        chroma_path=test_config.CHROMA_PATH,
        embedding_model=test_config.EMBEDDING_MODEL,
        max_results=test_config.MAX_RESULTS
    )

    # Add course metadata and content
    vector_store.add_course_metadata(sample_course)
    vector_store.add_course_content(sample_course_chunks)

    return vector_store


@pytest.fixture
def empty_vector_store(test_config):
    """Create an empty vector store for testing"""
    return VectorStore(
        chroma_path=test_config.CHROMA_PATH,
        embedding_model=test_config.EMBEDDING_MODEL,
        max_results=test_config.MAX_RESULTS
    )
