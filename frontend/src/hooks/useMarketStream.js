/**
 * useMarketStream.js
 * Custom React hook for the WebSocket live market stream.
 * Returns { liveData, connected } where liveData is a Map<symbol, tick>.
 * Manages WebSocket lifecycle cleanly — connects when enabled, disconnects when not.
 */
import { useState, useEffect, useRef, useCallback } from 'react';

const getWsUrl = () => {
    const url = import.meta.env.VITE_WS_URL;
    if (!url) return `ws://${window.location.hostname}:8000/ws/market`;
    
    const cleanUrl = url.replace(/\/$/, ""); // Remove trailing slash
    const protocol = cleanUrl.startsWith('ws') ? "" : "wss://";
    const path = cleanUrl.includes('/ws/market') ? "" : "/ws/market";
    
    return `${protocol}${cleanUrl}${path}`;
};

const WS_URL = getWsUrl();

/**
 * @param {boolean} enabled - Toggle stream on/off
 * @returns {{ liveData: Map, connected: boolean }}
 */
export function useMarketStream(enabled) {
    const [liveData, setLiveData] = useState(new Map());
    const [connected, setConnected] = useState(false);
    const wsRef = useRef(null);
    const pingRef = useRef(null);

    const disconnect = useCallback(() => {
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
        if (pingRef.current) {
            clearInterval(pingRef.current);
            pingRef.current = null;
        }
        setConnected(false);
    }, []);

    const connect = useCallback(() => {
        if (wsRef.current) return; // already connected

        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
            setConnected(true);
            // Keep-alive ping every 10s (server ignores the content)
            pingRef.current = setInterval(() => {
                if (ws.readyState === WebSocket.OPEN) ws.send('ping');
            }, 10_000);
        };

        ws.onmessage = (event) => {
            try {
                const tick = JSON.parse(event.data);
                if (!tick?.symbol) return;

                setLiveData((prev) => {
                    const next = new Map(prev);
                    const old = next.get(tick.symbol);
                    // Attach direction for flash animation
                    tick.direction = old
                        ? tick.price > old.price ? 'up' : tick.price < old.price ? 'down' : old.direction
                        : 'neutral';
                    next.set(tick.symbol, tick);
                    return next;
                });
            } catch {
                // malformed JSON — ignore
            }
        };

        ws.onerror = () => setConnected(false);
        ws.onclose = () => { setConnected(false); wsRef.current = null; };
    }, []);

    useEffect(() => {
        if (enabled) {
            connect();
        } else {
            disconnect();
            setLiveData(new Map());
        }
        return () => disconnect();
    }, [enabled, connect, disconnect]);

    return { liveData, connected };
}
