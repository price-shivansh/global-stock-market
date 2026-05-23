import React, { useState, useEffect } from 'react';
import { analyzeSymbol } from '../../api/quantService';
import {
  TrendingUp, TrendingDown, Minus, Target, ShieldAlert,
  Activity, Newspaper, AlertCircle, Info
} from 'lucide-react';

const QuantDashboard = ({ symbol }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!symbol) return;
    
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await analyzeSymbol(symbol);
        setData(result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [symbol]);

  if (!symbol) {
    return (
      <div className="p-8 text-center bg-[#1A1E29] rounded-2xl border border-gray-800 text-gray-400">
        Select an asset to view Quant Intelligence
      </div>
    );
  }

  if (loading) {
    return (
      <div className="p-8 bg-[#1A1E29] rounded-2xl border border-gray-800 animate-pulse flex flex-col items-center justify-center min-h-[400px]">
        <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4"></div>
        <p className="text-blue-400 font-medium">Analyzing {symbol} via Quant Engine...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-900/20 rounded-2xl border border-red-500/30 flex items-start gap-4">
        <AlertCircle className="text-red-400 shrink-0 mt-1" size={24} />
        <div>
          <h3 className="text-red-400 font-bold text-lg">Analysis Failed</h3>
          <p className="text-red-300 mt-1">{error}</p>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const getBiasColor = (bias) => {
    switch(bias.toLowerCase()) {
      case 'bullish': return 'text-green-400 bg-green-400/10 border-green-400/20';
      case 'bearish': return 'text-red-400 bg-red-400/10 border-red-400/20';
      default: return 'text-gray-400 bg-gray-400/10 border-gray-400/20';
    }
  };

  const getBiasIcon = (bias) => {
    switch(bias.toLowerCase()) {
      case 'bullish': return <TrendingUp size={24} className="text-green-400" />;
      case 'bearish': return <TrendingDown size={24} className="text-red-400" />;
      default: return <Minus size={24} className="text-gray-400" />;
    }
  };

  // Ensure TP1 is nicely formatted
  const tp1 = data.trade_plan?.target_1;
  const sl = data.trade_plan?.stop_loss;

  return (
    <div className="bg-[#1A1E29] rounded-2xl border border-gray-800 overflow-hidden shadow-2xl">
      {/* Header Area */}
      <div className="bg-gradient-to-r from-gray-900 to-[#1A1E29] p-6 border-b border-gray-800 flex justify-between items-center flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h2 className="text-2xl font-black text-white tracking-tight">{data.symbol}</h2>
            <span className={`px-3 py-1 rounded-full text-sm font-bold border flex items-center gap-1.5 ${getBiasColor(data.bias)}`}>
              {getBiasIcon(data.bias)}
              {data.bias}
            </span>
          </div>
          <p className="text-gray-400 text-sm flex items-center gap-1">
            <Info size={14} /> Quant Decision Engine Output
          </p>
        </div>
        
        {/* Confidence Gauge Area */}
        <div className="flex flex-col items-end">
          <div className="text-sm text-gray-400 font-semibold uppercase tracking-wider mb-1">Model Confidence</div>
          <div className="flex items-end gap-2">
            <span className="text-4xl font-black bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-indigo-400">
              {data.confidence_score}
            </span>
            <span className="text-gray-500 font-bold mb-1 text-lg">/ 100</span>
          </div>
        </div>
      </div>

      <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Col - Scores & Why */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Sub-Scores */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700/50">
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-400 text-sm font-medium flex items-center gap-2">
                  <Activity size={16} className="text-blue-400" /> Technical Score
                </span>
                <span className="text-xs font-bold px-2 py-0.5 rounded bg-blue-500/20 text-blue-300">70% Weight</span>
              </div>
              <div className="text-2xl font-bold text-white">{data.technical_score}<span className="text-gray-500 text-sm ml-1">/100</span></div>
            </div>
            <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700/50">
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-400 text-sm font-medium flex items-center gap-2">
                  <Newspaper size={16} className="text-purple-400" /> Sentiment Score
                </span>
                <span className="text-xs font-bold px-2 py-0.5 rounded bg-purple-500/20 text-purple-300">30% Weight</span>
              </div>
              <div className="text-2xl font-bold text-white">{data.sentiment_score}<span className="text-gray-500 text-sm ml-1">/100</span></div>
            </div>
          </div>

          {/* Explanation */}
          <div className="bg-gray-800/30 rounded-xl p-5 border border-gray-700/50">
            <h3 className="text-white font-bold text-lg mb-3 flex items-center gap-2">
               Analysis Reasoning
            </h3>
            <p className="text-blue-200 mb-4 font-medium leading-relaxed">{data.explanation.summary}</p>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="text-xs uppercase text-gray-500 font-bold tracking-wider mb-2">Technical Factors</h4>
                <ul className="space-y-2">
                  {data.explanation.technical_details.map((detail, idx) => (
                    <li key={idx} className="text-sm text-gray-300 flex items-start gap-2">
                      <span className="text-blue-500 mt-0.5">•</span>
                      <span>{detail}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h4 className="text-xs uppercase text-gray-500 font-bold tracking-wider mb-2">News Context</h4>
                <ul className="space-y-2">
                  {data.explanation.sentiment_details.map((detail, idx) => (
                    <li key={idx} className="text-sm text-gray-300 flex items-start gap-2">
                      <span className="text-purple-500 mt-0.5">•</span>
                      <span>{detail}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>

        </div>

        {/* Right Col - Trade Plan */}
        <div className="bg-gray-800/40 rounded-xl p-5 border border-gray-700">
          <h3 className="text-white font-bold text-lg mb-4 flex items-center gap-2">
             Suggested Trade Plan
          </h3>
          
          {data.bias === 'Neutral' ? (
            <div className="text-center py-8 text-gray-400">
              <Minus size={32} className="mx-auto mb-2 opacity-50" />
              <p>Conditions are neutral.</p>
              <p className="text-sm">No trade plan generated.</p>
            </div>
          ) : (
            <div className="space-y-5">
              
              <div className="flex justify-between items-center pb-3 border-b border-gray-700/50">
                <span className="text-gray-400 text-sm">Action</span>
                <span className={`font-bold uppercase ${data.bias === 'Bullish' ? 'text-green-400' : 'text-red-400'}`}>
                  {data.bias === 'Bullish' ? 'BUY / LONG' : 'SELL / SHORT'}
                </span>
              </div>

              <div className="space-y-1">
                <span className="text-gray-400 text-xs font-bold uppercase tracking-wider">Entry Zone</span>
                <div className="text-xl font-mono text-white flex justify-between">
                  {data.trade_plan.entry_zone.min.toFixed(2)} - {data.trade_plan.entry_zone.max.toFixed(2)}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="bg-red-900/10 border border-red-500/20 rounded-lg p-3">
                  <span className="text-red-400 text-xs font-bold uppercase flex items-center gap-1 mb-1">
                    <ShieldAlert size={12} /> Stop Loss
                  </span>
                  <div className="text-lg font-mono text-white">{sl?.toFixed(2)}</div>
                </div>
                <div className="bg-green-900/10 border border-green-500/20 rounded-lg p-3">
                  <span className="text-green-400 text-xs font-bold uppercase flex items-center gap-1 mb-1">
                    <Target size={12} /> Target 1
                  </span>
                  <div className="text-lg font-mono text-white">{tp1?.toFixed(2)}</div>
                </div>
              </div>

              {data.trade_plan.target_2 && (
                <div className="flex justify-between items-center text-sm border-t border-gray-700/50 pt-3">
                  <span className="text-gray-400">Target 2 (Extended)</span>
                  <span className="font-mono text-white">{data.trade_plan.target_2.toFixed(2)}</span>
                </div>
              )}

              <div className="flex justify-between items-center text-sm pt-1">
                <span className="text-gray-400">Risk/Reward</span>
                <span className="font-mono text-yellow-400 font-bold">1 : {data.trade_plan.risk_reward_ratio}</span>
              </div>

              <button 
                disabled
                className="w-full mt-4 bg-gray-700 text-gray-400 py-3 rounded-lg font-bold text-sm cursor-not-allowed border border-gray-600 transition-colors"
                title="Paper trading integration coming in Phase 2"
              >
                Paper Trade (Coming Soon)
              </button>

            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default QuantDashboard;
