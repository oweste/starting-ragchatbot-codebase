"""Pytest configuration and shared fixtures for RAG system tests"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import List
from unittest.mock import Mock, MagicMock
from fastapi.testclient import TestClient

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


@pytest.fixture
def mock_rag_system(sample_course):
    """Create a mocked RAG system for API testing"""
    mock_rag = MagicMock()

    # Mock session manager
    mock_session_manager = MagicMock()
    mock_session_manager.create_session.return_value = "test-session-123"
    mock_rag.session_manager = mock_session_manager

    # Mock query method
    mock_rag.query.return_value = (
        "This is a test answer about AI.",
        [
            {
                "course_title": sample_course.title,
                "lesson_number": 0,
                "lesson_title": "Introduction to AI"
            }
        ]
    )

    # Mock get_course_analytics method
    mock_rag.get_course_analytics.return_value = {
        "total_courses": 1,
        "course_titles": [sample_course.title]
    }

    return mock_rag


@pytest.fixture
def test_app(mock_rag_system):
    """Create a test FastAPI app with mocked dependencies"""
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    from typing import List, Optional, Dict

    # Create test app
    app = FastAPI(title="Course Materials RAG System - Test", root_path="")

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Define request/response models
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[Dict[str, Optional[str]]]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    # Define endpoints
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()

            answer, sources = mock_rag_system.query(request.query, session_id)

            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/")
    async def root():
        return {"message": "Course Materials RAG System API"}

    return app


@pytest.fixture
def test_client(test_app):
    """Create a test client for API testing"""
    return TestClient(test_app)
