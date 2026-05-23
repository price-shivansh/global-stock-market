import apiClient from './api';

export const fetchNews = async () => {
  try {
    const response = await apiClient.get('/api/mobile/news');
    return response.data;
  } catch (error) {
    console.error('Error fetching live news:', {
      message: error.message,
      code: error.code,
      status: error.response?.status,
      data: error.response?.data,
    });
    throw error;
  }
};

export const fetchHistoricalNews = async (date) => {
  try {
    const response = await apiClient.get(`/api/mobile/news/history?date=${date}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching historical news for ${date}:`, {
      message: error.message,
      code: error.code,
      status: error.response?.status,
      data: error.response?.data,
    });
    throw error;
  }
};

export const fetchAvailableDates = async () => {
  try {
    const response = await apiClient.get('/api/mobile/news/history/dates');
    return response.data;
  } catch (error) {
    console.error('Error fetching available dates:', {
      message: error.message,
      code: error.code,
      status: error.response?.status,
      data: error.response?.data,
    });
    throw error;
  }
};

export const fetchMarketOverview = async () => {
  try {
    const response = await apiClient.get('/api/mobile/market-overview');
    return response.data;
  } catch (error) {
    console.error('Error fetching market overview:', {
      message: error.message,
      code: error.code,
      status: error.response?.status,
      data: error.response?.data,
    });
    throw error;
  }
};

export const fetchSentimentSummary = async () => {
  try {
    const response = await apiClient.get('/api/mobile/sentiment');
    return response.data;
  } catch (error) {
    console.error('Error fetching sentiment summary:', {
      message: error.message,
      code: error.code,
      status: error.response?.status,
      data: error.response?.data,
    });
    throw error;
  }
};