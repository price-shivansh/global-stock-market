import React, { useState } from 'react';
import {
  TrendingUp, TrendingDown, Target, ShieldAlert, CheckCircle2, Activity, Newspaper, BarChart2, Info
} from 'lucide-react';

const QuantPanelMock = ({ symbol, onApplyPlan }) => {
  const [activeTab, setActiveTab] = useState('Overview');

  // Static mock data for Phase 1 UI
  const mockData = {
    symbol: symbol,
    bias: 'Bullish',
    confidence_score: 82.5,
    technical_score: 85.0,
    sentiment_score: 76.6,
    trade_plan: {
      entry_zone: { min: 100.5, max: 102.0 },
      stop_loss: 98.0,
      target_1: 105.0,
      target_2: 108.0,
      risk_reward_ratio: 2.0
    },
    explanation: {
      summary: "Strong technical setup supported by positive news sentiment. The asset has recently crossed above major moving averages and is showing strong accumulation patterns in the lower timeframes.",
      technical_details: [
        "RSI is recovering from oversold territory (currently at 45).",
        "MACD shows a recent bullish crossover on the 1H chart.",
        "Price is trading above the 50 EMA, acting as dynamic support.",
        "Volume profile indicates strong accumulation at the 100 level."
      ],
      sentiment_details: [
        "Recent news sentiment is 76% bullish across 14 major outlets.",
        "Key headlines mention strong quarterly guidance and potential upgrades.",
        "Social media volume has spiked 120% in the last 4 hours."
      ]
    }
  };

  const getBiasColor = (bias) => {
    return 'text-[#00ff88] bg-[#00ff88]/10 border-[#00ff88]/20';
  };

  const handleApply = () => {
    if (onApplyPlan) {
      onApplyPlan({
        direction: 'BUY',
        stopLoss: mockData.trade_plan.stop_loss,
        target: mockData.trade_plan.target_1,
        symbol: symbol
      });
    }
  };

  const tabs = ['Overview', 'Technical', 'News'];

  return (
    <div className="flex flex-col bg-[#030f1e] border border-[#00ff88]/20 rounded-md relative min-h-min">
      {/* Corner accents */}
      <span className="absolute top-0 left-0 w-2 h-2 border-t border-l border-[#00ff88]" />
      <span className="absolute top-0 right-0 w-2 h-2 border-t border-r border-[#00ff88]" />
      <span className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-[#00ff88]" />
      <span className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-[#00ff88]" />

      {/* Header Summary Row */}
      <div className="flex justify-between items-center px-4 py-3 bg-[#00ff88]/5 border-b border-[#00ff88]/10 flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <Activity size={18} className="text-[#00ff88]" />
          <h3 className="text-sm font-bold text-white font-['Orbitron'] tracking-wider">
            QUANT DECISION ENGINE
          </h3>
          <span className={`px-2 py-0.5 rounded text-xs font-bold border flex items-center gap-1 ${getBiasColor(mockData.bias)}`}>
            <TrendingUp size={14} /> {mockData.bias}
          </span>
        </div>
        <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5 hidden sm:flex">
                <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Tech</span>
                <span className="text-sm font-bold text-gray-300">{mockData.technical_score}</span>
            </div>
            <div className="flex items-center gap-1.5 hidden sm:flex">
                <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Sent</span>
                <span className="text-sm font-bold text-gray-300">{mockData.sentiment_score}</span>
            </div>
            <div className="h-4 w-px bg-gray-700 hidden sm:block"></div>
            <div className="flex items-center gap-2">
                <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">Confidence</span>
                <span className="text-lg font-black text-[#00ff88] drop-shadow-[0_0_8px_rgba(0,255,136,0.5)]">
                    {mockData.confidence_score}%
                </span>
            </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex px-4 border-b border-[#00ff88]/10 bg-black/20">
        {tabs.map(tab => (
            <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`py-2 px-4 text-xs font-['Orbitron'] tracking-wider transition-colors border-b-2 ${activeTab === tab ? 'text-[#00ff88] border-[#00ff88] bg-[#00ff88]/5' : 'text-gray-500 border-transparent hover:text-gray-300'}`}
            >
                {tab}
            </button>
        ))}
      </div>

      {/* Tab Content Area */}
      <div className="p-4 flex flex-col gap-4">
        
        {/* Overview Tab */}
        {activeTab === 'Overview' && (
            <div className="flex flex-col lg:flex-row gap-6">
                {/* Summary */}
                <div className="flex-1">
                    <p className="text-[#00eeff] font-medium text-xs font-['Share_Tech_Mono'] leading-relaxed mb-4">
                    &gt; {mockData.explanation.summary}
                    </p>
                    
                    <div className="grid grid-cols-2 gap-4 mt-2">
                        <div className="bg-[#00ff88]/5 border border-[#00ff88]/10 rounded p-3">
                            <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider block mb-1">Technical Score</span>
                            <div className="text-xl font-bold text-white">{mockData.technical_score}</div>
                        </div>
                        <div className="bg-[#00ff88]/5 border border-[#00ff88]/10 rounded p-3">
                            <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider block mb-1">Sentiment Score</span>
                            <div className="text-xl font-bold text-white">{mockData.sentiment_score}</div>
                        </div>
                    </div>
                </div>

                {/* Trade Plan */}
                <div className="w-full lg:w-[280px] shrink-0 bg-[#00ff88]/5 border border-[#00ff88]/20 rounded p-4">
                    <h4 className="text-[10px] text-[#00ff88] font-bold uppercase tracking-widest mb-3 flex items-center gap-2">
                    <Target size={12} /> Suggested Plan
                    </h4>
                    
                    <div className="space-y-2 mb-4">
                        <div className="flex justify-between items-center">
                            <span className="text-xs text-gray-400 uppercase tracking-wider">Entry Zone</span>
                            <span className="font-['Share_Tech_Mono'] text-white text-sm">{mockData.trade_plan.entry_zone.min.toFixed(2)} - {mockData.trade_plan.entry_zone.max.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between items-center">
                            <span className="text-xs text-gray-400 uppercase tracking-wider flex items-center gap-1"><ShieldAlert size={10} className="text-[#ff2244]" /> Stop Loss</span>
                            <span className="font-['Share_Tech_Mono'] text-[#ff2244] text-sm">{mockData.trade_plan.stop_loss.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between items-center">
                            <span className="text-xs text-gray-400 uppercase tracking-wider">Target 1</span>
                            <span className="font-['Share_Tech_Mono'] text-[#00ff88] text-sm">{mockData.trade_plan.target_1.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between items-center">
                            <span className="text-xs text-gray-400 uppercase tracking-wider">Target 2</span>
                            <span className="font-['Share_Tech_Mono'] text-[#00ff88] text-sm">{mockData.trade_plan.target_2.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between items-center pt-2 border-t border-[#00ff88]/10">
                            <span className="text-xs text-gray-400 uppercase tracking-wider">Risk / Reward</span>
                            <span className="font-['Share_Tech_Mono'] text-[#ffaa00] text-sm">1 : {mockData.trade_plan.risk_reward_ratio}</span>
                        </div>
                    </div>

                    <button 
                    onClick={handleApply}
                    className="w-full bg-[#00ff88]/20 hover:bg-[#00ff88]/30 border border-[#00ff88] text-[#00ff88] font-['Orbitron'] text-xs tracking-wider py-2 rounded transition-colors"
                    >
                    APPLY TO ORDER FORM
                    </button>
                </div>
            </div>
        )}

        {/* Technical Tab */}
        {activeTab === 'Technical' && (
            <div className="bg-black/20 rounded p-4 border border-gray-800">
                <h4 className="text-[11px] text-[#00ff88] font-bold uppercase tracking-widest mb-3 flex items-center gap-2">
                    <BarChart2 size={14} /> Technical Factors
                </h4>
                <div className="max-h-[160px] overflow-y-auto pr-2" style={{ scrollbarWidth: 'thin', scrollbarColor: '#00ff88 transparent' }}>
                    <ul className="space-y-3">
                        {mockData.explanation.technical_details.map((d, i) => (
                        <li key={i} className="text-xs text-gray-300 flex items-start gap-2 leading-relaxed">
                            <CheckCircle2 size={14} className="text-[#00ff88] mt-0.5 shrink-0" />
                            <span>{d}</span>
                        </li>
                        ))}
                    </ul>
                </div>
            </div>
        )}

        {/* News Tab */}
        {activeTab === 'News' && (
            <div className="bg-black/20 rounded p-4 border border-gray-800">
                <h4 className="text-[11px] text-[#aa44ff] font-bold uppercase tracking-widest mb-3 flex items-center gap-2">
                    <Newspaper size={14} /> Sentiment & News Context
                </h4>
                <div className="max-h-[160px] overflow-y-auto pr-2" style={{ scrollbarWidth: 'thin', scrollbarColor: '#aa44ff transparent' }}>
                    <ul className="space-y-3">
                        {mockData.explanation.sentiment_details.map((d, i) => (
                        <li key={i} className="text-xs text-gray-300 flex items-start gap-2 leading-relaxed">
                            <Info size={14} className="text-[#aa44ff] mt-0.5 shrink-0" />
                            <span>{d}</span>
                        </li>
                        ))}
                    </ul>
                </div>
            </div>
        )}

      </div>
    </div>
  );
};

export default QuantPanelMock;
