from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from app.core.config import settings

def get_robust_llm():
    """
    Builds a deeply nested LLM chain that cascades through available 
    providers when the primary model fails or hits rate limits.
    """
    fallbacks = []
    
    # 1. Groq (Primary for speed and power)
    primary_llm = None
    if settings.GROQ_API_KEY:
        primary_llm = ChatGroq(model="llama-3.3-70b-versatile", max_retries=0, request_timeout=15, api_key=settings.GROQ_API_KEY)
        
    # 2. OpenRouter (Secondary backup for Llama 3.3)
    if settings.OPENROUTER_API_KEY:
        from langchain_openai import ChatOpenAI
        or_llm = ChatOpenAI(
            model="meta-llama/llama-3.3-70b-instruct",
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            max_retries=0,
            timeout=15
        )
        if not primary_llm:
            primary_llm = or_llm
        else:
            fallbacks.append(or_llm)
            
    # 3. NVIDIA (Tertiary backup)
    if settings.NVIDIA_API_KEY:
        from langchain_openai import ChatOpenAI
        nvidia_llm = ChatOpenAI(
            model="meta/llama-3.1-70b-instruct",
            api_key=settings.NVIDIA_API_KEY,
            base_url="https://integrate.api.nvidia.com/v1",
            max_retries=0,
            timeout=15
        )
        if not primary_llm:
            primary_llm = nvidia_llm
        else:
            fallbacks.append(nvidia_llm)
            
    # 4. Gemini (Safety Net)
    gemini_llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", max_retries=1, request_timeout=15, api_key=settings.GEMINI_API_KEY)
    if not primary_llm:
        primary_llm = gemini_llm
    else:
        fallbacks.append(gemini_llm)
        
    if fallbacks:
        return primary_llm.with_fallbacks(fallbacks=fallbacks, exceptions_to_handle=(Exception,))
    return primary_llm

def get_frontier_llm(tools=None):
    """
    Returns the most powerful reasoning model available for complex agentic tasks.
    Primary: Groq Llama 3.3 70B
    Fallback 1: OpenRouter Llama 3.3 70B
    Fallback 2: Gemini 1.5 Pro
    """
    fallbacks = []
    
    primary_llm = None
    if settings.GROQ_API_KEY:
        primary_llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=settings.GROQ_API_KEY,
            max_retries=0, # Fail fast so fallback kicks in
            request_timeout=15
        )
        if tools:
            primary_llm = primary_llm.bind_tools(tools)
            
    if settings.OPENROUTER_API_KEY:
        from langchain_openai import ChatOpenAI
        or_llm = ChatOpenAI(
            model="meta-llama/llama-3.3-70b-instruct",
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            max_retries=0,
            timeout=15
        )
        if tools:
            or_llm = or_llm.bind_tools(tools)
        if not primary_llm:
            primary_llm = or_llm
        else:
            fallbacks.append(or_llm)
            
    gemini_llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", max_retries=1, request_timeout=15, api_key=settings.GEMINI_API_KEY)
    if tools:
        gemini_llm = gemini_llm.bind_tools(tools)
        
    if not primary_llm:
        primary_llm = gemini_llm
    else:
        fallbacks.append(gemini_llm)
        
    if fallbacks:
        return primary_llm.with_fallbacks(fallbacks=fallbacks, exceptions_to_handle=(Exception,))
    return primary_llm

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
            max_retries=0,
            request_timeout=10
        )
        fallbacks = [
            ChatGoogleGenerativeAI(model="gemini-1.5-flash", max_retries=1, request_timeout=15)
        ]
        return fast_llm.with_fallbacks(fallbacks=fallbacks, exceptions_to_handle=(Exception,))
    
    return ChatGoogleGenerativeAI(model="gemini-1.5-flash", max_retries=1, request_timeout=15)

def get_router_llm():
    """Returns an extremely fast and cheap LLM for routing tasks (like Supervisor)."""
    return get_fast_llm()
