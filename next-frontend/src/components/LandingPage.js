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
            {/* Ad Preview Video - larger */}
            <video controls poster="https://placehold.co/700x340?text=Ad+Preview+GIF" style={{borderRadius: '20px', boxShadow: '0 2px 24px #18333a55', marginTop: '2rem', width: '100%', maxWidth: 700, height: 340, objectFit: 'cover', background: '#222'}}>
              <source src="http://127.0.0.1:5000/static/generated/replicate-prediction-j9qzxv3hmdrme0cq934sp9sxer_1_2.mp4" type="video/mp4" />
              Your browser does not support the video tag.
            </video>
          </div>
        </div>
        {/* Features 3x2 grid */}
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">🔎</div>
            <div className="feature-title">Company Research & Report</div>
            <div className="feature-desc">We research your company and generate a detailed report on your products, services, and brand voice. Download the report for insights and transparency.</div>
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
            <div className="feature-icon">🌟</div>
            <div className="feature-title">Inspired by the Best</div>
            <div className="feature-desc">Your ad is inspired by the most effective ads in history.</div>
          </div>
          <div className="feature-card">
            <div className="feature-icon">⚡</div>
            <div className="feature-title">Instant Download</div>
            <div className="feature-desc">Download your video and report instantly, no waiting.</div>
          </div>
          <div className="feature-card">
            <div className="feature-icon">💸</div>
            <div className="feature-title">Unbeatable Value</div>
            <div className="feature-desc">
              Creating a professional 15 second ad can cost $1,500 or more.<br />
              With us, you get a cinematic, AI-powered 16-second ad for just <b>$16</b> a fraction of the industry price.
            </div>
          </div>
        </div>
        {/* Main CTA at the bottom */}
        <div className="secondary-cta">
          <button className="cta-secondary" onClick={() => router.push('/chat')}>Generate Ad</button>
        </div>
      </div>
    </div>
  );
}

export default LandingPage; 