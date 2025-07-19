"use client";

import React from 'react';
import Link from 'next/link';

export default function LandingPage() {
  return (
    <div className="landing-page">
      {/* Navigation */}
      <nav className="navbar">
        <div className="nav-container">
          <div className="logo-section">
            <div className="logo">
              <div className="genie-icon">
                <div className="genie-head">
                  <div className="star">⭐</div>
                  <div className="face">
                    <div className="eyes">
                      <div className="eye"></div>
                      <div className="eye"></div>
                    </div>
                    <div className="mustache"></div>
                    <div className="smile"></div>
                  </div>
                </div>
                <div className="circuits">
                  <div className="circuit-line"></div>
                  <div className="circuit-line"></div>
                  <div className="circuit-line"></div>
                </div>
              </div>
              <span className="logo-text">adgenie</span>
            </div>
          </div>
          
          <div className="nav-links">
            <a href="#home" className="nav-link">HOME</a>
            <a href="#features" className="nav-link">FEATURES</a>
            <a href="#about" className="nav-link">ABOUT</a>
            <a href="#pricing" className="nav-link">PRICING</a>
            <Link href="/create" className="nav-link cta-btn">CREATE AD</Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="hero" id="home">
        <div className="hero-container">
          <div className="hero-content">
            <h1 className="hero-title">
              Welcome to the Future of 
              <span className="gradient-text"> AI Video Advertising</span>
            </h1>
            <p className="hero-subtitle">
              Create stunning, professional video ads in seconds with our advanced VEO-3 AI technology. 
              Upload your visuals, answer a few questions, and watch magic happen.
            </p>
            <div className="hero-buttons">
              <Link href="/create" className="primary-btn">
                <span>Start Creating</span>
                <div className="btn-glow"></div>
              </Link>
              <button className="secondary-btn">Watch Demo</button>
            </div>
            
            <div className="hero-stats">
              <div className="stat">
                <div className="stat-number">10K+</div>
                <div className="stat-label">Ads Created</div>
              </div>
              <div className="stat">
                <div className="stat-number">16s</div>
                <div className="stat-label">Perfect Length</div>
              </div>
              <div className="stat">
                <div className="stat-number">VEO-3</div>
                <div className="stat-label">AI Powered</div>
              </div>
            </div>
          </div>
          
          <div className="hero-visual">
            <div className="floating-card">
              <div className="card-header">AdGenie Studio</div>
              <div className="card-content">
                <div className="chat-section">
                  <div className="chat-bubble bot">
                    Hi! I'm your AI Ad Generator
                  </div>
                  <div className="chat-bubble user">
                    Create an ad for my startup
                  </div>
                </div>
                <div className="upload-section">
                  <div className="upload-icon">📁</div>
                  <span>Drop images here</span>
                </div>
              </div>
            </div>
            
            <div className="floating-elements">
              <div className="floating-icon icon-1">🎬</div>
              <div className="floating-icon icon-2">✨</div>
              <div className="floating-icon icon-3">🚀</div>
              <div className="floating-icon icon-4">💫</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="features" id="features">
        <div className="container">
          <h2 className="section-title">Powerful Features</h2>
          <div className="features-grid">
            <div className="feature-card">
              <div className="feature-icon">🎬</div>
              <h3>VEO-3 AI Technology</h3>
              <p>Cutting-edge Google VEO-3 with frame-to-video continuation for seamless 16-second ads</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">📸</div>
              <h3>Smart Image Integration</h3>
              <p>Upload any images and our AI intelligently integrates them with perfect context</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">⚡</div>
              <h3>Lightning Fast</h3>
              <p>Generate professional video ads in minutes, not hours or days</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🎯</div>
              <h3>Perfect Targeting</h3>
              <p>AI-powered audience analysis and trend integration for maximum impact</p>
            </div>
          </div>
        </div>
      </section>

      <style jsx>{`
        .landing-page {
          min-height: 100vh;
          background: linear-gradient(135deg, #1e40af 0%, #3b82f6 25%, #60a5fa  50%, #93c5fd  75%, #dbeafe 100%);
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
          position: relative;
          overflow-x: hidden;
        }

        .landing-page::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: url('data:image/svg+xml,<svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><g fill="none" fill-rule="evenodd"><g fill="%23ffffff" fill-opacity="0.05"><circle cx="50" cy="50" r="2"/></g></svg>');
          opacity: 0.3;
        }

        /* Navigation */
        .navbar {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          background: rgba(255, 255, 255, 0.1);
          backdrop-filter: blur(20px);
          border-bottom: 1px solid rgba(255, 255, 255, 0.2);
          z-index: 1000;
          padding: 1rem 0;
        }

        .nav-container {
          max-width: 1200px;
          margin: 0 auto;
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0 2rem;
        }

        .logo-section {
          display: flex;
          align-items: center;
        }

        .logo {
          display: flex;
          align-items: center;
          gap: 0.8rem;
        }

        .genie-icon {
          position: relative;
          width: 40px;
          height: 40px;
        }

        .genie-head {
          width: 32px;
          height: 32px;
          background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
          border-radius: 50%;
          position: relative;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .star {
          position: absolute;
          top: -5px;
          right: -5px;
          font-size: 12px;
        }

        .face {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 2px;
        }

        .eyes {
          display: flex;
          gap: 6px;
        }

        .eye {
          width: 4px;
          height: 4px;
          background: #1e293b;
          border-radius: 50%;
        }

        .mustache {
          width: 8px;
          height: 2px;
          background: #1e293b;
          border-radius: 1px;
        }

        .smile {
          width: 6px;
          height: 3px;
          border: 1px solid #1e293b;
          border-top: none;
          border-radius: 0 0 6px 6px;
        }

        .circuits {
          position: absolute;
          right: -8px;
          top: 8px;
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .circuit-line {
          width: 12px;
          height: 2px;
          background: #60a5fa;
          border-radius: 1px;
          position: relative;
        }

        .circuit-line::after {
          content: '';
          position: absolute;
          right: -4px;
          top: -1px;
          width: 4px;
          height: 4px;
          background: #60a5fa;
          border-radius: 50%;
        }

        .logo-text {
          font-size: 1.5rem;
          font-weight: 800;
          color: white;
          text-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }

        .nav-links {
          display: flex;
          align-items: center;
          gap: 2rem;
        }

        .nav-link {
          color: rgba(255, 255, 255, 0.9);
          text-decoration: none;
          font-weight: 500;
          font-size: 0.9rem;
          transition: all 0.3s ease;
          padding: 0.5rem 1rem;
          border-radius: 8px;
        }

        .nav-link:hover {
          color: white;
          background: rgba(255, 255, 255, 0.1);
        }

        .cta-btn {
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          color: white !important;
          padding: 0.7rem 1.5rem !important;
          border-radius: 10px;
          font-weight: 600;
          box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
        }

        .cta-btn:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 25px rgba(16, 185, 129, 0.4);
          background: linear-gradient(135deg, #059669 0%, #047857 100%) !important;
        }

        /* Hero Section */
        .hero {
          min-height: 100vh;
          display: flex;
          align-items: center;
          position: relative;
          z-index: 1;
          padding-top: 80px;
        }

        .hero-container {
          max-width: 1200px;
          margin: 0 auto;
          padding: 0 2rem;
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 4rem;
          align-items: center;
        }

        .hero-content {
          color: white;
        }

        .hero-title {
          font-size: 3.5rem;
          font-weight: 800;
          line-height: 1.1;
          margin-bottom: 1.5rem;
          text-shadow: 0 2px 20px rgba(0,0,0,0.2);
        }

        .gradient-text {
          background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }

        .hero-subtitle {
          font-size: 1.2rem;
          line-height: 1.6;
          margin-bottom: 2rem;
          opacity: 0.9;
          font-weight: 400;
        }

        .hero-buttons {
          display: flex;
          gap: 1rem;
          margin-bottom: 3rem;
        }

        .primary-btn {
          position: relative;
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          color: white;
          padding: 1rem 2rem;
          border-radius: 12px;
          font-weight: 700;
          font-size: 1.1rem;
          text-decoration: none;
          display: inline-flex;
          align-items: center;
          transition: all 0.3s ease;
          overflow: hidden;
          box-shadow: 0 8px 30px rgba(16, 185, 129, 0.3);
        }

        .primary-btn:hover {
          transform: translateY(-3px);
          box-shadow: 0 15px 40px rgba(16, 185, 129, 0.4);
        }

        .btn-glow {
          position: absolute;
          top: 0;
          left: -100%;
          width: 100%;
          height: 100%;
          background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
          transition: left 0.5s ease;
        }

        .primary-btn:hover .btn-glow {
          left: 100%;
        }

        .secondary-btn {
          background: rgba(255, 255, 255, 0.1);
          color: white;
          border: 2px solid rgba(255, 255, 255, 0.3);
          padding: 1rem 2rem;
          border-radius: 12px;
          font-weight: 600;
          font-size: 1.1rem;
          cursor: pointer;
          transition: all 0.3s ease;
          backdrop-filter: blur(10px);
        }

        .secondary-btn:hover {
          background: rgba(255, 255, 255, 0.2);
          transform: translateY(-2px);
        }

        .hero-stats {
          display: flex;
          gap: 2rem;
        }

        .stat {
          text-align: center;
        }

        .stat-number {
          font-size: 2rem;
          font-weight: 800;
          color: #fbbf24;
          text-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }

        .stat-label {
          font-size: 0.9rem;
          opacity: 0.8;
          font-weight: 500;
        }

        /* Hero Visual */
        .hero-visual {
          position: relative;
          display: flex;
          justify-content: center;
          align-items: center;
        }

        .floating-card {
          background: rgba(255, 255, 255, 0.95);
          border-radius: 20px;
          padding: 1.5rem;
          box-shadow: 0 20px 60px rgba(0,0,0,0.2);
          backdrop-filter: blur(20px);
          border: 1px solid rgba(255, 255, 255, 0.3);
          width: 300px;
          animation: float 6s ease-in-out infinite;
        }

        .card-header {
          font-weight: 700;
          color: #1e293b;
          margin-bottom: 1rem;
          text-align: center;
          font-size: 1.1rem;
        }

        .chat-section {
          margin-bottom: 1rem;
        }

        .chat-bubble {
          padding: 0.8rem;
          border-radius: 12px;
          margin-bottom: 0.5rem;
          font-size: 0.9rem;
          font-weight: 500;
        }

        .chat-bubble.bot {
          background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
          color: white;
          margin-right: 20%;
        }

        .chat-bubble.user {
          background: #f1f5f9;
          color: #1e293b;
          margin-left: 20%;
        }

        .upload-section {
          background: #f8fafc;
          border: 2px dashed #cbd5e1;
          border-radius: 12px;
          padding: 1rem;
          text-align: center;
          color: #64748b;
        }

        .upload-icon {
          font-size: 1.5rem;
          margin-bottom: 0.5rem;
        }

        .floating-elements {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          pointer-events: none;
        }

        .floating-icon {
          position: absolute;
          font-size: 2rem;
          animation: floatAround 8s ease-in-out infinite;
        }

        .icon-1 {
          top: 10%;
          left: 10%;
          animation-delay: 0s;
        }

        .icon-2 {
          top: 20%;
          right: 10%;
          animation-delay: 2s;
        }

        .icon-3 {
          bottom: 30%;
          left: 5%;
          animation-delay: 4s;
        }

        .icon-4 {
          bottom: 10%;
          right: 20%;
          animation-delay: 6s;
        }

        /* Features Section */
        .features {
          padding: 5rem 0;
          background: rgba(255, 255, 255, 0.1);
          backdrop-filter: blur(20px);
        }

        .container {
          max-width: 1200px;
          margin: 0 auto;
          padding: 0 2rem;
        }

        .section-title {
          font-size: 2.5rem;
          font-weight: 800;
          text-align: center;
          color: white;
          margin-bottom: 3rem;
          text-shadow: 0 2px 20px rgba(0,0,0,0.2);
        }

        .features-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 2rem;
        }

        .feature-card {
          background: rgba(255, 255, 255, 0.9);
          padding: 2rem;
          border-radius: 16px;
          text-align: center;
          box-shadow: 0 10px 40px rgba(0,0,0,0.1);
          backdrop-filter: blur(20px);
          border: 1px solid rgba(255, 255, 255, 0.3);
          transition: all 0.3s ease;
        }

        .feature-card:hover {
          transform: translateY(-5px);
          box-shadow: 0 20px 60px rgba(0,0,0,0.15);
        }

        .feature-icon {
          font-size: 3rem;
          margin-bottom: 1rem;
        }

        .feature-card h3 {
          font-size: 1.3rem;
          font-weight: 700;
          color: #1e293b;
          margin-bottom: 1rem;
        }

        .feature-card p {
          color: #64748b;
          line-height: 1.6;
          font-weight: 500;
        }

        /* Animations */
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-20px); }
        }

        @keyframes floatAround {
          0%, 100% { transform: translate(0, 0) rotate(0deg); }
          25% { transform: translate(10px, -10px) rotate(90deg); }
          50% { transform: translate(-5px, -20px) rotate(180deg); }
          75% { transform: translate(-15px, -5px) rotate(270deg); }
        }

        /* Mobile Responsive */
        @media (max-width: 768px) {
          .nav-container {
            padding: 0 1rem;
          }

          .nav-links {
            gap: 1rem;
          }

          .nav-link {
            font-size: 0.8rem;
            padding: 0.4rem 0.8rem;
          }

          .hero-container {
            grid-template-columns: 1fr;
            gap: 2rem;
            text-align: center;
          }

          .hero-title {
            font-size: 2.5rem;
          }

          .hero-buttons {
            justify-content: center;
          }

          .floating-card {
            width: 250px;
          }

          .features-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
} 