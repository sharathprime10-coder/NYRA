from app.tools.registry import rag_tool
from pydantic import BaseModel

class ToolCallArgs(BaseModel):
    query: str
    user_id: int = None
    document_id: int = None

def test_rag_tool_scoping_enforced():
    """
    Regression test asserting that rag_tool requires a user_id.
    """
    # Call rag_tool without user_id
    result = rag_tool.invoke({"query": "test query", "user_id": None, "document_id": None})
    
    assert isinstance(result, dict)
    assert "error" in result
    assert "user_id is required" in result["error"]

def test_rag_tool_scoping_filters(mocker):
    """
    Test that the query passes the correct user_id filter to chromadb.
    """
    mock_db = mocker.patch("app.tools.registry.SessionLocal")
    mock_rag = mocker.patch("app.tools.registry.rag_service.query")
    
    # Return empty list from rag
    mock_rag.return_value = []
    
    result = rag_tool.invoke({"query": "test query", "user_id": 1, "document_id": 5})
    
    # Assert query was called with the correct filter
    mock_rag.assert_called_once()
    called_kwargs = mock_rag.call_args.kwargs
    filters = called_kwargs.get("filters")
    assert filters is not None
    assert "$and" in filters
    
    # Verify user_id is enforced in the filter
    user_filter = [f for f in filters["$and"] if "user_id" in f][0]
    assert user_filter["user_id"] == 1
