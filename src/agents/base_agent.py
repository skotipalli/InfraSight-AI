"""
InfraSight-AI: Base Agent Class
Foundation for all LangChain-based agents.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from langchain_community.llms import Ollama
    from langchain.agents import AgentExecutor, create_react_agent
    from langchain.prompts import PromptTemplate
    from langchain.tools import Tool
    from langchain.memory import ConversationBufferMemory
except ImportError:
    print("LangChain not installed. Run: pip install langchain langchain-community")

from config.settings import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    """Standardized agent response."""
    success: bool
    result: Any
    reasoning: str
    confidence: float
    metadata: Dict[str, Any]


class BaseAgent(ABC):
    """Base class for all InfraSight agents."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.llm = None
        self.memory = None
        self.tools = []
        self.agent_executor = None
        self._initialize()

    def _initialize(self):
        """Initialize the LLM and memory."""
        try:
            self.llm = Ollama(
                base_url=config.ollama.base_url,
                model=config.ollama.model,
                temperature=0.1,  # Low temperature for consistent outputs
            )
            self.memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
            logger.info(f"Initialized {self.name} with Ollama model {config.ollama.model}")
        except Exception as e:
            logger.warning(f"Could not initialize LLM: {e}. Agent will run in mock mode.")
            self.llm = None

    @abstractmethod
    def get_tools(self) -> List[Tool]:
        """Return the tools available to this agent."""
        pass

    @abstractmethod
    def get_prompt_template(self) -> str:
        """Return the prompt template for this agent."""
        pass

    def build_agent(self):
        """Build the agent executor."""
        if self.llm is None:
            logger.warning("LLM not available. Agent will not be built.")
            return

        self.tools = self.get_tools()

        prompt = PromptTemplate.from_template(self.get_prompt_template())

        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )

        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            max_iterations=5,
            early_stopping_method="generate",
            handle_parsing_errors=True
        )

        logger.info(f"Built agent executor for {self.name} with {len(self.tools)} tools")

    @abstractmethod
    def run(self, input_data: Dict[str, Any]) -> AgentResponse:
        """Execute the agent with given input."""
        pass

    def _create_response(
        self,
        success: bool,
        result: Any,
        reasoning: str = "",
        confidence: float = 0.0,
        **metadata
    ) -> AgentResponse:
        """Create a standardized response."""
        return AgentResponse(
            success=success,
            result=result,
            reasoning=reasoning,
            confidence=confidence,
            metadata=metadata
        )


class Neo4jTool:
    """Helper class for Neo4j operations."""

    def __init__(self):
        self.driver = None
        self._connect()

    def _connect(self):
        """Connect to Neo4j."""
        try:
            from neo4j import GraphDatabase
            self.driver = GraphDatabase.driver(
                config.neo4j.uri,
                auth=(config.neo4j.user, config.neo4j.password)
            )
        except Exception as e:
            logger.warning(f"Could not connect to Neo4j: {e}")

    def query(self, cypher: str, parameters: Dict = None) -> List[Dict]:
        """Execute a Cypher query."""
        if self.driver is None:
            return []

        with self.driver.session(database=config.neo4j.database) as session:
            result = session.run(cypher, parameters or {})
            return result.data()

    def close(self):
        """Close the connection."""
        if self.driver:
            self.driver.close()


class PostgresTool:
    """Helper class for PostgreSQL operations."""

    def __init__(self):
        self.conn = None
        self._connect()

    def _connect(self):
        """Connect to PostgreSQL."""
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            self.conn = psycopg2.connect(**config.postgres.dsn)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        except Exception as e:
            logger.warning(f"Could not connect to PostgreSQL: {e}")

    def query(self, sql: str, parameters: tuple = None) -> List[Dict]:
        """Execute a SQL query."""
        if self.conn is None:
            return []

        self.cursor.execute(sql, parameters)
        return self.cursor.fetchall()

    def close(self):
        """Close the connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
