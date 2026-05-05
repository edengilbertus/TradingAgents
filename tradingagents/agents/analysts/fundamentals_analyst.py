from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_balance_sheet,
    get_cashflow,
    get_fundamentals,
    get_global_news,
    get_income_statement,
    get_insider_transactions,
    get_language_instruction,
    get_news,
)
from tradingagents.dataflows.config import get_config
from tradingagents.dataflows.forex import parse_forex_pair
from tradingagents.dataflows.indices import parse_index


def create_fundamentals_analyst(llm):
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        instrument_context = build_instrument_context(ticker)
        forex_pair = parse_forex_pair(ticker)
        index_info = parse_index(ticker)

        if forex_pair:
            tools = [
                get_fundamentals,
                get_news,
                get_global_news,
            ]
            system_message = (
                f"You are a macro fundamentals analyst for the forex pair "
                f"{forex_pair.display_symbol}. Write a comprehensive report on "
                f"relative {forex_pair.base} versus {forex_pair.quote} fundamentals: "
                "central-bank policy divergence, rate expectations, real yields, "
                "inflation, labor markets, growth, fiscal policy, trade/current "
                "account balances, commodity exposure, safe-haven demand, carry, "
                "liquidity, and geopolitical risk. Use get_fundamentals for the "
                "FX macro framework and current exchange-rate context, then use "
                "get_news and get_global_news for recent macro catalysts. Avoid "
                "equity-only financial statement analysis."
                + " Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."
                + get_language_instruction()
            )
        elif index_info:
            tools = [
                get_fundamentals,
                get_news,
                get_global_news,
            ]
            system_message = (
                f"You are a macro fundamentals analyst for the market index "
                f"{index_info.name} ({index_info.yfinance_symbol}). This index "
                f"tracks {index_info.components_desc}. Write a comprehensive "
                "report on index-level macro fundamentals: monetary policy and "
                "interest rate outlook, inflation trends, GDP/growth data, "
                "employment figures, corporate earnings season (aggregate), "
                "sector composition and rotation, market breadth, fund flows, "
                "cross-asset signals (dollar, bonds, credit spreads, VIX), and "
                "geopolitical/regulatory risks. Use get_fundamentals for the "
                "index macro framework, then use get_news and get_global_news "
                "for recent macro catalysts. Do NOT use equity-specific financial "
                "statement tools (balance sheet, cash flow, income statement) — "
                "they are not applicable to market indices."
                + " Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."
                + get_language_instruction()
            )
        else:
            tools = [
                get_fundamentals,
                get_balance_sheet,
                get_cashflow,
                get_income_statement,
            ]
            system_message = (
                "You are a researcher tasked with analyzing fundamental information over the past week about a company. Please write a comprehensive report of the company's fundamental information such as financial documents, company profile, basic company financials, and company financial history to gain a full view of the company's fundamental information to inform traders. Make sure to include as much detail as possible. Provide specific, actionable insights with supporting evidence to help traders make informed decisions."
                + " Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."
                + " Use the available tools: `get_fundamentals` for comprehensive company analysis, `get_balance_sheet`, `get_cashflow`, and `get_income_statement` for specific financial statements."
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
            "fundamentals_report": report,
        }

    return fundamentals_analyst_node
