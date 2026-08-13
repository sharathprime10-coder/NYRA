from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from app.core.config import settings

def get_robust_llm():
    """
    Builds a deeply nested LLM chain that cascades through available 
    providers when the primary model fails or hits rate limits.
    """
    # 1. Primary Model: Google Gemini
    primary_llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", max_retries=1)
    
    fallbacks = []
    
    # 2. Groq Fallbacks
    if settings.GROQ_API_KEY:
        # High reasoning, high speed
        fallbacks.append(ChatGroq(model="llama-3.3-70b-versatile", max_retries=1, api_key=settings.GROQ_API_KEY))
        # Backup if Llama is overloaded
        fallbacks.append(ChatGroq(model="qwen-2.5-32b", max_retries=1, api_key=settings.GROQ_API_KEY))
        # Backup if Qwen is overloaded
        fallbacks.append(ChatGroq(model="gemma2-9b-it", max_retries=1, api_key=settings.GROQ_API_KEY))
        
    # 3. NVIDIA Fallback
    if settings.NVIDIA_API_KEY:
        from langchain_openai import ChatOpenAI
        fallbacks.append(ChatOpenAI(
            model="nvidia/nemotron-3-ultra-550b-a55b",
            api_key=settings.NVIDIA_API_KEY,
            base_url="https://integrate.api.nvidia.com/v1",
            max_retries=1,
            model_kwargs={"extra_body": {"chat_template_kwargs": {"enable_thinking": True}, "reasoning_budget": 16384}}
        ))
        
    # 4. Future providers can be added here
    # if settings.HUGGINGFACE_API_KEY:
    #     fallbacks.append(...)
    
    if fallbacks:
        return primary_llm.with_fallbacks(fallbacks)
    return primary_llm

def get_frontier_llm():
    """
    Returns the most powerful reasoning model available for complex agentic tasks.
    Primary: NVIDIA Nemotron 3 Ultra 550B
    Fallback: Groq LLaMA 3.3 70B
    """
    if settings.NVIDIA_API_KEY:
        from langchain_openai import ChatOpenAI
        frontier_llm = ChatOpenAI(
            model="nvidia/nemotron-3-ultra-550b-a55b",
            api_key=settings.NVIDIA_API_KEY,
            base_url="https://integrate.api.nvidia.com/v1",
            max_retries=1,
            model_kwargs={"extra_body": {"chat_template_kwargs": {"enable_thinking": True}, "reasoning_budget": 16384}}
        )
        
        # Fallback to Groq if NVIDIA fails
        if settings.GROQ_API_KEY:
            frontier_llm = frontier_llm.with_fallbacks([
                ChatGroq(model="llama-3.3-70b-versatile", max_retries=1, api_key=settings.GROQ_API_KEY)
            ])
            
        return frontier_llm
    
    # If no NVIDIA key, default to the robust cascade
    return get_robust_llm()

def get_writer_llm():
    """Returns the LLM for writing responses. Can be customized later."""
    return get_robust_llm()

def get_critic_llm():
    """Returns the LLM for critiquing responses. Can be customized later."""
    return get_frontier_llm()
