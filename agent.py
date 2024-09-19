from dateutil.parser import parse
from datetime import datetime 

from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint import MemorySaver
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
# from langchain_community.tools.tavily_search import TavilySearchResults
# from langchain.tools.retriever import create_retriever_tool

from fetch_data import AccountFetcher, TweetFetcher

@tool
def fetch_twitter_data(username='', keywords=[]):
    """Use this to search the twitter API. Username and keywords are optional."""
    
    account_fetcher = AccountFetcher()
    tweet_fetcher = TweetFetcher()
    
    start_date="2024-01-01"
    end_date="2024-12-31"
    start_date = datetime.strptime(start_date, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
    end_date = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)

    account_id = None
    if username:
        # Fetch and save accounts
        accounts = account_fetcher.fetch_all()
        if not accounts:
            return None

        account_map = {str(account['username']): account['account_id'] for account in accounts}
        account_id = account_map.get(username)
        
        if account_id is None:
            return "No account found"

    user_tweets = tweet_fetcher.fetch_all(account_id, start_date, end_date, keywords)

    if not user_tweets:
        return "No tweets found"

    # Sort tweets by date in descending order
    user_tweets.sort(key=lambda x: parse(x['created_at']), reverse=True)

    return user_tweets[:100]

class ChatAgent:
    def __init__(self, anthropic_api_key, tavily_api_key, base_prompt, vectorstore=None):

        # Set up language model
        self.model = ChatAnthropic(model_name="claude-3-5-sonnet-20240620", api_key=anthropic_api_key)

        # Set up memory
        self.memory = MemorySaver()

        # hardcode thread id - TODO: create separate thread ids for different discord channels and threads
        self.config = {
            'configurable': {
                'thread_id': '1'
            }
        }

        # TODO: Add TavilySearchResults
        self.tools = [fetch_twitter_data]

        self.graph = create_react_agent(self.model, tools=self.tools, checkpointer=self.memory)

        # Add the system prompt
        inputs = {"messages": [("user", base_prompt)]}
        output = self.graph.stream(inputs, stream_mode="values", config=self.config)

        self.print_stream(output)

    def print_stream(self, stream):
        content = ""
        for s in stream:
            try:
                message = s["agent"]["messages"][-1]
                content = message.content
                if isinstance(message, tuple):
                    print(message)
                else:
                    message.pretty_print()
            except KeyError:
                continue
            
        return content

    def get_response(self, message=""):
        inputs = {"messages": [("user", message)]}
        content = self.print_stream(self.graph.stream(inputs, config=self.config))
        return content[:1999]
