from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import build_instrument_context, get_language_instruction, get_news
from tradingagents.dataflows.config import get_config
from tradingagents.dataflows.forex import parse_forex_pair
from tradingagents.dataflows.indices import parse_index


def create_social_media_analyst(llm):
    def social_media_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        instrument_context = build_instrument_context(ticker)
        forex_pair = parse_forex_pair(ticker)
        index_info = parse_index(ticker)

        tools = [
            get_news,
        ]

        if forex_pair:
            role = (
                f"You are a forex sentiment analyst for {forex_pair.display_symbol}. "
                "Analyze public positioning, market commentary, trader sentiment, "
                "risk appetite, central-bank reaction, and currency-specific news "
                "over the past week. Focus on what sentiment implies for relative "
                f"{forex_pair.base} versus {forex_pair.quote} demand. "
            )
        elif index_info:
            role = (
                f"You are a market sentiment analyst for the {index_info.name} "
                f"({index_info.yfinance_symbol}) index. Analyze market-wide "
                "sentiment over the past week: retail and institutional "
                "positioning, put/call ratios, VIX and volatility sentiment, "
                "fund flow trends, social media market commentary, risk appetite "
                "indicators, sector rotation signals, and overall investor "
                "confidence. Focus on what sentiment implies for index direction. "
            )
        else:
            role = (
                "You are a social media and company specific news researcher/analyst "
                "tasked with analyzing social media posts, recent company news, and "
                "public sentiment for a specific company over the past week. "
            )

        system_message = (
            role
            + "Use the get_news(query, start_date, end_date) tool to search for company-specific, currency-specific, market sentiment, and social media discussions. Try to look at all sources possible from social media to sentiment to news. Provide specific, actionable insights with supporting evidence to help traders make informed decisions."
            + """ Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."""
            + get_language_instruction()
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. {instrument_context}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state["messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "sentiment_report": report,
        }

    return social_media_analyst_node
