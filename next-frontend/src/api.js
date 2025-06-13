// API base URL - automatically detects environment
const getApiBaseUrl = () => {
  // If we're in the browser and on localhost, use local backend
  if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
    return 'http://127.0.0.1:5001';
  }
  // If we have a Railway URL set in environment, use it
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  // Default fallback (you'll need to replace this with your actual Railway URL)
  return 'https://your-railway-app.railway.app';
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