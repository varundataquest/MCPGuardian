#!/usr/bin/env python3
"""
MCP Server Connector Agent - Interactive Mode

This agent actually connects the user's agent to the MCP server
by asking for their specific requirements and generating the actual connection code.
"""

import json
import os
import sys
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import asyncio
from pathlib import Path

class AgentType(Enum):
    LANGCHAIN = "langchain"
    LANGGRAPH = "langgraph"
    AUTOGEN = "autogen"
    CUSTOM = "custom"

@dataclass
class UserRequirements:
    """User's agent requirements"""
    agent_type: AgentType
    agent_name: str
    agent_description: str
    preferred_language: str
    deployment_platform: str
    environment: str
    region: str
    app_name: str
    app_type: str
    additional_requirements: List[str]

@dataclass
class ConnectionResult:
    """Result of the connection process"""
    success: bool
    connection_code: str
    config_file: str
    requirements_file: str
    setup_script: str
    test_script: str
    error_message: Optional[str] = None

class InteractiveMCPConnector:
    """Interactive connector that actually connects the user's agent to MCP servers"""
    
    def __init__(self):
        self.server_info = {
            "name": "deployment-mcp-server",
            "endpoint": "https://api.deployer-mcp.com",
            "score": 89,
            "auth": "oauth",
            "details": "One-click deployment of web apps to AWS/GCP/Azure with Docker and Kubernetes"
        }
    
    def run(self) -> ConnectionResult:
        """Run the interactive connector"""
        print("🔗 MCP Server Connector Agent - Interactive Mode")
        print("=" * 60)
        print(f"Connecting: {self.server_info['name']} (Score: {self.server_info['score']}/100)")
        print(f"Endpoint: {self.server_info['endpoint']}")
        print(f"Auth: {self.server_info['auth']}")
        print(f"Details: {self.server_info['details']}")
        print()
        
        try:
            # Get user requirements
            requirements = self._get_user_requirements()
            
            # Generate connection code
            connection_code = self._generate_connection_code(requirements)
            
            # Generate configuration files
            config_file = self._generate_config_file(requirements)
            requirements_file = self._generate_requirements_file(requirements)
            setup_script = self._generate_setup_script(requirements)
            test_script = self._generate_test_script(requirements)
            
            # Save files
            self._save_files(requirements, connection_code, config_file, requirements_file, setup_script, test_script)
            
            # Display results
            self._display_results(requirements, connection_code)
            
            return ConnectionResult(
                success=True,
                connection_code=connection_code,
                config_file=config_file,
                requirements_file=requirements_file,
                setup_script=setup_script,
                test_script=test_script
            )
            
        except Exception as e:
            return ConnectionResult(
                success=False,
                connection_code="",
                config_file="",
                requirements_file="",
                setup_script="",
                test_script="",
                error_message=str(e)
            )
    
    def _get_user_requirements(self) -> UserRequirements:
        """Get user requirements interactively"""
        print("📋 Let's configure your agent connection!")
        print()
        
        # Agent type
        print("What type of agent are you building?")
        for i, agent_type in enumerate(AgentType, 1):
            print(f"  {i}. {agent_type.value.title()}")
        
        while True:
            try:
                choice = int(input("\nEnter your choice (1-4): ")) - 1
                if 0 <= choice < len(AgentType):
                    agent_type = list(AgentType)[choice]
                    break
                else:
                    print("Invalid choice. Please enter 1-4.")
            except ValueError:
                print("Please enter a number.")
        
        # Agent details
        agent_name = input("\nWhat's your agent's name? (e.g., 'DeploymentBot'): ").strip()
        if not agent_name:
            agent_name = "DeploymentAgent"
        
        agent_description = input("Describe what your agent does: ").strip()
        if not agent_description:
            agent_description = "Deploys web applications with one-click"
        
        # Deployment preferences
        print("\nDeployment Platform:")
        platforms = ["aws", "gcp", "azure", "docker", "kubernetes"]
        for i, platform in enumerate(platforms, 1):
            print(f"  {i}. {platform.upper()}")
        
        while True:
            try:
                choice = int(input("Enter your choice (1-5): ")) - 1
                if 0 <= choice < len(platforms):
                    deployment_platform = platforms[choice]
                    break
                else:
                    print("Invalid choice. Please enter 1-5.")
            except ValueError:
                print("Please enter a number.")
        
        environment = input("Environment (development/staging/production): ").strip().lower()
        if environment not in ["development", "staging", "production"]:
            environment = "development"
        
        region = input("Region (e.g., us-east-1, eu-west-1): ").strip()
        if not region:
            region = "us-east-1"
        
        app_name = input("Your app name: ").strip()
        if not app_name:
            app_name = "my-web-app"
        
        app_type = input("App type (react/vue/angular/node/python/django/flask): ").strip().lower()
        if not app_type:
            app_type = "react"
        
        # Additional requirements
        print("\nAdditional requirements (press Enter when done):")
        additional_requirements = []
        while True:
            req = input("  - ").strip()
            if not req:
                break
            additional_requirements.append(req)
        
        return UserRequirements(
            agent_type=agent_type,
            agent_name=agent_name,
            agent_description=agent_description,
            preferred_language="python",
            deployment_platform=deployment_platform,
            environment=environment,
            region=region,
            app_name=app_name,
            app_type=app_type,
            additional_requirements=additional_requirements
        )
    
    def _generate_connection_code(self, requirements: UserRequirements) -> str:
        """Generate the actual connection code for the user's agent"""
        
        if requirements.agent_type == AgentType.LANGCHAIN:
            return self._generate_langchain_code(requirements)
        elif requirements.agent_type == AgentType.LANGGRAPH:
            return self._generate_langgraph_code(requirements)
        elif requirements.agent_type == AgentType.AUTOGEN:
            return self._generate_autogen_code(requirements)
        else:
            return self._generate_custom_code(requirements)
    
    def _generate_langchain_code(self, requirements: UserRequirements) -> str:
        return f'''#!/usr/bin/env python3
"""
{requirements.agent_name} - LangChain Agent with MCP Deployment Integration
{requirements.agent_description}
"""

import os
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools import MCPTool
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from modelcontextprotocol import ClientSession, StdioServerParameters
import asyncio

class {requirements.agent_name}:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4", temperature=0)
        self.deployment_client = None
        self.setup_mcp_connection()
    
    def setup_mcp_connection(self):
        """Initialize MCP client for deployment server"""
        try:
            self.deployment_client = ClientSession(
                StdioServerParameters(
                    command="deployment-mcp-server",
                    args=["--endpoint", "{self.server_info['endpoint']}"]
                )
            )
            print("✅ MCP deployment server connected successfully!")
        except Exception as e:
            print(f"❌ Failed to connect to MCP server: {{e}}")
            raise
    
    def create_deployment_tool(self):
        """Create deployment tool for LangChain"""
        return MCPTool(
            name="deploy_webapp",
            description="Deploy web applications with one-click to {requirements.deployment_platform.upper()}",
            mcp_client=self.deployment_client
        )
    
    def create_agent(self):
        """Create the LangChain agent"""
        tools = [self.create_deployment_tool()]
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are {requirements.agent_name}, an AI agent that {requirements.agent_description}.
            
            You can deploy web applications to {requirements.deployment_platform.upper()} with one-click deployment.
            
            When deploying:
            - Use the deploy_webapp tool
            - Specify the app name: {requirements.app_name}
            - Use platform: {requirements.deployment_platform}
            - Use environment: {requirements.environment}
            - Use region: {requirements.region}
            
            Always provide clear status updates and handle errors gracefully."""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{{input}}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        agent = create_openai_functions_agent(self.llm, tools, prompt)
        return AgentExecutor(agent=agent, tools=tools, verbose=True)
    
    def deploy(self, deployment_request: str):
        """Deploy the application"""
        agent = self.create_agent()
        
        result = agent.invoke({{
            "input": f"Deploy {{deployment_request}} for {{requirements.app_name}} to {{requirements.deployment_platform.upper()}} {{requirements.environment}} environment in {{requirements.region}}"
        }})
        
        return result

def main():
    """Main function"""
    # Set up environment variables
    os.environ.setdefault("OPENAI_API_KEY", "your_openai_api_key_here")
    os.environ.setdefault("DEPLOYMENT_OAUTH_CLIENT_ID", "your_oauth_client_id_here")
    os.environ.setdefault("DEPLOYMENT_OAUTH_CLIENT_SECRET", "your_oauth_client_secret_here")
    
    # Create and run the agent
    agent = {requirements.agent_name}()
    
    # Example deployment
    deployment_request = input("What would you like to deploy? ")
    result = agent.deploy(deployment_request)
    print(f"Deployment result: {{result}}")

if __name__ == "__main__":
    main()'''
    
    def _generate_langgraph_code(self, requirements: UserRequirements) -> str:
        return f'''#!/usr/bin/env python3
"""
{requirements.agent_name} - LangGraph Agent with MCP Deployment Integration
{requirements.agent_description}
"""

import os
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from modelcontextprotocol import ClientSession, StdioServerParameters
import asyncio

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    deployment_status: str
    deployment_result: dict

class {requirements.agent_name}:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4", temperature=0)
        self.deployment_client = None
        self.setup_mcp_connection()
    
    def setup_mcp_connection(self):
        """Initialize MCP client for deployment server"""
        try:
            self.deployment_client = ClientSession(
                StdioServerParameters(
                    command="deployment-mcp-server",
                    args=["--endpoint", "{self.server_info['endpoint']}"]
                )
            )
            print("✅ MCP deployment server connected successfully!")
        except Exception as e:
            print(f"❌ Failed to connect to MCP server: {{e}}")
            raise
    
    def create_deployment_node(self):
        """Create deployment tool node"""
        return ToolNode([self.deployment_client])
    
    def create_agent_node(self, state: AgentState) -> AgentState:
        """Agent node that decides on deployment actions"""
        messages = state["messages"]
        
        # Get the last human message
        last_message = messages[-1] if messages else HumanMessage(content="")
        
        # Create AI response
        ai_message = AIMessage(content=f"I'll help you deploy {{requirements.app_name}} to {{requirements.deployment_platform.upper()}} {{requirements.environment}} environment in {{requirements.region}}.")
        
        return {{
            "messages": [ai_message],
            "deployment_status": "initiated",
            "deployment_result": {{}}
        }}
    
    def create_workflow(self):
        """Create the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("agent", self.create_agent_node)
        workflow.add_node("deploy", self.create_deployment_node())
        
        # Add edges
        workflow.add_edge("agent", "deploy")
        workflow.add_edge("deploy", END)
        
        return workflow.compile()
    
    def deploy(self, deployment_request: str):
        """Deploy the application"""
        workflow = self.create_workflow()
        
        result = workflow.invoke({{
            "messages": [HumanMessage(content=deployment_request)],
            "deployment_status": "pending",
            "deployment_result": {{}}
        }})
        
        return result

def main():
    """Main function"""
    # Set up environment variables
    os.environ.setdefault("OPENAI_API_KEY", "your_openai_api_key_here")
    os.environ.setdefault("DEPLOYMENT_OAUTH_CLIENT_ID", "your_oauth_client_id_here")
    os.environ.setdefault("DEPLOYMENT_OAUTH_CLIENT_SECRET", "your_oauth_client_secret_here")
    
    # Create and run the agent
    agent = {requirements.agent_name}()
    
    # Example deployment
    deployment_request = input("What would you like to deploy? ")
    result = agent.deploy(deployment_request)
    print(f"Deployment result: {{result}}")

if __name__ == "__main__":
    main()'''
    
    def _generate_autogen_code(self, requirements: UserRequirements) -> str:
        return f'''#!/usr/bin/env python3
"""
{requirements.agent_name} - AutoGen Agent with MCP Deployment Integration
{requirements.agent_description}
"""

import os
import autogen
from modelcontextprotocol import ClientSession, StdioServerParameters
import asyncio

class {requirements.agent_name}:
    def __init__(self):
        self.deployment_client = None
        self.setup_mcp_connection()
        self.setup_autogen_agents()
    
    def setup_mcp_connection(self):
        """Initialize MCP client for deployment server"""
        try:
            self.deployment_client = ClientSession(
                StdioServerParameters(
                    command="deployment-mcp-server",
                    args=["--endpoint", "{self.server_info['endpoint']}"]
                )
            )
            print("✅ MCP deployment server connected successfully!")
        except Exception as e:
            print(f"❌ Failed to connect to MCP server: {{e}}")
            raise
    
    def setup_autogen_agents(self):
        """Set up AutoGen agents"""
        # Configuration for LLM
        config_list = [
            {{
                "model": "gpt-4",
                "api_key": os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")
            }}
        ]
        
        # Create deployment specialist agent
        self.deployment_agent = autogen.AssistantAgent(
            name="deployment_specialist",
            system_message=f"""You are a deployment specialist for {requirements.agent_name}.
            You can deploy web applications to {requirements.deployment_platform.upper()} with one-click deployment.
            
            Your capabilities:
            - Deploy {requirements.app_type} applications
            - Use platform: {requirements.deployment_platform}
            - Use environment: {requirements.environment}
            - Use region: {requirements.region}
            - Handle deployment errors and rollbacks
            
            Always provide clear status updates and handle errors gracefully.""",
            llm_config={{"config_list": config_list}},
            human_input_mode="NEVER"
        )
        
        # Create user proxy agent
        self.user_proxy = autogen.UserProxyAgent(
            name="user_proxy",
            human_input_mode="ALWAYS",
            max_consecutive_auto_reply=10,
            is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
            code_execution_config={{"work_dir": "workspace"}},
            llm_config={{"config_list": config_list}}
        )
        
        # Register deployment function
        self.deployment_agent.register_function(
            function_map={{"deploy_webapp": self.deploy_webapp}}
        )
    
    async def deploy_webapp(self, app_name: str, platform: str, environment: str, region: str):
        """Deploy a web application using MCP server"""
        try:
            result = await self.deployment_client.call_tool("deploy", {{
                "app_name": app_name,
                "platform": platform,
                "environment": environment,
                "region": region
            }})
            return f"✅ Successfully deployed {{app_name}} to {{platform}} {{environment}} in {{region}}"
        except Exception as e:
            return f"❌ Deployment failed: {{e}}"
    
    def deploy(self, deployment_request: str):
        """Deploy the application"""
        # Start conversation
        self.user_proxy.initiate_chat(
            self.deployment_agent,
            message=f"Deploy {{deployment_request}} for {{requirements.app_name}} to {{requirements.deployment_platform.upper()}} {{requirements.environment}} environment in {{requirements.region}}"
        )

def main():
    """Main function"""
    # Set up environment variables
    os.environ.setdefault("OPENAI_API_KEY", "your_openai_api_key_here")
    os.environ.setdefault("DEPLOYMENT_OAUTH_CLIENT_ID", "your_oauth_client_id_here")
    os.environ.setdefault("DEPLOYMENT_OAUTH_CLIENT_SECRET", "your_oauth_client_secret_here")
    
    # Create and run the agent
    agent = {requirements.agent_name}()
    
    # Example deployment
    deployment_request = input("What would you like to deploy? ")
    agent.deploy(deployment_request)

if __name__ == "__main__":
    main()'''
    
    def _generate_custom_code(self, requirements: UserRequirements) -> str:
        return f'''#!/usr/bin/env python3
"""
{requirements.agent_name} - Custom Agent with MCP Deployment Integration
{requirements.agent_description}
"""

import os
import asyncio
from modelcontextprotocol import ClientSession, StdioServerParameters
from typing import Dict, Any

class {requirements.agent_name}:
    def __init__(self):
        self.deployment_client = None
        self.setup_mcp_connection()
    
    def setup_mcp_connection(self):
        """Initialize MCP client for deployment server"""
        try:
            self.deployment_client = ClientSession(
                StdioServerParameters(
                    command="deployment-mcp-server",
                    args=["--endpoint", "{self.server_info['endpoint']}"]
                )
            )
            print("✅ MCP deployment server connected successfully!")
        except Exception as e:
            print(f"❌ Failed to connect to MCP server: {{e}}")
            raise
    
    async def list_deployment_tools(self):
        """List available deployment tools"""
        try:
            tools = await self.deployment_client.list_tools()
            print(f"Available deployment tools: {{tools}}")
            return tools
        except Exception as e:
            print(f"❌ Failed to list tools: {{e}}")
            return []
    
    async def deploy_webapp(self, app_name: str, platform: str, environment: str, region: str, **kwargs):
        """Deploy a web application"""
        try:
            deployment_config = {{
                "app_name": app_name,
                "platform": platform,
                "environment": environment,
                "region": region,
                **kwargs
            }}
            
            print(f"🚀 Deploying {{app_name}} to {{platform}} {{environment}} in {{region}}...")
            
            result = await self.deployment_client.call_tool("deploy", deployment_config)
            
            print(f"✅ Deployment successful!")
            print(f"Result: {{result}}")
            
            return result
        except Exception as e:
            print(f"❌ Deployment failed: {{e}}")
            raise
    
    async def check_deployment_status(self, deployment_id: str):
        """Check deployment status"""
        try:
            result = await self.deployment_client.call_tool("status", {{"deployment_id": deployment_id}})
            return result
        except Exception as e:
            print(f"❌ Failed to check status: {{e}}")
            return None
    
    async def rollback_deployment(self, deployment_id: str):
        """Rollback deployment"""
        try:
            result = await self.deployment_client.call_tool("rollback", {{"deployment_id": deployment_id}})
            return result
        except Exception as e:
            print(f"❌ Failed to rollback: {{e}}")
            return None

async def main():
    """Main function"""
    # Set up environment variables
    os.environ.setdefault("DEPLOYMENT_OAUTH_CLIENT_ID", "your_oauth_client_id_here")
    os.environ.setdefault("DEPLOYMENT_OAUTH_CLIENT_SECRET", "your_oauth_client_secret_here")
    
    # Create agent
    agent = {requirements.agent_name}()
    
    # List available tools
    await agent.list_deployment_tools()
    
    # Deploy application
    deployment_request = input("What would you like to deploy? ")
    
    result = await agent.deploy_webapp(
        app_name="{requirements.app_name}",
        platform="{requirements.deployment_platform}",
        environment="{requirements.environment}",
        region="{requirements.region}",
        app_type="{requirements.app_type}"
    )
    
    print(f"Final result: {{result}}")

if __name__ == "__main__":
    asyncio.run(main())'''
    
    def _generate_config_file(self, requirements: UserRequirements) -> str:
        config = {
            "agent": {
                "name": requirements.agent_name,
                "type": requirements.agent_type.value,
                "description": requirements.agent_description
            },
            "mcp_server": {
                "name": self.server_info["name"],
                "endpoint": self.server_info["endpoint"],
                "auth": {
                    "type": self.server_info["auth"],
                    "client_id": "${{DEPLOYMENT_OAUTH_CLIENT_ID}}",
                    "client_secret": "${{DEPLOYMENT_OAUTH_CLIENT_SECRET}}"
                }
            },
            "deployment": {
                "platform": requirements.deployment_platform,
                "environment": requirements.environment,
                "region": requirements.region,
                "app_name": requirements.app_name,
                "app_type": requirements.app_type
            },
            "additional_requirements": requirements.additional_requirements
        }
        return json.dumps(config, indent=2)
    
    def _generate_requirements_file(self, requirements: UserRequirements) -> str:
        base_requirements = [
            "modelcontextprotocol>=0.1.0",
            "httpx>=0.27.0",
            "python-dotenv>=1.0.0"
        ]
        
        if requirements.agent_type == AgentType.LANGCHAIN:
            base_requirements.extend([
                "langchain>=0.1.0",
                "langchain-openai>=0.1.0"
            ])
        elif requirements.agent_type == AgentType.LANGGRAPH:
            base_requirements.extend([
                "langgraph>=0.2.0",
                "langchain-openai>=0.1.0"
            ])
        elif requirements.agent_type == AgentType.AUTOGEN:
            base_requirements.extend([
                "pyautogen>=0.2.0"
            ])
        
        return "\n".join(base_requirements)
    
    def _generate_setup_script(self, requirements: UserRequirements) -> str:
        return f'''#!/bin/bash
# Setup script for {requirements.agent_name}

echo "🔧 Setting up {requirements.agent_name}..."

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
echo "Setting up environment variables..."
echo "export OPENAI_API_KEY=your_openai_api_key_here" >> .env
echo "export DEPLOYMENT_OAUTH_CLIENT_ID=your_oauth_client_id_here" >> .env
echo "export DEPLOYMENT_OAUTH_CLIENT_SECRET=your_oauth_client_secret_here" >> .env

# Create workspace directory
mkdir -p workspace

echo "✅ Setup complete!"
echo "📝 Don't forget to:"
echo "   1. Add your actual API keys to .env"
echo "   2. Test the connection with: python test_connection.py"
echo "   3. Run your agent with: python {requirements.agent_name.lower()}.py"'''
    
    def _generate_test_script(self, requirements: UserRequirements) -> str:
        return f'''#!/usr/bin/env python3
"""
Test script for {requirements.agent_name} MCP connection
"""

import asyncio
import os
from modelcontextprotocol import ClientSession, StdioServerParameters

async def test_connection():
    """Test the MCP connection"""
    print("🧪 Testing MCP connection...")
    
    try:
        # Initialize client
        client = ClientSession(
            StdioServerParameters(
                command="deployment-mcp-server",
                args=["--endpoint", "{self.server_info['endpoint']}"]
            )
        )
        
        # List available tools
        tools = await client.list_tools()
        print(f"✅ Available tools: {{tools}}")
        
        # Test a simple deployment call
        test_result = await client.call_tool("status", {{"test": True}})
        print(f"✅ Test call successful: {{test_result}}")
        
        print("🎉 Connection test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Connection test failed: {{e}}")
        return False

if __name__ == "__main__":
    asyncio.run(test_connection())'''
    
    def _save_files(self, requirements: UserRequirements, connection_code: str, config_file: str, requirements_file: str, setup_script: str, test_script: str):
        """Save all generated files"""
        # Create output directory
        output_dir = Path(f"{requirements.agent_name.lower()}_agent")
        output_dir.mkdir(exist_ok=True)
        
        # Save main agent file
        agent_file = output_dir / f"{requirements.agent_name.lower()}.py"
        with open(agent_file, 'w') as f:
            f.write(connection_code)
        
        # Save config file
        config_file_path = output_dir / "config.json"
        with open(config_file_path, 'w') as f:
            f.write(config_file)
        
        # Save requirements file
        requirements_file_path = output_dir / "requirements.txt"
        with open(requirements_file_path, 'w') as f:
            f.write(requirements_file)
        
        # Save setup script
        setup_script_path = output_dir / "setup.sh"
        with open(setup_script_path, 'w') as f:
            f.write(setup_script)
        os.chmod(setup_script_path, 0o755)
        
        # Save test script
        test_script_path = output_dir / "test_connection.py"
        with open(test_script_path, 'w') as f:
            f.write(test_script)
        
        print(f"📁 Files saved to: {output_dir}")
    
    def _display_results(self, requirements: UserRequirements, connection_code: str):
        """Display the connection results"""
        print("\n" + "="*80)
        print("🎉 CONNECTION SUCCESSFUL!")
        print("="*80)
        print(f"✅ Your {requirements.agent_name} is now connected to the MCP deployment server!")
        print()
        print("📁 Generated files:")
        print(f"  - {requirements.agent_name.lower()}.py (Your agent)")
        print(f"  - config.json (Configuration)")
        print(f"  - requirements.txt (Dependencies)")
        print(f"  - setup.sh (Setup script)")
        print(f"  - test_connection.py (Test script)")
        print()
        print("🚀 Next steps:")
        print("  1. cd {requirements.agent_name.lower()}_agent")
        print("  2. chmod +x setup.sh && ./setup.sh")
        print("  3. python test_connection.py")
        print("  4. python {requirements.agent_name.lower()}.py")
        print()
        print("🔑 Required environment variables:")
        print("  - OPENAI_API_KEY")
        print("  - DEPLOYMENT_OAUTH_CLIENT_ID")
        print("  - DEPLOYMENT_OAUTH_CLIENT_SECRET")
        print()
        print("💡 Your agent can now deploy {requirements.app_name} to {requirements.deployment_platform.upper()}!")

def main():
    """Main function"""
    connector = InteractiveMCPConnector()
    result = connector.run()
    
    if result.success:
        print("\n🎯 Connection completed successfully!")
    else:
        print(f"\n❌ Connection failed: {result.error_message}")

if __name__ == "__main__":
    main() 