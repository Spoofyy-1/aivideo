// API base URL - automatically detects environment
const getApiBaseUrl = () => {
  // Debug logging
  console.log('Detecting API URL...');
  console.log('window exists:', typeof window !== 'undefined');
  console.log('hostname:', typeof window !== 'undefined' ? window.location.hostname : 'server-side');
  console.log('NEXT_PUBLIC_API_URL:', process.env.NEXT_PUBLIC_API_URL);
  
  // If we have a Railway URL set in environment, use it first
  if (process.env.NEXT_PUBLIC_API_URL) {
    console.log('Using environment API URL:', process.env.NEXT_PUBLIC_API_URL);
    return process.env.NEXT_PUBLIC_API_URL;
  }
  
  // Only use localhost if we're actually on localhost (not Vercel)
  if (typeof window !== 'undefined' && (
    window.location.hostname === 'localhost' || 
    window.location.hostname === '127.0.0.1'
  )) {
    console.log('Using local backend');
    return 'http://localhost:5000';
  }
  
  // For all other cases (including Vercel), use production Railway URL
  console.log('Using production Railway URL');
  return 'https://aivideo-production.up.railway.app';
};

const API_BASE_URL = getApiBaseUrl();
console.log('Final API_BASE_URL:', API_BASE_URL);

export async function generateAd(answers) {
    console.log('Making API call to:', `${API_BASE_URL}/generate`);
    console.log('Request payload:', answers);
    
    try {
      const res = await fetch(`${API_BASE_URL}/generate`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify(answers)
      });
      
      console.log('Response status:', res.status);
      console.log('Response headers:', res.headers);
      
      if (!res.ok) {
        const errorText = await res.text();
        console.error('API call failed:', res.status, res.statusText, errorText);
        throw new Error(`Failed to generate ad: ${res.status} ${res.statusText}`);
      }
      
      const data = await res.json();
      console.log('API response:', data);
      return data;
    } catch (error) {
      console.error('Generate ad error:', error);
      throw error;
    }
}

export async function researchCompany(companyUrl) {
    console.log('Making API call to:', `${API_BASE_URL}/research`);
    console.log('Company URL:', companyUrl);
    
    try {
      const res = await fetch(`${API_BASE_URL}/research`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ company_url: companyUrl })
      });
      
      console.log('Research response status:', res.status);
      
      if (!res.ok) {
        const errorText = await res.text();
        console.error('Research API call failed:', res.status, res.statusText, errorText);
        throw new Error(`Failed to research company: ${res.status} ${res.statusText}`);
      }
      
      const data = await res.json();
      console.log('Research API response:', data);
      return data;
    } catch (error) {
      console.error('Research company error:', error);
      throw error;
    }
}

export async function testAPI() {
    console.log('Making API call to:', `${API_BASE_URL}/test`);
    
    try {
      const res = await fetch(`${API_BASE_URL}/test`, {
        method: 'GET',
        headers: { 
          'Accept': 'text/plain'
        }
      });
      
      console.log('Test response status:', res.status);
      
      if (!res.ok) {
        const errorText = await res.text();
        console.error('Test API call failed:', res.status, res.statusText, errorText);
        throw new Error(`API test failed: ${res.status} ${res.statusText}`);
      }
      
      const data = await res.text();
      console.log('Test API response:', data);
      return data;
    } catch (error) {
      console.error('Test API error:', error);
      throw error;
    }
} 