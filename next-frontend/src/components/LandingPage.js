"use client";

import React from 'react';
import { useRouter } from 'next/navigation';

function LandingPage() {
  const router = useRouter();

  return (
    <div className="landing-outer">
      <div className="container landing-container">
        {/* Hero Section */}
        <div className="hero">
          <h1 className="hero-title">Create AI-Powered Ad Videos in Minutes</h1>
          <div className="hero-visual">
            {/* Video Player - using Railway backend URL */}
            <video 
              controls 
              poster="https://placehold.co/700x340/2a3f47/b6d6e0?text=AI+Generated+Ad+Preview"
              style={{
                borderRadius: '20px', 
                boxShadow: '0 2px 24px #18333a55', 
                marginTop: '2rem', 
                width: '100%', 
                maxWidth: 700, 
                height: 340, 
                objectFit: 'cover',
                background: '#2a3f47'
              }}
            >
              <source src="https://aivideo-production.up.railway.app/static/generated/replicate-prediction-j9qzxv3hmdrme0cq934sp9sxer_1_2.mp4" type="video/mp4" />
              Your browser does not support the video tag.
            </video>
          </div>
        </div>
        
        {/* Features 3x2 grid - uniform sizing */}
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">🔎</div>
            <div className="feature-title">Company Research & Report</div>
            <div className="feature-desc">We research your company and generate a detailed report on your products, services, and brand voice.</div>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📝</div>
            <div className="feature-title">Scripted by GPT-4 & Gemini</div>
            <div className="feature-desc">Get creative, on-brand scripts powered by the latest AI models for each ad.</div>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🎬</div>
            <div className="feature-title">Video Generated with Veo-3</div>
            <div className="feature-desc">Your ad video is created using Google's Veo-3 for cinematic, story-driven visuals.</div>
          </div>
          <div className="feature-card">
            <div className="feature-icon">⭐</div>
            <div className="feature-title">Inspired by the Best</div>
            <div className="feature-desc">Your ad is inspired by the most effective ads in history for maximum impact.</div>
          </div>
          <div className="feature-card">
            <div className="feature-icon">⚡</div>
            <div className="feature-title">Instant Download</div>
            <div className="feature-desc">Download your video and report instantly, no waiting required.</div>
          </div>
          <div className="feature-card">
            <div className="feature-icon">💸</div>
            <div className="feature-title">Unbeatable Value</div>
            <div className="feature-desc">Get a cinematic, AI-powered 16-second ad for just <strong>$16</strong> - a fraction of the industry price.</div>
          </div>
        </div>
        
        {/* Generate Ad Button */}
        <div className="cta-section">
          <button className="generate-ad-btn" onClick={() => router.push('/chat')}>
            Generate Ad
          </button>
        </div>
      </div>
    </div>
  );
}

export default LandingPage; 