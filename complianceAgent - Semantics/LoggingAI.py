from langchain_openai import ChatOpenAI

class LoggingChatOpenAI(ChatOpenAI):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        '''print("\n" + "="*30)
        print("PROMPT SENT TO LLM")
        print("-"*30)
        for msg in messages:
            # Use type (system, human, ai, tool...) and pretty format
            role = getattr(msg, "type", type(msg).__name__)
            content = getattr(msg, "content", str(msg))
            print(f"{role.upper():>8}: {content}\n")
        print("="*30 + "\n")'''
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
