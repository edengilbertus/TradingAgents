from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_global_news,
    get_language_instruction,
    get_news,
)
from tradingagents.dataflows.config import get_config
from tradingagents.dataflows.forex import parse_forex_pair
from tradingagents.dataflows.indices import parse_index


def create_news_analyst(llm):
    def news_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        instrument_context = build_instrument_context(ticker)
        forex_pair = parse_forex_pair(ticker)
        index_info = parse_index(ticker)

        tools = [
            get_news,
            get_global_news,
        ]

        if forex_pair:
            news_role = (
                f"You are a forex macro-news researcher for {forex_pair.display_symbol}. "
                "Analyze the past week of currency-relevant news: central-bank "
                "communications, rate expectations, inflation and labor data, GDP "
                "surprises, fiscal headlines, geopolitical risk, commodity shocks, "
                "risk appetite, and cross-asset flows. "
            )
        elif index_info:
            news_role = (
                f"You are a macro-news researcher for the {index_info.name} "
                f"({index_info.yfinance_symbol}) market index. Analyze the past "
                "week of index-relevant news: central-bank decisions and forward "
                "guidance, economic data releases (jobs, CPI, GDP, PMIs), "
                "corporate earnings season trends, sector rotation catalysts, "
                "fiscal and regulatory policy changes, geopolitical developments, "
                "fund flow data, and cross-asset signals (bonds, dollar, "
                "commodities, volatility). "
            )
        else:
            news_role = (
                "You are a news researcher tasked with analyzing recent news and "
                "trends over the past week. Please write a comprehensive report "
                "of the current state of the world that is relevant for trading "
                "and macroeconomics. "
            )

        system_message = (
            news_role
            + "Use the available tools: get_news(query, start_date, end_date) for company-specific, currency-specific, or targeted news searches, and get_global_news(curr_date, look_back_days, limit) for broader macroeconomic news. Provide specific, actionable insights with supporting evidence to help traders make informed decisions."
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
            "news_report": report,
        }

    return news_analyst_node
