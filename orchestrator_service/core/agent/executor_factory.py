from typing import Any, List

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


def create_agent_executor(
    *,
    system_prompt_placeholder: str = "{system_prompt}",
    model_name: str = "gpt-4o-mini",
    temperature: float = 0.0,
    openai_api_key: str = "",
    tools: List[Any],
) -> AgentExecutor:
    """
    Crea un AgentExecutor de LangChain a partir de:
    - un placeholder de system_prompt (inyectado en cada request)
    - el nombre de modelo y temperatura
    - la lista de tools a utilizar (dependiente del nicho)

    Este factory es agnóstico al dominio (dental / CRM / otro);
    la selección de tools y el contenido concreto del system_prompt
    se resuelven fuera, en la capa de orquestación.
    """

    llm = ChatOpenAI(
        model=model_name,
        temperature=temperature,
        openai_api_key=openai_api_key,
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt_placeholder),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent = create_openai_tools_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=False)

