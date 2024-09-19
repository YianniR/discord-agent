import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from new_agent import ChatAgent

load_dotenv()
discord_bot_token = os.getenv('DISCORD_BOT_TOKEN')
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
tavily_api_key = os.getenv("TAVILY_API_KEY")

client = commands.Bot(command_prefix='!', intents=discord.Intents.all())

# # Optionally load the vector store from the pickle file
# vectorstore_path = 'vectorstores/vectorstore.pkl'
# vectorstore = None
# if os.path.exists(vectorstore_path):
#     with open(vectorstore_path, 'rb') as f:
#         vectorstore = pickle.load(f)

# Load base prompt from text file with UTF-8 encoding
with open('base_prompt.txt', encoding='utf-8') as f:
    base_prompt = f.read()

agent = ChatAgent(
    anthropic_api_key=anthropic_api_key,
    tavily_api_key=tavily_api_key,
    base_prompt=base_prompt
)

async def reply_to_user(ctx, reply):
    await ctx.send(reply)

@client.event
async def on_ready():
    print("Logged in as {0.user}".format(client))

@client.event
async def on_reaction_add(reaction, user):
    print(reaction.emoji)
    ctx = await client.get_context(reaction.message)
    async with ctx.typing():
        if reaction.emoji == "✅":
            message = reaction.message
            await message.reply("Searching fact checking websites to assess the claim. Please wait...")

            prompt = f"Fact check the following user message, cross reference using online resources. \n \
            User message: \"{message.content}\" \n \
            "
            response = agent.get_response(prompt)

            await message.reply(response)

@client.command(name="summarize", category="General")
async def summarize(ctx):
    await reply_to_user(ctx, "I am summarizing the conversation in this channel. This may take some time, please be patient.")
    n = int(ctx.message.content.replace('!summarize', '').strip())

    messages = []
    async for msg in ctx.channel.history(limit=n):
        messages.append(msg)
    messages_text = '\n'.join([msg.content for msg in messages[::-1]])

    prompt = f"Summarize the following messages. Provide a summary of each participant's views separately, and highlight any key points of agreement or disagreement. Messages: {messages_text}"
    response = agent.get_response(prompt)
    await reply_to_user(ctx, response)
summarize.help = "Summarizes the given text into a shorter, more concise version."

@client.command(name="define", category="General")
async def define(ctx):

    await ctx.message.reply("Searching online dictionaries. Please wait...")

    base_prompt = "I want to give you a word, and then you search the Twitter API. "

    # Check if the command is a reply to a message in a thread
    if isinstance(ctx.message.reference.resolved, discord.Message):
        parent_message = ctx.message.reference.resolved
        term = ctx.message.content.replace('!define', '').strip()

        await ctx.send(f"Defining term {term}, in content: {parent_message.content}")

        prompt = f"Define the term \"{term}\", in the following context: \"{parent_message.content}\". Cross reference using online resources. Return your answer in bullet points"
        response = agent.get_response(base_prompt + prompt)
        await reply_to_user(ctx, response)

    else:

        term = ctx.message.content.replace('!define', '').strip()

        prompt = f"Define the term \"{term}\", cross reference using online resources. Return your answer in bullet points"

        response = agent.get_response(base_prompt + prompt)
        await reply_to_user(ctx, response)

        await ctx.send("If you wish to provide context, use this command in a thread reply for the message you wish to use as context.")
related.help = "Returns the definition to a term."

@client.command(name="exit", category="General")
async def exit(ctx):
    exit()

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('!'):
        await client.process_commands(message)

    elif client.user.mentioned_in(message):

        ctx = await client.get_context(message)
        
        async with ctx.typing():
            prompt = f'{message.content}'.format(message.content)            
            print(prompt)
            response = agent.get_response(message=prompt)
        
        await reply_to_user(ctx, response)

client.run(discord_bot_token)
