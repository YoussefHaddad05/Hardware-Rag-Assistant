from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """The expected payload when a user asks a question."""
    question: str = Field(
        ..., 
        min_length=1, 
        description="The user's question to the RAG system", 
        json_schema_extra={"example": "How much flash memory does the Arduino Uno have?"}
    )


class QueryResponse(BaseModel):
    """The payload returned by the API containing the answer and citations."""
    answer: str = Field(..., description="The generated answer from the LLM")
    sources: list[str] = Field(..., description="A list of source chunks used to generate the answer")