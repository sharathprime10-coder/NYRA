from app.services.rag_service import query_knowledge_base


def test():
    try:
        res = query_knowledge_base("What is this?")
        print("Success:", res)
    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    test()
