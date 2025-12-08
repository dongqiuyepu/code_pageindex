"""
Distributed Code Agent
Works with distributed index structure (separate file per directory).
"""

import os
import json
import subprocess
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from src.distributed_models import RepositoryIndex, DirectoryIndex


# ============================================================================
# Agent State
# ============================================================================

class AgentState(TypedDict):
    """State of the distributed code agent."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    files_investigated: list  # Track files that have been read
    iteration_count: int  # Track number of iterations


# ============================================================================
# Bash Tool
# ============================================================================

# Global state for tracking files (will be updated by tool)
_files_investigated = []

@tool
def bash(command: str) -> str:
    """
    Execute bash commands to navigate hierarchical distributed index and read files.
    
    Use this tool to:
    - Read repository index: cat distributed_index/repo_index.json
    - Read root directory: cat distributed_index/index.json
    - Read subdirectory: cat distributed_index/src/index.json
    - Navigate deeper: cat distributed_index/src/openai/index.json
    - Search in index: cat distributed_index/src/openai/index.json | jq '.files[] | select(.relative_path | contains("auth"))'
    - Read code files: cat /path/to/file.py
    - Search code: grep -r "pattern" /path/to/dir
    
    Args:
        command: Bash command to execute
        
    Returns:
        Command output or error message
    """
    global _files_investigated
    
    try:
        # Security: restrict to safe commands
        dangerous_commands = ['rm', 'mv', 'cp', 'chmod', 'chown', 'sudo', 'su', '>', '>>', '&&', '||']
        for dangerous in dangerous_commands:
            if dangerous in command:
                return f"Error: Command contains restricted operation: {dangerous}"
        
        # Track files being read
        if 'cat ' in command and '.py' in command and 'index.json' not in command:
            # Extract file path from cat command
            parts = command.split()
            for i, part in enumerate(parts):
                if part == 'cat' and i + 1 < len(parts):
                    file_path = parts[i + 1]
                    if file_path not in _files_investigated:
                        _files_investigated.append(file_path)
        
        # Execute command
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,  # Increased timeout for thorough research
            cwd=os.getcwd()
        )
        
        output = result.stdout if result.stdout else result.stderr
        
        # Limit output size but allow larger outputs for thorough research
        if len(output) > 50000:
            output = output[:50000] + "\n... (output truncated, use grep or sed for specific sections)"
        
        return output if output else "Command executed successfully (no output)"
        
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds"
    except Exception as e:
        return f"Error executing command: {str(e)}"


# ============================================================================
# Distributed Code Agent
# ============================================================================

class DistributedCodeAgent:
    """
    Code agent that uses distributed index structure.
    Each directory has its own index file.
    """
    
    def __init__(
        self,
        repo_index: RepositoryIndex,
        index_root_dir: str,
        model: str = "gpt-4o",
        verbose: bool = True
    ):
        """
        Initialize distributed code agent.
        
        Args:
            repo_index: Repository index
            index_root_dir: Root directory containing distributed index
            model: OpenAI model to use
            verbose: Whether to print reasoning steps
        """
        self.repo_index = repo_index
        self.index_root_dir = os.path.abspath(index_root_dir)
        self.model = model
        self.verbose = verbose
        
        # Initialize LLM
        self.llm = ChatOpenAI(model=model, temperature=0)
        
        # Define tools (only bash)
        self.tools = [bash]
        
        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # Build graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the agent graph."""
        
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", ToolNode(self.tools))
        
        # Set entry point
        workflow.set_entry_point("agent")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "tools",
                "end": END
            }
        )
        
        # Add edge from tools back to agent
        workflow.add_edge("tools", "agent")
        
        return workflow.compile()
    
    def _agent_node(self, state: AgentState) -> AgentState:
        """Agent reasoning node with research tracking."""
        messages = state["messages"]
        iteration_count = state.get("iteration_count", 0) + 1
        files_investigated = state.get("files_investigated", [])
        
        # Add research progress reminder every few iterations
        if iteration_count > 0 and iteration_count % 5 == 0:
            progress_msg = HumanMessage(content=f"""
RESEARCH PROGRESS CHECK (Iteration {iteration_count}):
- Files investigated so far: {len(files_investigated)}
- Files: {', '.join(files_investigated[-10:]) if files_investigated else 'None yet'}

REMINDER: Have you investigated enough files? 
- Simple questions need 5-10 files minimum
- Complex questions need 10-20 files minimum

If you haven't reached the minimum, continue investigating more files.
If you have enough information, you may provide your comprehensive answer.
""")
            messages = list(messages) + [progress_msg]
        
        response = self.llm_with_tools.invoke(messages)
        
        return {
            "messages": [response],
            "iteration_count": iteration_count,
            "files_investigated": files_investigated
        }
    
    def _should_continue(self, state: AgentState) -> str:
        """Determine if agent should continue or end."""
        messages = state["messages"]
        last_message = messages[-1]
        
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "continue"
        return "end"
    
    def _create_system_prompt(self) -> str:
        """Create system prompt with hierarchical distributed index information."""
        
        return f"""You are a code research agent with access to a HIERARCHICAL DISTRIBUTED code index.

HIERARCHICAL INDEX STRUCTURE:
The code repository is indexed with a HIERARCHICAL FOLDER STRUCTURE that MIRRORS the code repository:

1. Repository Index: {self.index_root_dir}/repo_index.json
   - Contains repository metadata and reference to root directory index
   - Use this to understand overall repository structure
   
2. Directory Indices: HIERARCHICAL STRUCTURE (mirrors code repo)
   - Root directory: {self.index_root_dir}/index.json
   - Subdirectories: {self.index_root_dir}/{{path}}/index.json
   - Examples:
     * Root: {self.index_root_dir}/index.json
     * src/: {self.index_root_dir}/src/index.json
     * src/openai/: {self.index_root_dir}/src/openai/index.json
     * src/openai/resources/: {self.index_root_dir}/src/openai/resources/index.json
   
   Each index.json contains:
     * File metadata (INLINE, full details including summaries and code elements)
     * Subdirectory references (POINTERS with summaries)
     * Statistics (file count, line count)
     * Bottom-up aggregated summary
   
3. Code Files: Full source code at file_path
   - Read actual code when you need implementation details

IMPORTANT - PRE-COMPUTED STATISTICS:
The repo_index.json contains PRE-COMPUTED statistics that you should use DIRECTLY:
- total_files: Total number of files in repository
- total_lines: Total lines of code
- total_classes: Total number of classes
- total_functions: Total number of functions
- total_methods: Total number of methods

For questions about counts/statistics, ALWAYS check repo_index.json FIRST:
cat {self.index_root_dir}/repo_index.json | jq '.total_classes'

DO NOT use grep to count classes/functions - the statistics are already computed!

NAVIGATION STRATEGY:
1. Start with repo_index.json to understand structure AND get statistics:
   cat {self.index_root_dir}/repo_index.json

2. Load root directory index:
   cat {self.index_root_dir}/index.json
   
3. Navigate to subdirectories by following the hierarchical path:
   - To explore src/: cat {self.index_root_dir}/src/index.json
   - To explore src/openai/: cat {self.index_root_dir}/src/openai/index.json
   - To explore src/openai/resources/: cat {self.index_root_dir}/src/openai/resources/index.json
   
4. Each directory index shows:
   - Files in that directory (INLINE with full metadata)
   - Subdirectories (references with summaries)
   - You can navigate deeper by following the path

5. Read file metadata INLINE in directory indices:
   - Files are stored with full metadata in their parent directory's index
   - Includes: summary, elements (classes/functions), imports, line count
   
6. Read actual code files when needed:
   cat /path/to/file.py

EXAMPLE WORKFLOW FOR STATISTICS:
Question: "How many classes does this repo have?"
# Step 1: Read pre-computed statistics from repo_index.json
cat {self.index_root_dir}/repo_index.json | jq '.total_classes'
# Answer: Use the value directly (e.g., 928)

Question: "How many lines of code?"
# Step 1: Read pre-computed statistics
cat {self.index_root_dir}/repo_index.json | jq '.total_lines'
# Answer: Use the value directly

EXAMPLE WORKFLOW FOR CODE EXPLORATION:
# Step 1: Understand repository
cat {self.index_root_dir}/repo_index.json

# Step 2: See top-level structure (root directory)
cat {self.index_root_dir}/index.json

# Step 3: Navigate to src directory
cat {self.index_root_dir}/src/index.json

# Step 4: Navigate to src/openai directory
cat {self.index_root_dir}/src/openai/index.json

# Step 5: Find files in directory (inline in index)
cat {self.index_root_dir}/src/openai/index.json | jq '.files[] | select(.relative_path | contains("client"))'

# Step 6: Read actual code
cat /path/to/src/openai/_client.py

DEEP RESEARCH WORKFLOW:
You MUST perform THOROUGH, COMPREHENSIVE research before answering. This means:

1. UNDERSTAND THE QUESTION DEEPLY
   - Break down what the user is really asking
   - Identify all aspects that need investigation
   - List multiple angles to explore

2. COMPREHENSIVE INDEX EXPLORATION
   - Start with repo_index.json for overview
   - Load relevant directory indices
   - Search with multiple keywords
   - Find ALL related files, not just first match
   - Look for: implementations, helpers, utilities, tests, examples

3. SYSTEMATIC FILE INVESTIGATION
   - Create list of ALL relevant files from directory indices
   - Read each file systematically using bash
   - For large files, use grep to find specific sections first
   - Follow imports and dependencies
   - Check both implementation and usage

4. DEEP CODE ANALYSIS
   - Read main implementation files completely
   - Read related helper/utility files
   - Check how classes/functions are used in other files
   - Look for patterns across multiple files
   - Find examples or tests that show usage
   - Understand the full context, not just isolated pieces

5. CROSS-REFERENCE AND VERIFY
   - Cross-check information across multiple files
   - Verify your understanding is complete
   - Look for edge cases or special handling
   - Check configuration or initialization code
   - Find documentation or comments

6. SYNTHESIZE COMPREHENSIVE ANSWER
   - Combine insights from ALL investigated files
   - Provide complete picture with multiple perspectives
   - Cite specific files and line numbers
   - Mention related components
   - Include examples from actual code

RESEARCH DEPTH REQUIREMENTS:
- Investigate MINIMUM 5-10 files for simple questions
- Investigate MINIMUM 10-20 files for complex questions
- Read FULL files when they're relevant (not just snippets)
- Follow the code flow across multiple files
- Investigate both high-level and low-level details

RESEARCH STRATEGIES:

Strategy 1: Keyword Expansion
- Search with multiple related terms
- Example: cat {self.index_root_dir}/src/openai/index.json | jq '.files[] | select(.summary | contains("auth") or contains("login") or contains("credential"))'

Strategy 2: Directory Exploration
- Find all files in relevant directories
- Example: cat {self.index_root_dir}/src/openai/resources/index.json | jq '.files[]'

Strategy 3: Dependency Following
- When you see imports, investigate them
- Example: Found "from _auth import AuthHandler" → cat {self.index_root_dir}/src/openai/index.json | jq '.files[] | select(.relative_path | contains("_auth"))'

Strategy 4: Usage Pattern Analysis
- Find where a class/function is used
- Example: grep -r "ClassName" /path/to/repo

Strategy 5: Hierarchical Investigation
- Start high-level (main classes)
- Dive into details (helper functions)
- Check examples (test files, examples directory)
- Navigate hierarchically: root → src → openai → resources

EXAMPLE DEEP RESEARCH:
Question: "How does authentication work?"

Step 1: Broad search in multiple directories
cat {self.index_root_dir}/index.json | jq '.subdirectories[] | select(.summary | contains("auth"))'
cat {self.index_root_dir}/src/openai/index.json | jq '.files[] | select(.summary | contains("auth"))'

Step 2: Read ALL relevant files
cat /path/to/_client.py
cat /path/to/_auth.py
cat /path/to/_credentials.py
cat /path/to/_api_key.py
... (continue until 10-20 files)

Step 3: Follow dependencies
grep -r "import.*auth" /path/to/repo
cat /path/to/each/related/file.py

Step 4: Cross-reference
grep -r "AuthHandler" /path/to/repo
cat /path/to/usage/examples.py

Step 5: Synthesize comprehensive answer with citations

QUALITY CHECKLIST BEFORE ANSWERING:
□ Have I investigated at least 5-10 relevant files?
□ Have I read the main implementation files completely?
□ Have I followed imports and dependencies?
□ Have I checked how components are used together?
□ Have I looked at examples or tests?
□ Have I verified my understanding across multiple files?
□ Can I cite specific files and line numbers?
□ Is my answer comprehensive and complete?

If you answer NO to any of these, DO MORE RESEARCH before answering.

Remember: DEPTH and THOROUGHNESS are more important than speed. Take time to investigate comprehensively.

REPOSITORY INFORMATION:
- Name: {self.repo_index.name}
- Total Files: {self.repo_index.total_files}
- Total Directories: {self.repo_index.total_directories}
- Total Lines: {self.repo_index.total_lines:,}
- Primary Language: {self.repo_index.primary_language}
- Summary: {self.repo_index.summary}

INDEX LOCATION:
- Repository Index: {self.index_root_dir}/repo_index.json
- Directory Indices: {self.index_root_dir}/.index/
- Root Index: {self.repo_index.root_index_path}

Begin your research now. Use the bash tool to navigate the distributed index and read files."""

    def query(self, question: str) -> dict:
        """
        Process a query about the codebase.
        
        Args:
            question: User's question about the code
            
        Returns:
            Dictionary with answer and reasoning trace
        """
        global _files_investigated
        _files_investigated = []  # Reset for new query
        
        print(f"\n{'='*80}")
        print(f"DISTRIBUTED CODE AGENT - DEEP RESEARCH MODE")
        print(f"{'='*80}")
        print(f"Question: {question}")
        print(f"Repository: {self.repo_index.name}")
        print(f"Index: {self.index_root_dir}")
        print(f"Mode: Distributed (separate file per directory)")
        print(f"{'='*80}\n")
        
        # Create system message
        system_message = SystemMessage(content=self._create_system_prompt())
        
        # Create initial state
        initial_state = {
            "messages": [system_message, HumanMessage(content=question)],
            "files_investigated": [],
            "iteration_count": 0
        }
        
        # Run the graph with increased recursion limit
        final_state = self.graph.invoke(
            initial_state,
            config={"recursion_limit": 100}  # Allow more iterations for deep research
        )
        
        # Extract reasoning trace
        reasoning_trace = self._extract_reasoning_trace(final_state["messages"])
        
        # Get final answer
        final_answer = final_state["messages"][-1].content
        
        # Get files investigated
        files_investigated = _files_investigated
        
        # Print reasoning if verbose
        if self.verbose:
            print(f"\n{'─'*80}")
            print("RESEARCH SUMMARY:")
            print(f"{'─'*80}")
            print(f"Total iterations: {final_state.get('iteration_count', 0)}")
            print(f"Files investigated: {len(files_investigated)}")
            if files_investigated:
                print(f"\nFiles read:")
                for f in files_investigated[:20]:  # Show first 20
                    print(f"  - {f}")
                if len(files_investigated) > 20:
                    print(f"  ... and {len(files_investigated) - 20} more")
            
            print(f"\n{'─'*80}")
            print("REASONING TRACE:")
            print(f"{'─'*80}")
            for i, step in enumerate(reasoning_trace, 1):
                print(f"\nStep {i}: {step['action']}")
                if step.get('command'):
                    print(f"  Command: {step['command'][:100]}...")
                if step.get('output') and len(step.get('output', '')) < 500:
                    print(f"  Output: {step['output'][:200]}...")
            
            print(f"\n{'─'*80}")
            print("FINAL ANSWER:")
            print(f"{'─'*80}")
            print(final_answer)
            print()
        
        return {
            "question": question,
            "answer": final_answer,
            "reasoning_trace": reasoning_trace,
            "total_steps": len(reasoning_trace),
            "files_investigated": files_investigated,
            "total_files": len(files_investigated),
            "iterations": final_state.get("iteration_count", 0),
            "messages": final_state["messages"]
        }
    
    def _extract_reasoning_trace(self, messages: list) -> list:
        """Extract reasoning trace from messages."""
        
        trace = []
        
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    trace.append({
                        "action": "bash_call",
                        "command": tool_call.get("args", {}).get("command", ""),
                        "tool_call_id": tool_call.get("id", "")
                    })
            elif hasattr(msg, "content") and msg.content:
                if "bash_output" in str(type(msg)):
                    trace.append({
                        "action": "bash_output",
                        "output": msg.content[:500]
                    })
        
        return trace
    
    def interactive(self):
        """Run agent in interactive mode."""
        
        print(f"\n{'='*80}")
        print(f"DISTRIBUTED CODE AGENT - INTERACTIVE MODE")
        print(f"{'='*80}")
        print(f"Repository: {self.repo_index.name}")
        print(f"Index: {self.index_root_dir}")
        print(f"Type 'exit' or 'quit' to end session")
        print(f"{'='*80}\n")
        
        while True:
            try:
                question = input("\nYour question: ").strip()
                
                if question.lower() in ['exit', 'quit', 'q']:
                    print("\nGoodbye!")
                    break
                
                if not question:
                    continue
                
                result = self.query(question)
                
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}")
                continue


def create_distributed_agent(
    index_root_dir: str,
    model: str = "gpt-4o",
    verbose: bool = True
) -> DistributedCodeAgent:
    """
    Create a distributed code agent from index directory.
    
    Args:
        index_root_dir: Root directory containing distributed index
        model: OpenAI model to use
        verbose: Whether to print reasoning steps
        
    Returns:
        DistributedCodeAgent instance
    """
    # Load repository index
    repo_index_path = os.path.join(index_root_dir, "repo_index.json")
    
    if not os.path.exists(repo_index_path):
        raise FileNotFoundError(f"Repository index not found: {repo_index_path}")
    
    with open(repo_index_path, 'r') as f:
        repo_data = json.load(f)
        repo_index = RepositoryIndex(**repo_data)
    
    return DistributedCodeAgent(
        repo_index=repo_index,
        index_root_dir=index_root_dir,
        model=model,
        verbose=verbose
    )
