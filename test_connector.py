#!/usr/bin/env python3
"""
Test script for the interactive connector agent
"""

import sys
import os
from unittest.mock import patch
from io import StringIO
from connector_agent_direct import InteractiveMCPConnector, UserRequirements, AgentType

def test_connector_with_mock_inputs():
    """Test the connector agent with mock user inputs"""
    
    # Mock user inputs for testing
    mock_inputs = [
        "1",  # LangChain
        "TestDeploymentAgent",  # Agent name
        "Deploys React apps to AWS",  # Description
        "1",  # AWS platform
        "production",  # Environment
        "us-west-2",  # Region
        "my-react-app",  # App name
        "react",  # App type
        "",  # No additional requirements
    ]
    
    print("🧪 Testing Interactive MCP Connector Agent...")
    print("=" * 60)
    
    # Create connector
    connector = InteractiveMCPConnector()
    
    # Test with mock inputs
    with patch('builtins.input', side_effect=mock_inputs):
        try:
            result = connector.run()
            
            if result.success:
                print("✅ Connector test PASSED!")
                print(f"📁 Generated files in: TestDeploymentAgent_agent/")
                print(f"📄 Main agent file: TestDeploymentAgent_agent/testdeploymentagent.py")
                print(f"⚙️ Config file: TestDeploymentAgent_agent/config.json")
                print(f"📦 Requirements: TestDeploymentAgent_agent/requirements.txt")
                print(f"🔧 Setup script: TestDeploymentAgent_agent/setup.sh")
                print(f"🧪 Test script: TestDeploymentAgent_agent/test_connection.py")
                
                # Check if files were actually created
                import pathlib
                agent_dir = pathlib.Path("TestDeploymentAgent_agent")
                if agent_dir.exists():
                    files = list(agent_dir.glob("*"))
                    print(f"📋 Files created: {len(files)}")
                    for file in files:
                        print(f"  - {file.name}")
                else:
                    print("❌ Agent directory not created")
                    return False
                
                return True
            else:
                print(f"❌ Connector test FAILED: {result.error_message}")
                return False
                
        except Exception as e:
            print(f"❌ Connector test FAILED with exception: {e}")
            return False

def test_different_agent_types():
    """Test generating code for different agent types"""
    
    print("\n🧪 Testing different agent types...")
    print("=" * 60)
    
    connector = InteractiveMCPConnector()
    
    # Test requirements for different agent types
    test_cases = [
        (AgentType.LANGCHAIN, "LangChainAgent", "Uses LangChain framework"),
        (AgentType.LANGGRAPH, "LangGraphAgent", "Uses LangGraph workflow"),
        (AgentType.AUTOGEN, "AutoGenAgent", "Uses AutoGen multi-agent"),
        (AgentType.CUSTOM, "CustomAgent", "Uses custom implementation"),
    ]
    
    for agent_type, name, description in test_cases:
        print(f"\n🔧 Testing {agent_type.value} agent...")
        
        requirements = UserRequirements(
            agent_type=agent_type,
            agent_name=name,
            agent_description=description,
            preferred_language="python",
            deployment_platform="aws",
            environment="development",
            region="us-east-1",
            app_name="test-app",
            app_type="react",
            additional_requirements=[]
        )
        
        try:
            # Generate connection code
            connection_code = connector._generate_connection_code(requirements)
            
            # Check if code contains expected elements
            if agent_type == AgentType.LANGCHAIN:
                assert "langchain" in connection_code.lower()
                assert "AgentExecutor" in connection_code
            elif agent_type == AgentType.LANGGRAPH:
                assert "langgraph" in connection_code.lower()
                assert "StateGraph" in connection_code
            elif agent_type == AgentType.AUTOGEN:
                assert "autogen" in connection_code.lower()
                assert "AssistantAgent" in connection_code
            else:  # Custom
                assert "modelcontextprotocol" in connection_code.lower()
                assert "ClientSession" in connection_code
            
            print(f"✅ {agent_type.value} code generation PASSED")
            
        except Exception as e:
            print(f"❌ {agent_type.value} code generation FAILED: {e}")
            return False
    
    return True

def test_configuration_generation():
    """Test configuration file generation"""
    
    print("\n🧪 Testing configuration generation...")
    print("=" * 60)
    
    connector = InteractiveMCPConnector()
    
    requirements = UserRequirements(
        agent_type=AgentType.LANGCHAIN,
        agent_name="ConfigTestAgent",
        agent_description="Tests configuration generation",
        preferred_language="python",
        deployment_platform="gcp",
        environment="staging",
        region="europe-west1",
        app_name="config-test-app",
        app_type="vue",
        additional_requirements=["monitoring", "logging"]
    )
    
    try:
        # Generate config file
        config_file = connector._generate_config_file(requirements)
        
        # Parse and verify config
        import json
        config = json.loads(config_file)
        
        # Check required fields
        assert config["agent"]["name"] == "ConfigTestAgent"
        assert config["agent"]["type"] == "langchain"
        assert config["deployment"]["platform"] == "gcp"
        assert config["deployment"]["environment"] == "staging"
        assert config["deployment"]["app_name"] == "config-test-app"
        assert config["deployment"]["app_type"] == "vue"
        assert "monitoring" in config["additional_requirements"]
        assert "logging" in config["additional_requirements"]
        
        print("✅ Configuration generation PASSED")
        print(f"📄 Config preview:")
        print(json.dumps(config, indent=2)[:500] + "...")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration generation FAILED: {e}")
        return False

def test_requirements_generation():
    """Test requirements file generation"""
    
    print("\n🧪 Testing requirements generation...")
    print("=" * 60)
    
    connector = InteractiveMCPConnector()
    
    test_cases = [
        (AgentType.LANGCHAIN, ["langchain", "langchain-openai"]),
        (AgentType.LANGGRAPH, ["langgraph", "langchain-openai"]),
        (AgentType.AUTOGEN, ["pyautogen"]),
        (AgentType.CUSTOM, []),  # Only base requirements
    ]
    
    for agent_type, expected_deps in test_cases:
        print(f"\n🔧 Testing {agent_type.value} requirements...")
        
        requirements = UserRequirements(
            agent_type=agent_type,
            agent_name="RequirementsTestAgent",
            agent_description="Tests requirements generation",
            preferred_language="python",
            deployment_platform="aws",
            environment="development",
            region="us-east-1",
            app_name="test-app",
            app_type="react",
            additional_requirements=[]
        )
        
        try:
            # Generate requirements
            requirements_file = connector._generate_requirements_file(requirements)
            
            # Check base requirements are always present
            assert "modelcontextprotocol" in requirements_file
            assert "httpx" in requirements_file
            assert "python-dotenv" in requirements_file
            
            # Check framework-specific requirements
            for dep in expected_deps:
                assert dep in requirements_file
            
            print(f"✅ {agent_type.value} requirements generation PASSED")
            print(f"📦 Requirements: {requirements_file.strip()}")
            
        except Exception as e:
            print(f"❌ {agent_type.value} requirements generation FAILED: {e}")
            return False
    
    return True

def main():
    """Run all tests"""
    print("🚀 Starting Interactive MCP Connector Agent Tests")
    print("=" * 80)
    
    tests = [
        ("Full Connector Test", test_connector_with_mock_inputs),
        ("Agent Types Test", test_different_agent_types),
        ("Configuration Test", test_configuration_generation),
        ("Requirements Test", test_requirements_generation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
    
    print(f"\n{'='*80}")
    print(f"🎯 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! The connector agent is working correctly.")
    else:
        print("⚠️ Some tests failed. Please check the output above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 