"""Integration tests for the RAG system"""

import shutil
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest
from config import Config
from rag_system import RAGSystem


class TestRAGSystemIntegration:
    """Integration tests for the complete RAG system"""

    @pytest.fixture
    def temp_config(self):
        """Create a test configuration with temporary paths"""
        temp_dir = tempfile.mkdtemp()
        config = Config()
        config.CHROMA_PATH = temp_dir
        config.MAX_RESULTS = 5  # Set to proper value
        yield config
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def temp_config_zero_results(self):
        """Create a test configuration with MAX_RESULTS=0 to test the bug"""
        temp_dir = tempfile.mkdtemp()
        config = Config()
        config.CHROMA_PATH = temp_dir
        config.MAX_RESULTS = 0  # This simulates the bug
        yield config
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def mock_anthropic_response(self):
        """Create a mock for successful Anthropic API response"""
        with patch("ai_generator.anthropic.Anthropic") as mock_client_class:
            mock_client = MagicMock()

            # Mock tool use response
            mock_tool_block = MagicMock()
            mock_tool_block.type = "tool_use"
            mock_tool_block.name = "search_course_content"
            mock_tool_block.id = "tool_123"
            mock_tool_block.input = {"query": "artificial intelligence"}

            mock_initial_response = MagicMock()
            mock_initial_response.content = [mock_tool_block]
            mock_initial_response.stop_reason = "tool_use"

            mock_final_response = MagicMock()
            mock_final_response.content = [MagicMock(text="AI is intelligent systems")]
            mock_final_response.stop_reason = "end_turn"

            mock_client.messages.create.side_effect = [
                mock_initial_response,
                mock_final_response,
            ]

            mock_client_class.return_value = mock_client
            yield mock_client

    def test_rag_system_initializes_correctly(self, temp_config):
        """Test that RAG system initializes all components"""
        rag = RAGSystem(temp_config)

        assert rag.document_processor is not None
        assert rag.vector_store is not None
        assert rag.ai_generator is not None
        assert rag.session_manager is not None
        assert rag.tool_manager is not None
        assert rag.search_tool is not None

    def test_add_course_document(self, temp_config):
        """Test adding a course document to the system"""
        # Create a temporary course file
        temp_dir = tempfile.mkdtemp()
        course_file = f"{temp_dir}/test_course.txt"

        with open(course_file, "w", encoding="utf-8") as f:
            f.write("Course Title: Test Course\n")
            f.write("Course Link: https://example.com/test\n")
            f.write("Course Instructor: Test Instructor\n")
            f.write("\n")
            f.write("Lesson 0: Introduction\n")
            f.write("Lesson Link: https://example.com/test/lesson-0\n")
            f.write("This is the introduction to the test course.\n")

        try:
            rag = RAGSystem(temp_config)
            course, chunk_count = rag.add_course_document(course_file)

            assert course is not None
            assert course.title == "Test Course"
            assert chunk_count > 0
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_query_with_content_found(
        self, temp_config, sample_course, sample_course_chunks, mock_anthropic_response
    ):
        """Test querying when relevant content exists"""
        rag = RAGSystem(temp_config)

        # Add test data
        rag.vector_store.add_course_metadata(sample_course)
        rag.vector_store.add_course_content(sample_course_chunks)

        # Query the system
        response, sources = rag.query("What is artificial intelligence?")

        # Should get a response
        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0

    def test_query_with_zero_max_results_bug(
        self,
        temp_config_zero_results,
        sample_course,
        sample_course_chunks,
        mock_anthropic_response,
    ):
        """Test that MAX_RESULTS=0 causes the 'query failed' bug"""
        rag = RAGSystem(temp_config_zero_results)

        # Add test data
        rag.vector_store.add_course_metadata(sample_course)
        rag.vector_store.add_course_content(sample_course_chunks)

        # Directly test the search tool
        search_result = rag.search_tool.execute(query="artificial intelligence")

        # With MAX_RESULTS=0, should get no results
        assert "No relevant content found" in search_result

    def test_query_creates_session_if_none_provided(
        self, temp_config, mock_anthropic_response
    ):
        """Test that query works without session_id"""
        rag = RAGSystem(temp_config)

        # Query without session_id - should not error
        with patch.object(
            rag.ai_generator, "generate_response", return_value="Test response"
        ):
            response, sources = rag.query("Test query")

            assert response == "Test response"
            assert isinstance(sources, list)

    def test_query_uses_existing_session(self, temp_config, mock_anthropic_response):
        """Test that query uses existing session correctly"""
        rag = RAGSystem(temp_config)

        # Create a session
        session_id = rag.session_manager.create_session()

        # Add some history
        rag.session_manager.add_exchange(
            session_id, "What is AI?", "AI is artificial intelligence"
        )

        # Query with session
        with patch.object(
            rag.ai_generator, "generate_response", return_value="Follow-up response"
        ) as mock_gen:
            response, sources = rag.query("Tell me more", session_id=session_id)

            # Verify history was passed
            call_args = mock_gen.call_args
            history = call_args[1]["conversation_history"]
            assert history is not None
            assert "What is AI?" in history

    def test_query_updates_session_history(self, temp_config, mock_anthropic_response):
        """Test that query updates conversation history"""
        rag = RAGSystem(temp_config)

        session_id = rag.session_manager.create_session()

        with patch.object(rag.ai_generator, "generate_response", return_value="Answer"):
            rag.query("Question", session_id=session_id)

            # Check history was updated
            history = rag.session_manager.get_conversation_history(session_id)
            assert history is not None
            assert "Question" in history
            assert "Answer" in history

    def test_get_course_analytics(
        self, temp_config, sample_course, sample_course_chunks
    ):
        """Test getting course analytics"""
        rag = RAGSystem(temp_config)

        # Add test data
        rag.vector_store.add_course_metadata(sample_course)
        rag.vector_store.add_course_content(sample_course_chunks)

        analytics = rag.get_course_analytics()

        assert "total_courses" in analytics
        assert "course_titles" in analytics
        assert analytics["total_courses"] == 1
        assert sample_course.title in analytics["course_titles"]

    def test_vector_store_max_results_configuration(self, temp_config):
        """Test that vector store respects MAX_RESULTS configuration"""
        rag = RAGSystem(temp_config)

        # Verify max_results is set from config
        assert rag.vector_store.max_results == temp_config.MAX_RESULTS

    def test_vector_store_max_results_zero_bug(self, temp_config_zero_results):
        """Test that MAX_RESULTS=0 is the root cause of the bug"""
        rag = RAGSystem(temp_config_zero_results)

        # Verify max_results is 0 (the bug)
        assert rag.vector_store.max_results == 0

        # This will cause search to return 0 results
        # even if data exists in the vector store


class TestRAGSystemDocumentProcessing:
    """Test document processing in RAG system"""

    @pytest.fixture
    def temp_config(self):
        """Create a test configuration"""
        temp_dir = tempfile.mkdtemp()
        config = Config()
        config.CHROMA_PATH = temp_dir
        config.MAX_RESULTS = 5
        yield config
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_add_course_folder_skips_existing(self, temp_config):
        """Test that add_course_folder doesn't re-add existing courses"""
        rag = RAGSystem(temp_config)

        # Create temporary folder with course files
        temp_docs = tempfile.mkdtemp()
        course_file = f"{temp_docs}/course.txt"

        with open(course_file, "w", encoding="utf-8") as f:
            f.write("Course Title: Unique Test Course\n")
            f.write("Course Link: https://example.com\n")
            f.write("Course Instructor: Instructor\n")
            f.write("\n")
            f.write("Lesson 0: Intro\n")
            f.write("Content here\n")

        try:
            # Add first time
            courses1, chunks1 = rag.add_course_folder(temp_docs, clear_existing=False)
            assert courses1 == 1

            # Add again - should skip
            courses2, chunks2 = rag.add_course_folder(temp_docs, clear_existing=False)
            assert courses2 == 0  # Should skip existing course

        finally:
            shutil.rmtree(temp_docs, ignore_errors=True)

    def test_add_course_folder_with_clear(
        self, temp_config, sample_course, sample_course_chunks
    ):
        """Test that add_course_folder clears existing data when requested"""
        rag = RAGSystem(temp_config)

        # Add some data
        rag.vector_store.add_course_metadata(sample_course)
        rag.vector_store.add_course_content(sample_course_chunks)

        # Verify data exists
        assert rag.vector_store.get_course_count() == 1

        # Clear and reload (with empty folder)
        temp_docs = tempfile.mkdtemp()
        try:
            rag.add_course_folder(temp_docs, clear_existing=True)

            # Data should be cleared
            assert rag.vector_store.get_course_count() == 0

        finally:
            shutil.rmtree(temp_docs, ignore_errors=True)


class TestRAGSystemSourceTracking:
    """Test source tracking in RAG system"""

    @pytest.fixture
    def temp_config(self):
        """Create a test configuration"""
        temp_dir = tempfile.mkdtemp()
        config = Config()
        config.CHROMA_PATH = temp_dir
        config.MAX_RESULTS = 5
        yield config
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_sources_returned_from_query(
        self, temp_config, sample_course, sample_course_chunks
    ):
        """Test that sources are returned from query"""
        rag = RAGSystem(temp_config)

        # Add test data
        rag.vector_store.add_course_metadata(sample_course)
        rag.vector_store.add_course_content(sample_course_chunks)

        # Mock AI response to use tool
        with patch.object(rag.ai_generator, "generate_response") as mock_gen:
            # Simulate AI calling the search tool
            def side_effect(*args, **kwargs):
                # Execute the tool
                rag.tool_manager.execute_tool(
                    "search_course_content", query="artificial intelligence"
                )
                return "AI response"

            mock_gen.side_effect = side_effect

            response, sources = rag.query("What is AI?")

            # Sources should be populated
            assert isinstance(sources, list)

    def test_sources_reset_after_query(
        self, temp_config, sample_course, sample_course_chunks
    ):
        """Test that sources are reset between queries"""
        rag = RAGSystem(temp_config)

        rag.vector_store.add_course_metadata(sample_course)
        rag.vector_store.add_course_content(sample_course_chunks)

        with patch.object(rag.ai_generator, "generate_response") as mock_gen:

            def side_effect(*args, **kwargs):
                rag.tool_manager.execute_tool("search_course_content", query="AI")
                return "Response"

            mock_gen.side_effect = side_effect

            # First query
            response1, sources1 = rag.query("Query 1")

            # Sources should be empty in tool manager after reset
            current_sources = rag.tool_manager.get_last_sources()
            assert len(current_sources) == 0
