/**
 * Mock Analytics Wrapper
 * 
 * Replace the implementations below with real analytics providers 
 * (like Vercel Analytics or GA4) when ready for production.
 */

export const trackEvent = (eventName: string, data?: Record<string, any>) => {
  // Mock implementation for development
  console.log(`[Analytics Mock] Event: "${eventName}"`, data || {});

  // Example GA4 swap-in:
  // if (typeof window.gtag === 'function') {
  //   window.gtag('event', eventName, data);
  // }
  
  // Example Vercel Analytics swap-in:
  // if (typeof window.va === 'function') {
  //   window.va('event', { name: eventName, data });
  // }
};

export const trackPageView = (pageName: string) => {
  console.log(`[Analytics Mock] Page View: "${pageName}"`);
};
