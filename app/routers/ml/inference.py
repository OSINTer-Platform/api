from typing import Any, Literal, cast
from pydantic import BaseModel, Field
from uuid import UUID, uuid4

from fastapi import APIRouter, Query
import openai

from modules.elastic import ArticleSearchQuery
from app import config_options
from modules.objects import BaseArticle

router = APIRouter()
openai.api_key = config_options.OPENAI_KEY


class Chat(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    visible: bool = True
    id: UUID = Field(default_factory=uuid4)


class ChatList(BaseModel):
    chats: list[Chat]
    article_base: list[BaseArticle] = []
    reached_max: bool = False

    def serialize(self) -> list[dict[str, str]]:
        return [{"role": chat.role, "content": chat.content} for chat in self.chats]


@router.post("/chat/continue")
def continue_chat(
    current_chats: ChatList,
    question: str | None = Query(None),
    visible: bool = Query(True),
    id: UUID = Query(default_factory=uuid4),
) -> ChatList:
    if question:
        current_chats.chats.append(
            Chat(role="user", content=question, visible=visible, id=id)
        )

    answer = cast(
        dict[str, Any],
        openai.ChatCompletion.create(  # type: ignore[no-untyped-call]
            model=config_options.OPENAI_MODEL,
            messages=current_chats.serialize(),
            n=1,
            temperature=1,
            frequency_penalty=0,
            presence_penalty=0,
        ),
    )

    new_chat = Chat.model_validate(answer["choices"][0]["message"])
    current_chats.chats.append(new_chat)

    current_chats.reached_max = answer["choices"][0]["finish_reason"] == "length"

    return current_chats


@router.get("/chat/ask")
def generate_answer_to_question(
    question: str, visible: bool = Query(True), id: UUID = Query(default_factory=uuid4)
) -> ChatList:
    q = ArticleSearchQuery(limit=3, semantic_search=question)
    articles = config_options.es_article_client.query_documents(q, True)[0]

    # Truncates at 3200 characthers as each 4'th characther ~ 1 token
    # and using the 4k token window with 3 articles, this leaves ~ 1700
    # tokens for the chat

    truncated_contents = [article.content[:3200] for article in articles]

    model_instruct = """
        Use the provided articles delimited by triple quotes to answer questions.
        If the answer cannot be found in the articles, write "I could not find an answer."
        If you cannot find a question to answer, write "I am sorry, I am not sure what you are asking?"
    """
    model_instruct = " ".join(
        [instruction.strip() for instruction in model_instruct.split("\n")]
    ).strip()

    new_chats = ChatList(
        chats=[Chat(role="system", content=model_instruct, visible=False)],
        article_base=[BaseArticle.model_validate(article) for article in articles],
    )

    for content in truncated_contents:
        content = content.replace('"""', '"')
        new_chats.chats.append(
            Chat(role="user", content=f'"""\n{content}\n"""', visible=False)
        )

    return continue_chat(new_chats, question, visible, id)
