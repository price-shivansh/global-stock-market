import math
from typing import List, Dict, Any, Tuple

class SummaryEngine:
    def __init__(self):
        pass

    def build_summary_paragraph(self, bias: str, confidence: float, ta_score: float, news_score: float, strongest_indicator: str, strongest_signal: str) -> str:
        summary = f"The market exhibits a {bias} bias with a {confidence:.1f}% confidence score"
        
        # Determine driver phrase
        if ta_score >= 60 and news_score >= 60:
            summary += ", driven by converging positive technicals and supportive news."
        elif ta_score <= 40 and news_score <= 40:
            summary += ", driven by converging negative technicals and bearish news."
        elif ta_score >= 60 and news_score < 40:
            summary += ", driven primarily by strong technical momentum, despite bearish news headwinds."
        elif ta_score <= 40 and news_score >= 60:
            summary += ", driven primarily by weak technicals, despite some supportive news."
        elif ta_score >= 60:
            summary += ", driven predominantly by strong technical indicators."
        elif ta_score <= 40:
            summary += ", driven predominantly by weak technical indicators."
        elif news_score >= 60:
            summary += ", driven largely by positive market sentiment with neutral technicals."
        elif news_score <= 40:
            summary += ", driven largely by negative market sentiment with neutral technicals."
        else:
            summary += ", reflecting a largely neutral and consolidating market environment."

        if strongest_indicator and strongest_signal:
            summary += f" Notably, {strongest_indicator} is signaling a {strongest_signal}."
            
        return summary

    def build_technical_bullets(self, ta_details: List[Dict[str, Any]]) -> List[str]:
        bullets = []
        for detail in ta_details:
            name = detail.get('name', 'Indicator')
            signal = detail.get('signal', 'NEUTRAL')
            val = detail.get('value')
            
            if signal == 'NEUTRAL':
                continue
                
            if name == 'MACD':
                if signal == 'BUY':
                    bullets.append("MACD is above the signal line, indicating bullish momentum.")
                else:
                    bullets.append("MACD is below the signal line, indicating bearish momentum.")
            elif 'RSI' in name:
                bullets.append(f"RSI is at {val}, showing a {signal.lower()} trajectory.")
            elif 'EMA' in name or 'SMA' in name:
                bullets.append(f"Price is trading {'above' if signal == 'BUY' else 'below'} the {name}, confirming the short-term trend.")
            elif name == 'Momentum(10)':
                bullets.append(f"10-period momentum is {'positive' if signal == 'BUY' else 'negative'} ({val}).")
            elif name == 'Bollinger Bands':
                if signal == 'BUY':
                    bullets.append("Price is near the lower Bollinger Band, suggesting potential oversold conditions.")
                else:
                    bullets.append("Price is near the upper Bollinger Band, suggesting potential overbought conditions.")
            else:
                bullets.append(f"{name} is exhibiting a {signal} signal.")
                
        if not bullets:
            bullets.append("Technical indicators are predominantly neutral.")
            
        return bullets[:4] # Return top 4 bullets to keep it concise

    def extract_news_drivers(self, relevant_news: List[Any]) -> List[str]:
        # relevant_news is a list of NewsItem objects (pydantic or from models.py)
        drivers = []
        
        pos_news = []
        neg_news = []
        
        for item in relevant_news:
            score = getattr(item, 'sentiment_score', 0)
            title = getattr(item, 'title', '')
            if score > 0.1:
                pos_news.append((score, title))
            elif score < -0.1:
                neg_news.append((score, title))
                
        # Sort by magnitude
        pos_news.sort(key=lambda x: x[0], reverse=True)
        neg_news.sort(key=lambda x: x[0]) # Lowest (most negative) first
        
        for _, title in pos_news[:2]:
            drivers.append(f"+ {title}")
            
        for _, title in neg_news[:2]:
            drivers.append(f"- {title}")
            
        if not drivers:
            drivers.append("No highly impactful directional news found recently.")
            
        return drivers

    def generate_risk_warnings(self, ta_details: List[Dict[str, Any]], ta_score: float, news_score: float, confidence: float) -> List[str]:
        warnings = []
        
        # Rule 1: Overbought / Oversold
        for detail in ta_details:
            if 'RSI' in detail.get('name', ''):
                val = detail.get('value', 50)
                if val is not None and isinstance(val, (int, float)):
                    if val > 70:
                        warnings.append(f"Asset is technically overbought (RSI {val}). Risk of pullback.")
                    elif val < 30:
                        warnings.append(f"Asset is technically oversold (RSI {val}). Potential for bounce.")
        
        # Rule 2: Divergence
        if abs(ta_score - news_score) >= 40:
            if ta_score > news_score:
                warnings.append("Divergence Warning: Technicals are bullish, but news sentiment is lagging. Expect volatility.")
            else:
                warnings.append("Divergence Warning: News sentiment is supportive, but technicals remain weak.")
                
        # Rule 3: Low Confidence / Range-bound
        if 40 <= confidence <= 60:
            warnings.append("Market is currently range-bound with conflicting signals. Caution advised.")
            
        if not warnings:
            warnings.append("No extreme risks detected in current conditions.")
            
        return warnings

    def generate_summary(self, bias: str, confidence: float, ta_score: float, news_score: float, ta_details: List[Dict[str, Any]], relevant_news: List[Any]) -> Tuple[str, List[str], List[str], List[str]]:
        
        # Find strongest indicator for the paragraph
        strongest_indicator = ""
        strongest_signal = ""
        for detail in ta_details:
            if detail.get('signal') != 'NEUTRAL':
                strongest_indicator = detail.get('name', '')
                strongest_signal = detail.get('signal', '')
                break # Just take the first active one
                
        ai_summary = self.build_summary_paragraph(bias, confidence, ta_score, news_score, strongest_indicator, strongest_signal)
        tech_bullets = self.build_technical_bullets(ta_details)
        news_drivers = self.extract_news_drivers(relevant_news)
        warnings = self.generate_risk_warnings(ta_details, ta_score, news_score, confidence)
        
        return ai_summary, tech_bullets, news_drivers, warnings

summary_engine = SummaryEngine()
