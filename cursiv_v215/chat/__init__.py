"""
Cursiv's chat engine, in parts. ui/chat_app.py routes each message and
re-exports these names for older imports.

  keys        -- saved AI keys (encrypted, see core/keystore.py) and key checks
  web_search  -- DuckDuckGo / Brave search, only when asked (core/netgate.py)
  file_tools  -- the AI's file tools and the code that runs them
  paid        -- xAI, OpenAI and Claude
"""
