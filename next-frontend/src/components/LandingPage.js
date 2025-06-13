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
            <div style={{
              borderRadius: '20px', 
              boxShadow: '0 2px 24px #18333a55', 
              marginTop: '2rem', 
              width: '100%', 
              maxWidth: 700, 
              height: 340, 
              background: 'linear-gradient(135deg, #223c44 0%, #18333a 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              position: 'relative',
              overflow: 'hidden'
            }}>
              <div style={{
                color: '#b6d6e0',
                fontSize: '1.2rem',
                fontWeight: '600',
                textAlign: 'center',
                padding: '2rem'
              }}>
                🎬 AI-Generated Ad Preview<br />
                <span style={{fontSize: '0.9rem', opacity: 0.8}}>
                  Your custom video will appear here
                </span>
              </div>
              <div style={{
                position: 'absolute',
                bottom: '1rem',
                left: '1rem',
                right: '1rem',
                height: '4px',
                background: 'rgba(60, 161, 181, 0.3)',
                borderRadius: '2px'
              }}>
                <div style={{
                  width: '30%',
                  height: '100%',
                  background: '#3ca1b5',
                  borderRadius: '2px'
                }}></div>
              </div>
            </div>
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
          <button className="cta-button" onClick={() => router.push('/chat')}>Generate Ad</button>
        </div>
      </div>
    </div>
  );
}

export default LandingPage; 