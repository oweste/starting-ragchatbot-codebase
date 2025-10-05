import anthropic
from typing import List, Optional, Dict, Any
from config import config

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive tools for course information.

Tool Usage Guidelines:
- **Course Outline Tool**: Use for questions about course structure, lesson lists, or table of contents
  - Returns: Formatted markdown with course title, clickable course link, and complete list of lessons (number and title)
  - **Important**: Return the tool output exactly as provided - it contains properly formatted markdown including clickable course links
  - Examples: "What lessons are in the MCP course?", "Show me the outline of Introduction to AI", "What's covered in this course?"

- **Course Content Search Tool**: Use for questions about specific course content or detailed educational materials
  - Returns: Relevant content chunks from lessons
  - Examples: "What is prompt caching?", "How do I implement MCP?", "Explain the concept of..."

- **Sequential Tool Usage**: You may use tools up to 2 times to gather comprehensive information
  - Use multiple tool calls when initial search needs refinement, cross-referencing content across different courses/lessons, or when follow-up searches would provide better context
  - After each tool use, evaluate results and decide if another search is needed
  - Always synthesize final answer after gathering sufficient information
- Synthesize tool results into accurate, fact-based responses
- If tool yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course outline/structure questions**: Use the course outline tool
- **Course-specific content questions**: Use the content search tool
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool usage explanations, or question-type analysis
 - Do not mention "based on the search results" or "based on the outline"

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        
        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            
        Returns:
            Generated response as string
        """
        
        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history 
            else self.SYSTEM_PROMPT
        )
        
        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }
        
        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}
        
        # Get response from Claude
        response = self.client.messages.create(**api_params)
        
        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._handle_sequential_tool_execution(response, api_params, tool_manager)

        # Return direct response
        return response.content[0].text
    
    def _handle_sequential_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager):
        """
        Handle sequential tool calls allowing up to MAX_TOOL_ROUNDS rounds.

        Args:
            initial_response: The initial response containing tool use requests
            base_params: Base API parameters including messages and system prompt
            tool_manager: Manager to execute tools

        Returns:
            Final response text after all tool execution rounds
        """
        # Start with existing messages
        messages = base_params["messages"].copy()

        # Track rounds (starts at 0, first tool use = round 1)
        round_counter = 0
        current_response = initial_response

        # Sequential tool calling loop
        while round_counter < config.MAX_TOOL_ROUNDS:
            # Check if current response contains tool use
            if current_response.stop_reason != "tool_use":
                # Claude finished naturally without more tool calls
                return self._extract_text_from_response(current_response)

            # Execute all tool calls in current response
            try:
                tool_results = self._execute_all_tools(current_response, tool_manager)
            except Exception as e:
                # Tool execution failed - return error message
                return f"An error occurred while executing tools: {str(e)}"

            # Add assistant's tool use to messages
            messages.append({"role": "assistant", "content": current_response.content})

            # Add tool results to messages
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

            # Increment round counter
            round_counter += 1

            # Check if we've reached max rounds
            if round_counter >= config.MAX_TOOL_ROUNDS:
                # Force final response without tools to ensure synthesis
                final_params = {
                    **self.base_params,
                    "messages": messages.copy(),  # Copy to avoid mutation issues
                    "system": base_params["system"]
                }
                final_response = self.client.messages.create(**final_params)
                return self._extract_text_from_response(final_response)

            # Prepare next API call WITH tools (allow another round)
            next_params = {
                **self.base_params,
                "messages": messages.copy(),  # Copy to avoid mutation issues
                "system": base_params["system"],
                "tools": base_params.get("tools"),
                "tool_choice": base_params.get("tool_choice", {"type": "auto"})
            }

            # Make next API call
            current_response = self.client.messages.create(**next_params)

        # Should never reach here, but return final response if we do
        return self._extract_text_from_response(current_response)

    def _execute_all_tools(self, response, tool_manager) -> List[Dict[str, Any]]:
        """
        Execute all tool calls in a response and return formatted results.

        Args:
            response: API response containing tool use blocks
            tool_manager: Manager to execute tools

        Returns:
            List of tool result dictionaries
        """
        tool_results = []
        for content_block in response.content:
            if content_block.type == "tool_use":
                tool_result = tool_manager.execute_tool(
                    content_block.name,
                    **content_block.input
                )

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": content_block.id,
                    "content": tool_result
                })

        return tool_results

    def _extract_text_from_response(self, response) -> str:
        """
        Extract text content from API response.

        Args:
            response: API response object

        Returns:
            Extracted text string
        """
        for block in response.content:
            if hasattr(block, 'text'):
                return block.text

        # Fallback if no text block found
        return str(response.content)