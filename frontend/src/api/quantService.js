const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const analyzeSymbol = async (symbol) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/quant/analyze?symbol=${encodeURIComponent(symbol)}`);
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to fetch quant analysis');
    }
    return await response.json();
  } catch (error) {
    console.error('Error analyzing symbol:', error);
    throw error;
  }
};
