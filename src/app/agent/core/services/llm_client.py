from langchain_openai import ChatOpenAI

from app.agent.core.config.settings import Settings

Settings.validate()

api_key = Settings.OPENAI_API_KEY

def get_chat_model(
    *,
    model_name: str,
    temperature: float = 0,
):
    """
    任意モデルを返す共通関数。
    必要になったら timeout や max_retries などもここで共通化できる。
    """
    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
    )


def get_chat_model_gpt5_4():
    """
    GPT-5.4 を返す。
    """
    return get_chat_model(
        model_name="gpt-5.4",
        temperature=0,
    )