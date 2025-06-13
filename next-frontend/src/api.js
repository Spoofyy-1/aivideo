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
    const res = await fetch(`${API_BASE_URL}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(answers)
    });
    if (!res.ok) {
      console.error('API call failed:', res.status, res.statusText);
      throw new Error('Failed to generate ad');
    }
    return await res.json();
}

export async function researchCompany(companyUrl) {
    console.log('Making API call to:', `${API_BASE_URL}/research`);
    const res = await fetch(`${API_BASE_URL}/research`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ company_url: companyUrl })
    });
    if (!res.ok) {
      console.error('API call failed:', res.status, res.statusText);
      throw new Error('Failed to research company');
    }
    return await res.json();
}

export async function testAPI() {
    console.log('Making API call to:', `${API_BASE_URL}/test`);
    const res = await fetch(`${API_BASE_URL}/test`);
    if (!res.ok) {
      console.error('API call failed:', res.status, res.statusText);
      throw new Error('API test failed');
    }
    return await res.text();
} 