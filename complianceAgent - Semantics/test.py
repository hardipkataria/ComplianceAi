from typing import Dict, Any, List

class Agent:
    def __init__(self, name: str):
        self.name = name

    def generate_prompt(self, user_input: str, context: Dict[str, Any]) -> str:
        """Generate prompt to send to the agent's AI backend."""
        raise NotImplementedError()

    def call(self, prompt: str) -> str:
        """Call the agent's AI model or tool."""
        raise NotImplementedError()


class SearchAgent(Agent):
    def __init__(self):
        super().__init__('SearchAgent')

    def generate_prompt(self, user_input, context):
        return f"Search query: {user_input}"

    def call(self, prompt):
        # Mock response
        return f"Search results for '{prompt}'"


class ComplianceAgent(Agent):
    def __init__(self):
        super().__init__('ComplianceAgent')

    def generate_prompt(self, user_input, context):
        return f"Check compliance based on: {user_input}"

    def call(self, prompt):
        # Mock response
        return f"Compliance check results for '{prompt}'"


class AgentManager:
    def __init__(self, agents: List[Agent]):
        self.agents = {agent.name: agent for agent in agents}
        self.context = {}

    def update_context(self, user_input):
        # Add/update conversation context memory
        self.context['last_user_input'] = user_input

    def decide_agents(self, user_input) -> List[str]:
        """
        Simple keyword-based routing.
        More sophisticated: Use LLM to classify intent and route intelligently.
        """
        user_input_lower = user_input.lower()
        if 'search' in user_input_lower:
            return ['SearchAgent']
        elif 'compliance' in user_input_lower or 'policy' in user_input_lower:
            return ['ComplianceAgent']
        else:
            # Default to SearchAgent for unknown queries
            return ['SearchAgent']

    def generate_prompts(self, user_input, agent_names: List[str]) -> Dict[str, str]:
        prompts = {}
        for name in agent_names:
            agent = self.agents[name]
            prompts[name] = agent.generate_prompt(user_input, self.context)
        return prompts

    def call_agents(self, prompts: Dict[str, str]) -> Dict[str, str]:
        results = {}
        for name, prompt in prompts.items():
            agent = self.agents[name]
            results[name] = agent.call(prompt)
        return results

    def handle_user_input(self, user_input: str) -> Dict[str, str]:
        self.update_context(user_input)
        agents_to_call = self.decide_agents(user_input)
        prompts = self.generate_prompts(user_input, agents_to_call)
        results = self.call_agents(prompts)
        return results


# Example usage
if __name__ == "__main__":
    agents = [SearchAgent(), ComplianceAgent()]
    manager = AgentManager(agents)

    while True:
        query = input("User: ")
        if query.lower() in ['exit', 'quit']:
            break
        responses = manager.handle_user_input(query)
        for agent_name, response in responses.items():
            print(f"{agent_name}: {response}")
