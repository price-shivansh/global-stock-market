import React, { useEffect, useRef, useState } from 'react';
import { createChart, CrosshairMode, CandlestickSeries, AreaSeries } from 'lightweight-charts';

const LightweightChart = ({ data, type = 'candle', width = 0, height = 400 }) => {
    const chartContainerRef = useRef();
    const chartRef = useRef(null);
    const seriesRef = useRef(null);
    const [chartError, setChartError] = useState(null);

    useEffect(() => {
        if (!chartContainerRef.current) return;

        const handleResize = () => {
            if (chartRef.current && chartContainerRef.current) {
                chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
            }
        };

        try {
            const chart = createChart(chartContainerRef.current, {
                width: chartContainerRef.current.clientWidth,
                height: height,
                layout: {
                    background: { type: 'solid', color: 'transparent' },
                    textColor: 'rgba(0, 255, 136, 0.5)',
                    fontFamily: 'Share Tech Mono',
                },
                grid: {
                    vertLines: { color: 'rgba(0, 255, 136, 0.06)', style: 1 },
                    horzLines: { color: 'rgba(0, 255, 136, 0.06)', style: 1 },
                },
                crosshair: {
                    mode: CrosshairMode.Normal,
                    vertLine: {
                        color: 'rgba(0, 255, 136, 0.4)',
                        width: 1,
                        style: 1,
                        labelBackgroundColor: '#030f1e',
                    },
                    horzLine: {
                        color: 'rgba(0, 255, 136, 0.4)',
                        width: 1,
                        style: 1,
                        labelBackgroundColor: '#030f1e',
                    },
                },
                rightPriceScale: {
                    borderColor: 'rgba(0, 255, 136, 0.2)',
                },
                timeScale: {
                    borderColor: 'rgba(0, 255, 136, 0.2)',
                    timeVisible: true,
                    secondsVisible: false,
                },
            });
            chartRef.current = chart;

            // Add series based on type (v5 API)
            if (type === 'candle') {
                // Check if addCandlestickSeries exists (backwards compatibility), else use addSeries
                if (typeof chart.addCandlestickSeries === 'function') {
                    seriesRef.current = chart.addCandlestickSeries({
                        upColor: 'rgba(0, 255, 136, 0.8)',
                        downColor: 'rgba(255, 34, 68, 0.8)',
                        borderDownColor: 'rgba(255, 34, 68, 1)',
                        borderUpColor: 'rgba(0, 255, 136, 1)',
                        wickDownColor: 'rgba(255, 34, 68, 1)',
                        wickUpColor: 'rgba(0, 255, 136, 1)',
                    });
                } else {
                    seriesRef.current = chart.addSeries(CandlestickSeries, {
                        upColor: 'rgba(0, 255, 136, 0.8)',
                        downColor: 'rgba(255, 34, 68, 0.8)',
                        borderDownColor: 'rgba(255, 34, 68, 1)',
                        borderUpColor: 'rgba(0, 255, 136, 1)',
                        wickDownColor: 'rgba(255, 34, 68, 1)',
                        wickUpColor: 'rgba(0, 255, 136, 1)',
                    });
                }
            } else {
                if (typeof chart.addAreaSeries === 'function') {
                    seriesRef.current = chart.addAreaSeries({
                        lineColor: '#00ff88',
                        topColor: 'rgba(0, 255, 136, 0.22)',
                        bottomColor: 'rgba(0, 255, 136, 0)',
                        lineWidth: 2,
                    });
                } else {
                    seriesRef.current = chart.addSeries(AreaSeries, {
                        lineColor: '#00ff88',
                        topColor: 'rgba(0, 255, 136, 0.22)',
                        bottomColor: 'rgba(0, 255, 136, 0)',
                        lineWidth: 2,
                    });
                }
            }

            window.addEventListener('resize', handleResize);

            return () => {
                window.removeEventListener('resize', handleResize);
                chart.remove();
            };
        } catch (e) {
            console.error("Failed to initialize lightweight chart:", e);
            setChartError(e.message || "Failed to load chart");
        }
    }, [type, height]); // Re-create chart if type changes

    useEffect(() => {
        if (!seriesRef.current || !data || data.length === 0) return;

        // Transform data
        const formattedData = data.map(item => {
            // lightweight-charts needs time in UNIX timestamp format (seconds) or string 'YYYY-MM-DD'
            // Assuming item.date is an ISO string or 'YYYY-MM-DD HH:mm:ss'
            let timeValue;
            try {
                timeValue = new Date(item.date).getTime() / 1000;
            } catch (e) {
                timeValue = item.date;
            }

            if (type === 'candle') {
                return {
                    time: timeValue,
                    open: item.open,
                    high: item.high,
                    low: item.low,
                    close: item.close,
                };
            } else {
                return {
                    time: timeValue,
                    value: item.close,
                };
            }
        });
        
        // Sort and deduplicate data by time to prevent Lightweight Charts errors
        const uniqueData = Array.from(new Map(formattedData.map(item => [item.time, item])).values());
        uniqueData.sort((a, b) => a.time - b.time);

        try {
            seriesRef.current.setData(uniqueData);
            chartRef.current.timeScale().fitContent();
        } catch(e) {
            console.error("Lightweight charts data error:", e);
        }

    }, [data, type]);

    if (chartError) {
        return (
            <div style={{ width: '100%', height: `${height}px`, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(255, 34, 68, 0.05)', border: '1px solid rgba(255, 34, 68, 0.3)', borderRadius: '4px' }}>
                <span style={{ color: '#ff2244', fontFamily: 'Share Tech Mono', fontSize: '0.8rem' }}>Chart Error: {chartError}</span>
            </div>
        );
    }

    return (
        <div ref={chartContainerRef} style={{ width: '100%', height: `${height}px`, position: 'relative' }} />
    );
};

export default LightweightChart;
