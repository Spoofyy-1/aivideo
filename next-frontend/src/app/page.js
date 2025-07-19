"use client";

import React from 'react';
import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="homepage">
      {/* Main Content */}
      <main className="main-content">
        <div className="hero-section">
          <h1 className="hero-title">Create AI-Powered Ad Videos in Minutes</h1>
          <p className="hero-subtitle">
            Find out what's working and what's not to get more powerful video ads.<br />
            Use our VEO-3 generator who can analyze millions of data.
          </p>
          
          <div className="hero-buttons">
            <button onClick={() => window.location.href = '/chat'} className="primary-btn">Get started</button>
          </div>
          
          <p className="hero-note">
            Trusted by businesses  •  30 days free trial
          </p>
        </div>
      </main>

      <style jsx>{`
        .homepage {
          min-height: 100vh;
          background: linear-gradient(135deg, #D789D7 0%, #9C27B0 25%, #673AB7 50%, #3F51B5 75%, #1A237E 100%);
          background-image: url('/background-pipes-ducks.jpg');
          background-size: 80%;
          background-position: center;
          background-attachment: fixed;
          background-repeat: no-repeat;
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
          color: white;
          position: relative;
        }

        .homepage::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: linear-gradient(135deg, rgba(215, 137, 215, 0.3) 0%, rgba(156, 39, 176, 0.4) 25%, rgba(103, 58, 183, 0.5) 50%, rgba(63, 81, 181, 0.4) 75%, rgba(26, 35, 126, 0.6) 100%);
          z-index: 1;
        }

        .main-content {
          position: relative;
          z-index: 2;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 100vh;
        }

        .hero-section {
          text-align: center;
          max-width: 800px;
          padding: 0 2rem;
        }

        .hero-title {
          font-size: 3.5rem;
          font-weight: 700;
          margin-bottom: 1.5rem;
          line-height: 1.1;
          color: white;
          text-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }

        .hero-subtitle {
          font-size: 1.2rem;
          line-height: 1.6;
          margin-bottom: 3rem;
          opacity: 0.9;
          font-weight: 400;
          text-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
        }

        .hero-buttons {
          display: flex;
          justify-content: center;
          align-items: center;
          margin-bottom: 2rem;
        }

        .primary-btn {
          background: linear-gradient(135deg, #3F51B5 0%, #9C27B0 100%);
          color: white;
          padding: 1.5rem 3rem;
          border-radius: 12px;
          font-weight: 700;
          font-size: 1.2rem;
          border: none;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          transition: all 0.3s ease;
          box-shadow: 0 8px 25px rgba(63, 81, 181, 0.3);
          text-transform: uppercase;
          letter-spacing: 1px;
        }

        .primary-btn:hover {
          transform: translateY(-3px);
          box-shadow: 0 12px 35px rgba(63, 81, 181, 0.4);
          background: linear-gradient(135deg, #4FC3F7 0%, #AB47BC 100%);
        }

        .hero-note {
          font-size: 0.9rem;
          opacity: 0.7;
          margin: 0;
          text-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }

        /* Mobile Responsive */
        @media (max-width: 768px) {
          .hero-title {
            font-size: 2.5rem;
          }

          .homepage {
            background-size: 100%;
          }
        }
      `}</style>
    </div>
  );
} 