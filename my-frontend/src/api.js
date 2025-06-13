export async function generateAd(answers) {
    const res = await fetch('http://127.0.0.1:5000/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(answers)
    });
    if (!res.ok) throw new Error('Failed to generate ad');
    return await res.json();
  }