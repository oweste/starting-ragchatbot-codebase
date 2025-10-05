"""Tests for AIGenerator tool calling functionality"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from ai_generator import AIGenerator
from search_tools import ToolManager, CourseSearchTool


class TestAIGeneratorToolCalling:
    """Test AIGenerator's ability to call tools correctly"""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Create a mock Anthropic client"""
        with patch('ai_generator.anthropic.Anthropic') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def ai_generator(self, mock_anthropic_client):
        """Create an AIGenerator with mocked client"""
        return AIGenerator(api_key="test-key", model="test-model")

    def test_ai_generator_initializes_correctly(self, ai_generator):
        """Test that AIGenerator initializes with correct parameters"""
        assert ai_generator.model == "test-model"
        assert ai_generator.base_params['model'] == "test-model"
        assert ai_generator.base_params['temperature'] == 0
        assert ai_generator.base_params['max_tokens'] == 800

    def test_generate_response_without_tools(self, ai_generator, mock_anthropic_client):
        """Test generate_response works without tools"""
        # Mock response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="This is a test response")]
        mock_response.stop_reason = "end_turn"
        mock_anthropic_client.messages.create.return_value = mock_response

        result = ai_generator.generate_response(
            query="What is AI?",
            tools=None,
            tool_manager=None
        )

        assert result == "This is a test response"
        assert mock_anthropic_client.messages.create.called

    def test_generate_response_with_tools_no_tool_use(self, ai_generator, mock_anthropic_client, populated_vector_store):
        """Test generate_response when Claude doesn't use tools"""
        # Mock response that doesn't use tools
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="I can answer this without searching")]
        mock_response.stop_reason = "end_turn"
        mock_anthropic_client.messages.create.return_value = mock_response

        # Create tool manager
        tool_manager = ToolManager()
        search_tool = CourseSearchTool(populated_vector_store)
        tool_manager.register_tool(search_tool)

        result = ai_generator.generate_response(
            query="What is 2+2?",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )

        assert result == "I can answer this without searching"

    def test_generate_response_with_tool_use(self, ai_generator, mock_anthropic_client, populated_vector_store):
        """Test generate_response when Claude uses a tool"""
        # Mock initial response with tool use
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.id = "tool_123"
        mock_tool_block.input = {"query": "artificial intelligence"}

        mock_initial_response = MagicMock()
        mock_initial_response.content = [mock_tool_block]
        mock_initial_response.stop_reason = "tool_use"

        # Mock final response after tool execution
        mock_final_response = MagicMock()
        mock_final_response.content = [MagicMock(text="AI is the simulation of human intelligence")]
        mock_final_response.stop_reason = "end_turn"

        # Set up mock to return different responses
        mock_anthropic_client.messages.create.side_effect = [
            mock_initial_response,
            mock_final_response
        ]

        # Create tool manager
        tool_manager = ToolManager()
        search_tool = CourseSearchTool(populated_vector_store)
        tool_manager.register_tool(search_tool)

        result = ai_generator.generate_response(
            query="What is AI?",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )

        # Should return final response after tool execution
        assert result == "AI is the simulation of human intelligence"
        # Should have called API twice (initial + final)
        assert mock_anthropic_client.messages.create.call_count == 2

    def test_tool_execution_flow(self, ai_generator, mock_anthropic_client, populated_vector_store):
        """Test the complete tool execution flow"""
        # Create mock tool use block
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.id = "tool_456"
        mock_tool_block.input = {
            "query": "neural networks",
            "lesson_number": 2
        }

        mock_initial_response = MagicMock()
        mock_initial_response.content = [mock_tool_block]
        mock_initial_response.stop_reason = "tool_use"

        mock_final_response = MagicMock()
        mock_final_response.content = [MagicMock(text="Neural networks are computing systems")]
        mock_final_response.stop_reason = "end_turn"

        mock_anthropic_client.messages.create.side_effect = [
            mock_initial_response,
            mock_final_response
        ]

        # Create tool manager
        tool_manager = ToolManager()
        search_tool = CourseSearchTool(populated_vector_store)
        tool_manager.register_tool(search_tool)

        result = ai_generator.generate_response(
            query="Explain neural networks",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )

        assert result == "Neural networks are computing systems"

        # Verify the second API call included tool results
        second_call_args = mock_anthropic_client.messages.create.call_args_list[1]
        messages = second_call_args[1]['messages']

        # Should have 3 messages: user query, assistant tool use, user tool result
        assert len(messages) == 3
        assert messages[0]['role'] == 'user'
        assert messages[1]['role'] == 'assistant'
        assert messages[2]['role'] == 'user'

        # Tool result should be in the last message
        tool_results = messages[2]['content']
        assert isinstance(tool_results, list)
        assert tool_results[0]['type'] == 'tool_result'
        assert tool_results[0]['tool_use_id'] == 'tool_456'

    def test_generate_response_includes_conversation_history(self, ai_generator, mock_anthropic_client):
        """Test that conversation history is included in system prompt"""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Response")]
        mock_response.stop_reason = "end_turn"
        mock_anthropic_client.messages.create.return_value = mock_response

        history = "User: Previous question\nAssistant: Previous answer"

        ai_generator.generate_response(
            query="New question",
            conversation_history=history,
            tools=None,
            tool_manager=None
        )

        # Check that history was included in system prompt
        call_args = mock_anthropic_client.messages.create.call_args
        system_content = call_args[1]['system']
        assert "Previous question" in system_content
        assert "Previous answer" in system_content

    def test_tool_definitions_passed_correctly(self, ai_generator, mock_anthropic_client, empty_vector_store):
        """Test that tool definitions are passed to API correctly"""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Response")]
        mock_response.stop_reason = "end_turn"
        mock_anthropic_client.messages.create.return_value = mock_response

        # Create tool manager with search tool
        tool_manager = ToolManager()
        search_tool = CourseSearchTool(empty_vector_store)
        tool_manager.register_tool(search_tool)

        ai_generator.generate_response(
            query="Test query",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )

        # Verify tools were passed to API
        call_args = mock_anthropic_client.messages.create.call_args
        assert 'tools' in call_args[1]
        tools = call_args[1]['tools']
        assert len(tools) > 0
        assert tools[0]['name'] == 'search_course_content'

    def test_system_prompt_contains_tool_instructions(self):
        """Test that SYSTEM_PROMPT contains instructions for tool usage"""
        prompt = AIGenerator.SYSTEM_PROMPT

        # Check for key tool usage instructions
        assert 'tool' in prompt.lower() or 'search' in prompt.lower()
        assert 'course' in prompt.lower()

        # Should have some guidance on when to use tools
        assert len(prompt) > 100  # Reasonably detailed prompt


class TestAIGeneratorErrorHandling:
    """Test error handling in AIGenerator"""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Create a mock Anthropic client"""
        with patch('ai_generator.anthropic.Anthropic') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def ai_generator(self, mock_anthropic_client):
        """Create an AIGenerator with mocked client"""
        return AIGenerator(api_key="test-key", model="test-model")

    def test_handles_api_errors_gracefully(self, ai_generator, mock_anthropic_client):
        """Test that API errors are propagated appropriately"""
        mock_anthropic_client.messages.create.side_effect = Exception("API Error")

        with pytest.raises(Exception) as exc_info:
            ai_generator.generate_response(
                query="Test query",
                tools=None,
                tool_manager=None
            )

        assert "API Error" in str(exc_info.value)
