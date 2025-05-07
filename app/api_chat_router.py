from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List
from app.config import OPENROUTER_API_KEY
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage

router = APIRouter()

# Хранилище истории чатов в памяти: chat_id -> list of messages
chat_histories: Dict[str, List[dict]] = {}

# Инициализация LangChain LLM
llm = ChatOpenAI(
    openai_api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    model_name="deepseek/deepseek-chat-v3-0324"
)

class ChatRequest(BaseModel):
    chat_id: str
    message: str

@router.post("/chat")
async def chat_endpoint(req: ChatRequest):
    # Получаем историю чата или создаём новую
    if req.chat_id not in chat_histories:
        chat_histories[req.chat_id] = [
            {"role": "system", "content": "Ты - юридический ассистент."}
        ]
    # Добавляем новое сообщение пользователя
    chat_histories[req.chat_id].append({"role": "user", "content": req.message})

    # Преобразуем историю в формат LangChain
    lc_messages = []
    for msg in chat_histories[req.chat_id]:
        if msg["role"] == "system":
            lc_messages.append(SystemMessage(content=msg["content"]))
        elif msg["role"] == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            lc_messages.append(AIMessage(content=msg["content"]))

    # Получаем ответ от LangChain LLM
    response = await llm.apredict_messages(lc_messages)

    # Добавляем ответ ассистента в историю
    chat_histories[req.chat_id].append({"role": "assistant", "content": response.content})

    return {"response": response.content, "history": chat_histories[req.chat_id]} 