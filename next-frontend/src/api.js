// API base URL - automatically detects environment
const getApiBaseUrl = () => {
  // If we're in the browser and on localhost, use local backend
  if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
    return 'http://localhost:5000';
  }
  // If we have a Railway URL set in environment, use it
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  // Production Railway URL
  return 'https://aivideo-production.up.railway.app';
};

const API_BASE_URL = getApiBaseUrl();

export async function generateAd(answers) {
    const res = await fetch(`${API_BASE_URL}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(answers)
    });
    if (!res.ok) throw new Error('Failed to generate ad');
    return await res.json();
}

export async function researchCompany(companyUrl) {
    const res = await fetch(`${API_BASE_URL}/research`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ company_url: companyUrl })
    });
    if (!res.ok) throw new Error('Failed to research company');
    return await res.json();
}

export async function testAPI() {
    const res = await fetch(`${API_BASE_URL}/test`);
    if (!res.ok) throw new Error('API test failed');
    return await res.text();
} 