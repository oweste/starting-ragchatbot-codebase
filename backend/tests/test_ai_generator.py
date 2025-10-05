"""Tests for AIGenerator tool calling functionality"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from ai_generator import AIGenerator
from search_tools import CourseSearchTool, ToolManager


class TestAIGeneratorToolCalling:
    """Test AIGenerator's ability to call tools correctly"""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Create a mock Anthropic client"""
        with patch("ai_generator.anthropic.Anthropic") as mock_client_class:
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
        assert ai_generator.base_params["model"] == "test-model"
        assert ai_generator.base_params["temperature"] == 0
        assert ai_generator.base_params["max_tokens"] == 800

    def test_generate_response_without_tools(self, ai_generator, mock_anthropic_client):
        """Test generate_response works without tools"""
        # Mock response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="This is a test response")]
        mock_response.stop_reason = "end_turn"
        mock_anthropic_client.messages.create.return_value = mock_response

        result = ai_generator.generate_response(
            query="What is AI?", tools=None, tool_manager=None
        )

        assert result == "This is a test response"
        assert mock_anthropic_client.messages.create.called

    def test_generate_response_with_tools_no_tool_use(
        self, ai_generator, mock_anthropic_client, populated_vector_store
    ):
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
            tool_manager=tool_manager,
        )

        assert result == "I can answer this without searching"

    def test_generate_response_with_tool_use(
        self, ai_generator, mock_anthropic_client, populated_vector_store
    ):
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
        mock_final_response.content = [
            MagicMock(text="AI is the simulation of human intelligence")
        ]
        mock_final_response.stop_reason = "end_turn"

        # Set up mock to return different responses
        mock_anthropic_client.messages.create.side_effect = [
            mock_initial_response,
            mock_final_response,
        ]

        # Create tool manager
        tool_manager = ToolManager()
        search_tool = CourseSearchTool(populated_vector_store)
        tool_manager.register_tool(search_tool)

        result = ai_generator.generate_response(
            query="What is AI?",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager,
        )

        # Should return final response after tool execution
        assert result == "AI is the simulation of human intelligence"
        # Should have called API twice (initial + final)
        assert mock_anthropic_client.messages.create.call_count == 2

    def test_tool_execution_flow(
        self, ai_generator, mock_anthropic_client, populated_vector_store
    ):
        """Test the complete tool execution flow"""
        # Create mock tool use block
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.id = "tool_456"
        mock_tool_block.input = {"query": "neural networks", "lesson_number": 2}

        mock_initial_response = MagicMock()
        mock_initial_response.content = [mock_tool_block]
        mock_initial_response.stop_reason = "tool_use"

        mock_final_response = MagicMock()
        mock_final_response.content = [
            MagicMock(text="Neural networks are computing systems")
        ]
        mock_final_response.stop_reason = "end_turn"

        mock_anthropic_client.messages.create.side_effect = [
            mock_initial_response,
            mock_final_response,
        ]

        # Create tool manager
        tool_manager = ToolManager()
        search_tool = CourseSearchTool(populated_vector_store)
        tool_manager.register_tool(search_tool)

        result = ai_generator.generate_response(
            query="Explain neural networks",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager,
        )

        assert result == "Neural networks are computing systems"

        # Verify the second API call included tool results
        second_call_args = mock_anthropic_client.messages.create.call_args_list[1]
        messages = second_call_args[1]["messages"]

        # Should have 3 messages: user query, assistant tool use, user tool result
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"

        # Tool result should be in the last message
        tool_results = messages[2]["content"]
        assert isinstance(tool_results, list)
        assert tool_results[0]["type"] == "tool_result"
        assert tool_results[0]["tool_use_id"] == "tool_456"

    def test_generate_response_includes_conversation_history(
        self, ai_generator, mock_anthropic_client
    ):
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
            tool_manager=None,
        )

        # Check that history was included in system prompt
        call_args = mock_anthropic_client.messages.create.call_args
        system_content = call_args[1]["system"]
        assert "Previous question" in system_content
        assert "Previous answer" in system_content

    def test_tool_definitions_passed_correctly(
        self, ai_generator, mock_anthropic_client, empty_vector_store
    ):
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
            tool_manager=tool_manager,
        )

        # Verify tools were passed to API
        call_args = mock_anthropic_client.messages.create.call_args
        assert "tools" in call_args[1]
        tools = call_args[1]["tools"]
        assert len(tools) > 0
        assert tools[0]["name"] == "search_course_content"

    def test_system_prompt_contains_tool_instructions(self):
        """Test that SYSTEM_PROMPT contains instructions for tool usage"""
        prompt = AIGenerator.SYSTEM_PROMPT

        # Check for key tool usage instructions
        assert "tool" in prompt.lower() or "search" in prompt.lower()
        assert "course" in prompt.lower()

        # Should have some guidance on when to use tools
        assert len(prompt) > 100  # Reasonably detailed prompt


class TestAIGeneratorErrorHandling:
    """Test error handling in AIGenerator"""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Create a mock Anthropic client"""
        with patch("ai_generator.anthropic.Anthropic") as mock_client_class:
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
                query="Test query", tools=None, tool_manager=None
            )

        assert "API Error" in str(exc_info.value)


class TestSequentialToolCalling:
    """Test sequential tool calling functionality (up to 2 rounds)"""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Create a mock Anthropic client"""
        with patch("ai_generator.anthropic.Anthropic") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def ai_generator(self, mock_anthropic_client):
        """Create an AIGenerator with mocked client"""
        return AIGenerator(api_key="test-key", model="test-model")

    @pytest.fixture
    def mock_tool_manager(self):
        """Create a mock tool manager for testing"""
        mock_manager = MagicMock()
        mock_manager.execute_tool.return_value = "Mock tool result"
        mock_manager.get_tool_definitions.return_value = [
            {"name": "search_course_content", "description": "Search course content"}
        ]
        return mock_manager

    def test_sequential_tool_calling_two_rounds(
        self, ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """Test that Claude can make 2 sequential tool calls"""
        # First tool use
        mock_tool_block_1 = MagicMock()
        mock_tool_block_1.type = "tool_use"
        mock_tool_block_1.name = "search_course_content"
        mock_tool_block_1.id = "tool_1"
        mock_tool_block_1.input = {"query": "MCP basics"}

        mock_response_1 = MagicMock()
        mock_response_1.content = [mock_tool_block_1]
        mock_response_1.stop_reason = "tool_use"

        # Second tool use
        mock_tool_block_2 = MagicMock()
        mock_tool_block_2.type = "tool_use"
        mock_tool_block_2.name = "search_course_content"
        mock_tool_block_2.id = "tool_2"
        mock_tool_block_2.input = {"query": "MCP advanced"}

        mock_response_2 = MagicMock()
        mock_response_2.content = [mock_tool_block_2]
        mock_response_2.stop_reason = "tool_use"

        # Final response
        mock_final_response = MagicMock()
        mock_final_response.content = [
            MagicMock(text="MCP allows for tool integration")
        ]
        mock_final_response.stop_reason = "end_turn"

        # Setup mock to return responses in sequence
        mock_anthropic_client.messages.create.side_effect = [
            mock_response_1,  # Initial call with tools
            mock_response_2,  # Second call (round 2) with tools
            mock_final_response,  # Final call without tools (forced synthesis)
        ]

        result = ai_generator.generate_response(
            query="Tell me about MCP",
            tools=mock_tool_manager.get_tool_definitions(),
            tool_manager=mock_tool_manager,
        )

        # Verify 3 API calls were made (initial + round 2 + final synthesis)
        assert mock_anthropic_client.messages.create.call_count == 3

        # Verify final response
        assert result == "MCP allows for tool integration"

    def test_sequential_stops_after_max_rounds(
        self, ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """Test that system enforces 2-round maximum even if Claude wants more"""
        # Mock tool block
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.id = "tool_123"
        mock_tool_block.input = {"query": "test"}

        # Mock responses - always return tool_use
        mock_tool_response = MagicMock()
        mock_tool_response.content = [mock_tool_block]
        mock_tool_response.stop_reason = "tool_use"

        # Final response (after tools removed)
        mock_final_response = MagicMock()
        mock_final_response.content = [
            MagicMock(text="Final answer based on gathered info")
        ]
        mock_final_response.stop_reason = "end_turn"

        # Setup: always return tool_use for first 2, then final response
        mock_anthropic_client.messages.create.side_effect = [
            mock_tool_response,  # Round 1
            mock_tool_response,  # Round 2
            mock_final_response,  # Forced synthesis (tools removed)
        ]

        result = ai_generator.generate_response(
            query="Test query",
            tools=mock_tool_manager.get_tool_definitions(),
            tool_manager=mock_tool_manager,
        )

        # Should have 3 calls: round 1 + round 2 + final (tools removed)
        assert mock_anthropic_client.messages.create.call_count == 3

        # Verify last call has NO tools parameter (forced synthesis)
        last_call_kwargs = mock_anthropic_client.messages.create.call_args_list[2][1]
        assert "tools" not in last_call_kwargs

        assert result == "Final answer based on gathered info"

    def test_sequential_early_termination(
        self, ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """Test that Claude can stop naturally after 1 round without using all rounds"""
        # First tool use
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.id = "tool_1"
        mock_tool_block.input = {"query": "AI basics"}

        mock_response_1 = MagicMock()
        mock_response_1.content = [mock_tool_block]
        mock_response_1.stop_reason = "tool_use"

        # Second response - Claude decides it has enough info (end_turn)
        mock_response_2 = MagicMock()
        mock_response_2.content = [MagicMock(text="AI is artificial intelligence")]
        mock_response_2.stop_reason = "end_turn"

        mock_anthropic_client.messages.create.side_effect = [
            mock_response_1,  # Initial with tool use
            mock_response_2,  # Natural completion after 1 round
        ]

        result = ai_generator.generate_response(
            query="What is AI?",
            tools=mock_tool_manager.get_tool_definitions(),
            tool_manager=mock_tool_manager,
        )

        # Only 2 API calls (didn't use all 2 rounds)
        assert mock_anthropic_client.messages.create.call_count == 2

        assert result == "AI is artificial intelligence"

    def test_messages_accumulate_across_rounds(
        self, ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """Test that conversation context accumulates correctly across rounds"""
        # Initial response (from generate_response's first call)
        mock_tool_block_1 = MagicMock()
        mock_tool_block_1.type = "tool_use"
        mock_tool_block_1.name = "search_course_content"
        mock_tool_block_1.id = "tool_1"
        mock_tool_block_1.input = {"query": "first search"}

        mock_response_1 = MagicMock()
        mock_response_1.content = [mock_tool_block_1]
        mock_response_1.stop_reason = "tool_use"

        # Round 1 response (second API call in while loop)
        mock_tool_block_2 = MagicMock()
        mock_tool_block_2.type = "tool_use"
        mock_tool_block_2.name = "search_course_content"
        mock_tool_block_2.id = "tool_2"
        mock_tool_block_2.input = {"query": "second search"}

        mock_response_2 = MagicMock()
        mock_response_2.content = [mock_tool_block_2]
        mock_response_2.stop_reason = "tool_use"

        # Final synthesis (after round 2, tools removed)
        mock_final_response = MagicMock()
        mock_final_response.content = [MagicMock(text="Final answer")]
        mock_final_response.stop_reason = "end_turn"

        # API call sequence:
        # Call 0: Initial (from generate_response) -> returns mock_response_1 (tool_use)
        # Call 1: After round 1 tools executed -> returns mock_response_2 (tool_use)
        # Call 2: After round 2 tools executed (max rounds) -> returns mock_final_response
        mock_anthropic_client.messages.create.side_effect = [
            mock_response_1,
            mock_response_2,
            mock_final_response,
        ]

        ai_generator.generate_response(
            query="Test query",
            tools=mock_tool_manager.get_tool_definitions(),
            tool_manager=mock_tool_manager,
        )

        # Verify 3 API calls total
        assert mock_anthropic_client.messages.create.call_count == 3

        # Call 1 (index 1): After executing tools from response_1, before round 2
        # Messages: [user query, assistant tool_use_1, user tool_result_1]
        second_call_kwargs = mock_anthropic_client.messages.create.call_args_list[1][1]
        messages_after_round_1 = second_call_kwargs["messages"]

        assert len(messages_after_round_1) == 3
        assert messages_after_round_1[0]["role"] == "user"  # Original query
        assert messages_after_round_1[1]["role"] == "assistant"  # Tool use 1
        assert messages_after_round_1[2]["role"] == "user"  # Tool result 1

        # Call 2 (index 2): Final synthesis after round 2 tools executed
        # Messages: [user query, asst tool_1, user result_1, asst tool_2, user result_2]
        final_call_kwargs = mock_anthropic_client.messages.create.call_args_list[2][1]
        messages_final = final_call_kwargs["messages"]

        assert len(messages_final) == 5
        assert messages_final[0]["role"] == "user"  # Original query
        assert messages_final[1]["role"] == "assistant"  # Tool use 1
        assert messages_final[2]["role"] == "user"  # Tool result 1
        assert messages_final[3]["role"] == "assistant"  # Tool use 2
        assert messages_final[4]["role"] == "user"  # Tool result 2

    def test_system_prompt_consistent_across_rounds(
        self, ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """Test that system prompt remains the same across all API calls"""
        # Setup two-round scenario
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.id = "tool_1"
        mock_tool_block.input = {"query": "test"}

        mock_tool_response = MagicMock()
        mock_tool_response.content = [mock_tool_block]
        mock_tool_response.stop_reason = "tool_use"

        mock_final_response = MagicMock()
        mock_final_response.content = [MagicMock(text="Answer")]
        mock_final_response.stop_reason = "end_turn"

        mock_anthropic_client.messages.create.side_effect = [
            mock_tool_response,
            mock_final_response,
        ]

        ai_generator.generate_response(
            query="Test",
            conversation_history="User: Hi\nAssistant: Hello",
            tools=mock_tool_manager.get_tool_definitions(),
            tool_manager=mock_tool_manager,
        )

        # Extract system prompts from both calls
        first_call_system = mock_anthropic_client.messages.create.call_args_list[0][1][
            "system"
        ]
        second_call_system = mock_anthropic_client.messages.create.call_args_list[1][1][
            "system"
        ]

        # Should be identical
        assert first_call_system == second_call_system
        assert "Previous conversation:" in first_call_system
        assert "Hi" in first_call_system

    def test_tool_execution_error_in_round_2(self, ai_generator, mock_anthropic_client):
        """Test graceful error handling when tool execution fails in round 2"""
        # Round 1 succeeds
        mock_tool_block_1 = MagicMock()
        mock_tool_block_1.type = "tool_use"
        mock_tool_block_1.name = "search_course_content"
        mock_tool_block_1.id = "tool_1"
        mock_tool_block_1.input = {"query": "test"}

        mock_response_1 = MagicMock()
        mock_response_1.content = [mock_tool_block_1]
        mock_response_1.stop_reason = "tool_use"

        # Round 2 - tool execution will fail
        mock_tool_block_2 = MagicMock()
        mock_tool_block_2.type = "tool_use"
        mock_tool_block_2.name = "search_course_content"
        mock_tool_block_2.id = "tool_2"
        mock_tool_block_2.input = {"query": "test2"}

        mock_response_2 = MagicMock()
        mock_response_2.content = [mock_tool_block_2]
        mock_response_2.stop_reason = "tool_use"

        mock_anthropic_client.messages.create.side_effect = [
            mock_response_1,
            mock_response_2,
        ]

        # Create mock tool manager that fails on second execution
        mock_tool_manager = MagicMock()
        call_count = [0]

        def execute_tool_side_effect(name, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("Tool execution failed")
            return "Success"

        mock_tool_manager.execute_tool.side_effect = execute_tool_side_effect
        mock_tool_manager.get_tool_definitions.return_value = [
            {"name": "search_course_content"}
        ]

        result = ai_generator.generate_response(
            query="Test",
            tools=mock_tool_manager.get_tool_definitions(),
            tool_manager=mock_tool_manager,
        )

        # Should return error message
        assert "error occurred while executing tools" in result.lower()

    def test_no_tools_after_max_rounds(
        self, ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """Test that final API call after max rounds has tools removed"""
        # Mock always returning tool_use
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.id = "tool_x"
        mock_tool_block.input = {"query": "test"}

        mock_tool_response = MagicMock()
        mock_tool_response.content = [mock_tool_block]
        mock_tool_response.stop_reason = "tool_use"

        mock_final_response = MagicMock()
        mock_final_response.content = [MagicMock(text="Final")]
        mock_final_response.stop_reason = "end_turn"

        mock_anthropic_client.messages.create.side_effect = [
            mock_tool_response,  # Round 1
            mock_tool_response,  # Round 2
            mock_final_response,  # Final (tools removed)
        ]

        ai_generator.generate_response(
            query="Test",
            tools=mock_tool_manager.get_tool_definitions(),
            tool_manager=mock_tool_manager,
        )

        # Verify first two calls have tools
        first_call_kwargs = mock_anthropic_client.messages.create.call_args_list[0][1]
        second_call_kwargs = mock_anthropic_client.messages.create.call_args_list[1][1]
        assert "tools" in first_call_kwargs
        assert "tools" in second_call_kwargs

        # Verify third call does NOT have tools (forced synthesis)
        third_call_kwargs = mock_anthropic_client.messages.create.call_args_list[2][1]
        assert "tools" not in third_call_kwargs
        assert "tool_choice" not in third_call_kwargs

    def test_backward_compatibility_single_round(
        self, ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """Test that single-round tool calling still works (backward compatibility)"""
        # Single tool use followed by end_turn
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.id = "tool_1"
        mock_tool_block.input = {"query": "AI"}

        mock_response_1 = MagicMock()
        mock_response_1.content = [mock_tool_block]
        mock_response_1.stop_reason = "tool_use"

        mock_response_2 = MagicMock()
        mock_response_2.content = [MagicMock(text="AI is artificial intelligence")]
        mock_response_2.stop_reason = "end_turn"

        mock_anthropic_client.messages.create.side_effect = [
            mock_response_1,
            mock_response_2,
        ]

        result = ai_generator.generate_response(
            query="What is AI?",
            tools=mock_tool_manager.get_tool_definitions(),
            tool_manager=mock_tool_manager,
        )

        # Should work exactly like before - 2 API calls
        assert mock_anthropic_client.messages.create.call_count == 2
        assert result == "AI is artificial intelligence"
