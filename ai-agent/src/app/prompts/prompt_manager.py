from src.app.prompts.templates.llama_prompt import LLAMA_TEMPLATES

class PromptManager:
    @staticmethod
    def get_langchain_messages(prompt_type: str, model_name: str = None) -> list[tuple[str, str]]:
        """
        Returns a list of tuples formatted for LangChain's ChatPromptTemplate.from_messages()
        Leaves variables (like {context}, {chat_history}, etc.) unformatted for LCEL to fill.
        """
        # We only support llama-3.1-8b-instant for now, so we map to LLAMA_TEMPLATES
        templates = LLAMA_TEMPLATES

        if prompt_type not in templates:
            raise ValueError(f"Prompt type '{prompt_type}' is not supported.")
            
        system_content = templates[prompt_type]["system"]
        human_content = templates[prompt_type]["human"]

        return [
            ("system", system_content),
            ("human", human_content)
        ]
