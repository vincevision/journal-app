from groq import Groq


def get_ai_analysis(trade_data: dict, api_key: str) -> str:
    client = Groq(api_key=api_key)

    prompt = build_prompt(trade_data)

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": """You are an expert SMC (Smart Money Concepts) trading analyst 
and journal coach. You analyze trades using ICT/SMC methodology including:
- Market Structure (BoS, CHoCH, higher highs/lows, lower highs/lows)
- Order Blocks (Bullish OB, Bearish OB, Mitigation Blocks, Breaker Blocks)
- Fair Value Gaps (FVG / Imbalances)
- Liquidity concepts (BSL, SSL, EQH, EQL, inducement, sweeps)
- Premium/Discount arrays
- Multi-timeframe analysis (HTF bias → LTF entry)
- Kill zones and sessions

Your job is to provide a comprehensive, structured analysis of each trade journal entry.
Be specific, actionable, and educational. Point out what was done correctly, 
what could be improved, and extract lessons for future trades.
Format your response with clear sections using markdown."""
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        model="llama-3.3-70b-versatile",
        temperature=0.3,
        max_tokens=4000,
    )

    return chat_completion.choices[0].message.content


def build_prompt(td: dict) -> str:
    liq_info = ""
    if td.get('liquidity_sweep'):
        liq_info = f"Yes — {td.get('liquidity_type', 'N/A')}"
    else:
        liq_info = "No / Not marked"

    refined_info = ""
    if td.get('refined_entry'):
        refined_info = f"Yes — {td.get('refined_poi', 'N/A')}"
    else:
        refined_info = "No — used unrefined zone"

    prompt = f"""
Analyze this SMC trade journal entry in detail:

═══════════════════════════════════════
TRADE OVERVIEW
═══════════════════════════════════════
Pair: {td.get('pair', 'N/A')}
Direction: {td.get('direction', 'N/A')}
Outcome: {td.get('outcome', 'N/A')}
Date: {td.get('date', 'N/A')}
Session: {td.get('session', 'N/A')}

═══════════════════════════════════════
HTF ANALYSIS (Macro Direction)
═══════════════════════════════════════
HTF Bias: {td.get('htf_bias', 'N/A')}
HTF Timeframe: {td.get('htf_timeframe', 'N/A')}
HTF Structure: {td.get('htf_structure', 'N/A')}
POI Type: {td.get('poi_type', 'N/A')}
POI Timeframe: {td.get('poi_timeframe', 'N/A')}

═══════════════════════════════════════
LTF CONFIRMATION (Entry Trigger)
═══════════════════════════════════════
LTF Timeframe: {td.get('ltf_timeframe', 'N/A')}
LTF Trigger: {td.get('ltf_trigger', 'N/A')}
Liquidity Sweep: {liq_info}
Refined Entry: {refined_info}

═══════════════════════════════════════
TRADE EXECUTION
═══════════════════════════════════════
Entry Price: {td.get('entry_price', 'N/A')}
Stop Loss: {td.get('sl_price', 'N/A')}
TP1: {td.get('tp1_price', 'N/A')}
TP2: {td.get('tp2_price', 'N/A')}
Risk:Reward: {td.get('risk_reward', 'N/A')}
P&L: {td.get('pnl', 'N/A')}

═══════════════════════════════════════
TRADER NOTES
═══════════════════════════════════════
Pre-Trade Plan: {td.get('pre_trade_notes', 'N/A')}
Post-Trade Review: {td.get('post_trade_notes', 'N/A')}
Mistakes Identified: {td.get('mistakes', 'N/A')}
Lessons: {td.get('lessons', 'N/A')}

═══════════════════════════════════════
EMOTIONAL STATE
═══════════════════════════════════════
Before: {td.get('emotion_before', 'N/A')}
During: {td.get('emotion_during', 'N/A')}
After: {td.get('emotion_after', 'N/A')}

Please provide:

1. **CONTEXT ANALYSIS** — Was the HTF bias correctly identified? Was the structure read 
   (BoS/CHoCH) valid for the directional bias? Was the POI appropriate?

2. **ENTRY QUALITY ASSESSMENT** — Rate the entry trigger. Was the LTF confirmation 
   (CHoCH + OB/FVG) properly waited for? Was the liquidity sweep meaningful? 
   Was refining the zone the right call (or not)?

3. **RISK MANAGEMENT REVIEW** — Was the SL placement logical (above/below the 
   POI structure)? Was the R:R adequate? Were TPs at logical levels 
   (opposing HTF structure, liquidity pools)?

4. **EXECUTION SUMMARY TABLE** — Create a clear summary table like:
   | Step | What Was Done | Assessment |
   |------|--------------|------------|
   | HTF Bias | ... | ✅/⚠️/❌ |
   | POI | ... | ... |
   | LTF Trigger | ... | ... |
   | SL Placement | ... | ... |
   | TP Levels | ... | ... |

5. **KEY LESSON** — What is the single most important takeaway from this trade?

6. **IMPROVEMENT SUGGESTIONS** — 2-3 specific, actionable improvements for next time.

7. **PATTERN RECOGNITION** — If this is a {td.get('outcome')} trade, what pattern 
   or mistake led to this outcome? What should be repeated (if win) or avoided (if loss)?
"""
    return prompt