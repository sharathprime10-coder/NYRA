from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from app.core.config import settings

def get_robust_llm():
    """
    Builds a deeply nested LLM chain that cascades through available 
    providers when the primary model fails or hits rate limits.
    """
    fallbacks = []
    
    # Use Gemini as a fallback, with correct model name
    gemini_llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", max_retries=1)
    
    if settings.GROQ_API_KEY:
        # Make Groq the primary to avoid Gemini rate limits
        primary_llm = ChatGroq(model="llama-3.3-70b-versatile", max_retries=1, api_key=settings.GROQ_API_KEY)
        fallbacks.append(ChatGroq(model="qwen-2.5-32b", max_retries=1, api_key=settings.GROQ_API_KEY))
        fallbacks.append(gemini_llm)
    else:
        primary_llm = gemini_llm
        
    # 3. NVIDIA Fallback
    if settings.NVIDIA_API_KEY:
        from langchain_openai import ChatOpenAI
        fallbacks.append(ChatOpenAI(
            model="nvidia/nemotron-3-ultra-550b-a55b",
            api_key=settings.NVIDIA_API_KEY,
            base_url="https://integrate.api.nvidia.com/v1",
            max_retries=1,
            extra_body={"chat_template_kwargs": {"enable_thinking": True}, "reasoning_budget": 16384}
        ))
        
    # 4. Future providers can be added here
    # if settings.HUGGINGFACE_API_KEY:
    #     fallbacks.append(...)
    
    if fallbacks:
        return primary_llm.with_fallbacks(fallbacks=fallbacks, exceptions_to_handle=(Exception,))
    return primary_llm

def get_frontier_llm():
    """
    Returns the most powerful reasoning model available for complex agentic tasks.
    Primary: Groq LLaMA 3.3 70B
    Fallback: Google Gemini
    """
    if settings.GROQ_API_KEY:
        from langchain_groq import ChatGroq
        from langchain_google_genai import ChatGoogleGenerativeAI
        frontier_llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=settings.GROQ_API_KEY,
            max_retries=1
        )
        fallbacks = [
            ChatGroq(model="qwen-2.5-32b", max_retries=1, api_key=settings.GROQ_API_KEY),
            ChatGoogleGenerativeAI(model="gemini-3.6-flash", max_retries=1)
        ]
        return frontier_llm.with_fallbacks(fallbacks=fallbacks, exceptions_to_handle=(Exception,))
    
    # If no Groq key, default to the robust cascade
    return get_robust_llm()

def get_writer_llm():
    """Returns the LLM for writing responses. Can be customized later."""
    return get_robust_llm()

def get_critic_llm():
    """Returns the LLM for critiquing responses. Can be customized later."""
    return get_frontier_llm()

def get_fast_llm():
    """
    Returns an extremely fast and cheap LLM for low-latency tasks.
    Primary: Groq LLaMA 3.1 8B Instant
    Fallback: Google Gemini
    """
    if settings.GROQ_API_KEY:
        from langchain_groq import ChatGroq
        from langchain_google_genai import ChatGoogleGenerativeAI
        fast_llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=settings.GROQ_API_KEY,
            max_retries=1
        )
        fallbacks = [
            ChatGoogleGenerativeAI(model="gemini-3.6-flash", max_retries=1)
        ]
        return fast_llm.with_fallbacks(fallbacks=fallbacks, exceptions_to_handle=(Exception,))
    
    return ChatGoogleGenerativeAI(model="gemini-3.6-flash", max_retries=1)

def get_router_llm():
    """Returns an extremely fast and cheap LLM for routing tasks (like Supervisor)."""
    return get_fast_llm()
