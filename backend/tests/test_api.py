"""API endpoint tests for the RAG system FastAPI application"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock


@pytest.mark.api
class TestAPIEndpoints:
    """Test suite for FastAPI endpoints"""

    def test_root_endpoint(self, test_client):
        """Test the root endpoint returns a welcome message"""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "Course Materials RAG System API"

    def test_query_endpoint_without_session_id(self, test_client, mock_rag_system):
        """Test /api/query endpoint creates a new session when none provided"""
        request_data = {
            "query": "What is artificial intelligence?"
        }

        response = test_client.post("/api/query", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

        # Verify session was created
        mock_rag_system.session_manager.create_session.assert_called_once()
        assert data["session_id"] == "test-session-123"

        # Verify query was called
        mock_rag_system.query.assert_called_once()

    def test_query_endpoint_with_session_id(self, test_client, mock_rag_system):
        """Test /api/query endpoint uses provided session_id"""
        existing_session_id = "existing-session-456"
        request_data = {
            "query": "What is machine learning?",
            "session_id": existing_session_id
        }

        response = test_client.post("/api/query", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Verify session_id is preserved
        assert data["session_id"] == existing_session_id

        # Verify create_session was NOT called
        mock_rag_system.session_manager.create_session.assert_not_called()

        # Verify query was called with correct session_id
        mock_rag_system.query.assert_called_once_with(
            "What is machine learning?",
            existing_session_id
        )

    def test_query_endpoint_response_structure(self, test_client, sample_course):
        """Test /api/query endpoint returns properly structured response"""
        request_data = {
            "query": "Tell me about neural networks"
        }

        response = test_client.post("/api/query", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Verify answer
        assert isinstance(data["answer"], str)
        assert len(data["answer"]) > 0

        # Verify sources structure
        assert isinstance(data["sources"], list)
        if len(data["sources"]) > 0:
            source = data["sources"][0]
            assert "course_title" in source
            assert "lesson_number" in source
            assert source["course_title"] == sample_course.title

    def test_query_endpoint_with_invalid_request(self, test_client):
        """Test /api/query endpoint handles invalid requests"""
        # Missing required field 'query'
        request_data = {
            "session_id": "test-session"
        }

        response = test_client.post("/api/query", json=request_data)

        # Should return 422 Unprocessable Entity for validation error
        assert response.status_code == 422

    def test_query_endpoint_with_empty_query(self, test_client):
        """Test /api/query endpoint handles empty query string"""
        request_data = {
            "query": ""
        }

        response = test_client.post("/api/query", json=request_data)

        # Empty string is valid, should return 200
        assert response.status_code == 200

    def test_query_endpoint_error_handling(self, test_client, mock_rag_system):
        """Test /api/query endpoint error handling"""
        # Make the query method raise an exception
        mock_rag_system.query.side_effect = Exception("Test error")

        request_data = {
            "query": "This will cause an error"
        }

        response = test_client.post("/api/query", json=request_data)

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Test error" in data["detail"]

    def test_courses_endpoint(self, test_client, mock_rag_system, sample_course):
        """Test /api/courses endpoint returns course statistics"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "total_courses" in data
        assert "course_titles" in data

        # Verify data
        assert data["total_courses"] == 1
        assert isinstance(data["course_titles"], list)
        assert sample_course.title in data["course_titles"]

        # Verify method was called
        mock_rag_system.get_course_analytics.assert_called_once()

    def test_courses_endpoint_error_handling(self, test_client, mock_rag_system):
        """Test /api/courses endpoint error handling"""
        # Make the get_course_analytics method raise an exception
        mock_rag_system.get_course_analytics.side_effect = Exception("Analytics error")

        response = test_client.get("/api/courses")

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Analytics error" in data["detail"]

    def test_query_endpoint_with_long_query(self, test_client):
        """Test /api/query endpoint handles long queries"""
        long_query = "What is " + "artificial intelligence " * 100
        request_data = {
            "query": long_query
        }

        response = test_client.post("/api/query", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data

    def test_cors_headers(self, test_client):
        """Test CORS headers are properly configured"""
        response = test_client.options(
            "/api/query",
            headers={"Origin": "http://localhost:3000"}
        )

        # Check CORS headers are present
        assert "access-control-allow-origin" in response.headers

    def test_multiple_sequential_queries(self, test_client):
        """Test multiple sequential queries with same session"""
        session_id = "persistent-session"

        queries = [
            "What is AI?",
            "Tell me about machine learning",
            "Explain neural networks"
        ]

        for query in queries:
            request_data = {
                "query": query,
                "session_id": session_id
            }

            response = test_client.post("/api/query", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == session_id

    def test_query_endpoint_special_characters(self, test_client):
        """Test /api/query endpoint handles special characters"""
        request_data = {
            "query": "What is AI? Can you explain <neural> networks & 'deep learning'?"
        }

        response = test_client.post("/api/query", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data


@pytest.mark.api
class TestAPIResponseModels:
    """Test suite for validating API response models"""

    def test_query_response_model_validation(self, test_client):
        """Test QueryResponse model validation"""
        request_data = {"query": "Test query"}

        response = test_client.post("/api/query", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

        # Type validation
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)

    def test_course_stats_response_model_validation(self, test_client):
        """Test CourseStats model validation"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert "total_courses" in data
        assert "course_titles" in data

        # Type validation
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)

        # All course titles should be strings
        for title in data["course_titles"]:
            assert isinstance(title, str)
