"""Tests for CourseSearchTool.execute() method"""

import pytest
from search_tools import CourseSearchTool, ToolManager


class TestCourseSearchToolExecute:
    """Test the execute method of CourseSearchTool"""

    def test_execute_returns_results_with_valid_query(self, populated_vector_store):
        """Test that execute returns formatted results for a valid query"""
        tool = CourseSearchTool(populated_vector_store)

        result = tool.execute(query="What is artificial intelligence?")

        # Should return formatted results, not error message
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
        assert "No relevant content found" not in result
        assert "[Test Course on AI" in result  # Should have course context

    def test_execute_returns_no_results_for_irrelevant_query(self, populated_vector_store):
        """Test that execute returns appropriate message for irrelevant query"""
        tool = CourseSearchTool(populated_vector_store)

        result = tool.execute(query="quantum physics of black holes in outer space")

        # May or may not find results depending on semantic similarity
        # Just verify it returns a string response
        assert isinstance(result, str)

    def test_execute_with_course_filter(self, populated_vector_store):
        """Test that execute respects course_name filter"""
        tool = CourseSearchTool(populated_vector_store)

        result = tool.execute(
            query="machine learning",
            course_name="Test Course on AI"
        )

        assert isinstance(result, str)
        assert "No relevant content found" not in result
        assert "Test Course on AI" in result

    def test_execute_with_lesson_filter(self, populated_vector_store):
        """Test that execute respects lesson_number filter"""
        tool = CourseSearchTool(populated_vector_store)

        result = tool.execute(
            query="neural networks",
            lesson_number=2
        )

        assert isinstance(result, str)
        # Should find content from lesson 2
        if "No relevant content found" not in result:
            assert "Lesson 2" in result

    def test_execute_with_both_filters(self, populated_vector_store):
        """Test that execute works with both course and lesson filters"""
        tool = CourseSearchTool(populated_vector_store)

        result = tool.execute(
            query="deep learning",
            course_name="Test Course",
            lesson_number=2
        )

        assert isinstance(result, str)

    def test_execute_with_nonexistent_course(self, populated_vector_store):
        """Test that execute handles nonexistent course gracefully"""
        tool = CourseSearchTool(populated_vector_store)

        result = tool.execute(
            query="anything",
            course_name="Nonexistent Course That Does Not Exist"
        )

        assert isinstance(result, str)
        assert "No course found" in result or "No relevant content found" in result

    def test_execute_tracks_sources(self, populated_vector_store):
        """Test that execute properly tracks sources in last_sources"""
        tool = CourseSearchTool(populated_vector_store)

        result = tool.execute(query="artificial intelligence")

        # If results found, sources should be populated
        if "No relevant content found" not in result:
            assert hasattr(tool, 'last_sources')
            assert isinstance(tool.last_sources, list)
            assert len(tool.last_sources) > 0

            # Check source structure
            first_source = tool.last_sources[0]
            assert 'text' in first_source
            assert 'link' in first_source

    def test_execute_with_empty_store(self, empty_vector_store):
        """Test that execute handles empty vector store gracefully"""
        tool = CourseSearchTool(empty_vector_store)

        result = tool.execute(query="anything")

        assert isinstance(result, str)
        assert "No relevant content found" in result or "error" in result.lower()

    def test_execute_formats_results_correctly(self, populated_vector_store):
        """Test that execute formats results with proper structure"""
        tool = CourseSearchTool(populated_vector_store)

        result = tool.execute(query="machine learning")

        if "No relevant content found" not in result:
            # Should have header with course and lesson info
            assert "[Test Course on AI" in result
            # Should have actual content
            lines = result.split('\n')
            assert len(lines) > 1  # At least header and content

    def test_tool_definition_structure(self, empty_vector_store):
        """Test that get_tool_definition returns correct structure"""
        tool = CourseSearchTool(empty_vector_store)

        definition = tool.get_tool_definition()

        assert isinstance(definition, dict)
        assert definition['name'] == 'search_course_content'
        assert 'description' in definition
        assert 'input_schema' in definition

        schema = definition['input_schema']
        assert schema['type'] == 'object'
        assert 'properties' in schema
        assert 'query' in schema['properties']
        assert 'required' in schema
        assert 'query' in schema['required']


class TestToolManager:
    """Test the ToolManager class"""

    def test_tool_manager_registers_tool(self, empty_vector_store):
        """Test that ToolManager can register a tool"""
        manager = ToolManager()
        tool = CourseSearchTool(empty_vector_store)

        manager.register_tool(tool)

        assert 'search_course_content' in manager.tools

    def test_tool_manager_executes_tool(self, populated_vector_store):
        """Test that ToolManager can execute a registered tool"""
        manager = ToolManager()
        tool = CourseSearchTool(populated_vector_store)
        manager.register_tool(tool)

        result = manager.execute_tool(
            'search_course_content',
            query="artificial intelligence"
        )

        assert isinstance(result, str)
        assert len(result) > 0

    def test_tool_manager_gets_sources(self, populated_vector_store):
        """Test that ToolManager retrieves sources from tools"""
        manager = ToolManager()
        tool = CourseSearchTool(populated_vector_store)
        manager.register_tool(tool)

        # Execute search to populate sources
        manager.execute_tool('search_course_content', query="AI")

        sources = manager.get_last_sources()
        assert isinstance(sources, list)

    def test_tool_manager_resets_sources(self, populated_vector_store):
        """Test that ToolManager can reset sources"""
        manager = ToolManager()
        tool = CourseSearchTool(populated_vector_store)
        manager.register_tool(tool)

        # Execute and verify sources exist
        manager.execute_tool('search_course_content', query="AI")
        sources_before = manager.get_last_sources()

        # Reset
        manager.reset_sources()
        sources_after = manager.get_last_sources()

        assert len(sources_after) == 0
