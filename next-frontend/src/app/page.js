"use client";

import React from 'react';
import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="homepage">
      {/* Navigation */}
      <nav className="navbar">
        <div className="nav-container">
          <div className="logo-section">
            <div className="company-logo">
              <div className="logo-circle"></div>
              <span>COMPANY</span>
            </div>
          </div>
          
          <div className="nav-links">
            <a href="#home" className="nav-link">HOME</a>
            <a href="#notification" className="nav-link">NOTIFICATION</a>
            <a href="#about" className="nav-link">ABOUT</a>
            <a href="#help" className="nav-link">HELP</a>
            <Link href="/chat" className="nav-link sign-in-btn">SIGN IN</Link>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="main-content">
        <div className="welcome-section">
          <div className="glow-effects">
            <div className="glow-orb glow-1"></div>
            <div className="glow-orb glow-2"></div>
            <div className="glow-orb glow-3"></div>
          </div>
          
          <div className="welcome-content">
            <h1 className="welcome-title">Welcome.</h1>
            <p className="welcome-subtitle">
              Create AI-powered video ads in minutes.<br />
              Upload your content and let our advanced AI bring your vision to life.
            </p>
            <Link href="/chat" className="get-started-btn">
              Get Started
            </Link>
          </div>
        </div>
      </main>

      <style jsx>{`
        .homepage {
          min-height: 100vh;
          background: linear-gradient(135deg, #D789D7 0%, #9C27B0 25%, #673AB7 50%, #3F51B5 75%, #1A237E 100%);
          background-attachment: fixed;
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
          position: relative;
          overflow: hidden;
        }

        .homepage::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: radial-gradient(circle at 30% 50%, rgba(63, 81, 181, 0.3) 0%, transparent 50%),
                      radial-gradient(circle at 70% 30%, rgba(156, 39, 176, 0.2) 0%, transparent 50%),
                      radial-gradient(circle at 50% 80%, rgba(26, 35, 126, 0.4) 0%, transparent 50%);
          opacity: 0.8;
        }

        .homepage::after {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.7);
          z-index: 1;
        }

        /* Navigation */
        .navbar {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          background: rgba(0, 0, 0, 0.3);
          backdrop-filter: blur(20px);
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
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

        .company-logo {
          display: flex;
          align-items: center;
          gap: 0.8rem;
          color: white;
          font-weight: 600;
          font-size: 1.1rem;
        }

        .logo-circle {
          width: 24px;
          height: 24px;
          background: white;
          border-radius: 50%;
        }

        .nav-links {
          display: flex;
          align-items: center;
          gap: 2rem;
        }

        .nav-link {
          color: rgba(255, 255, 255, 0.8);
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

        .sign-in-btn {
          background: white;
          color: #1A237E !important;
          padding: 0.7rem 1.5rem !important;
          border-radius: 25px;
          font-weight: 600;
          box-shadow: 0 4px 15px rgba(255, 255, 255, 0.2);
        }

        .sign-in-btn:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 25px rgba(255, 255, 255, 0.3);
          background: rgba(255, 255, 255, 0.95) !important;
        }

        /* Main Content */
        .main-content {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          position: relative;
          z-index: 2;
          padding-top: 80px;
        }

        .welcome-section {
          position: relative;
          text-align: center;
          color: white;
          max-width: 800px;
          padding: 0 2rem;
        }

        .glow-effects {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          pointer-events: none;
          z-index: -1;
        }

        .glow-orb {
          position: absolute;
          border-radius: 50%;
          filter: blur(80px);
          opacity: 0.6;
          animation: float 8s ease-in-out infinite;
        }

        .glow-1 {
          width: 300px;
          height: 300px;
          background: radial-gradient(circle, #3F51B5 0%, transparent 70%);
          top: -100px;
          left: -100px;
          animation-delay: 0s;
        }

        .glow-2 {
          width: 400px;
          height: 400px;
          background: radial-gradient(circle, #9C27B0 0%, transparent 70%);
          top: 50%;
          right: -150px;
          animation-delay: 3s;
        }

        .glow-3 {
          width: 250px;
          height: 250px;
          background: radial-gradient(circle, #673AB7 0%, transparent 70%);
          bottom: -100px;
          left: 50%;
          transform: translateX(-50%);
          animation-delay: 6s;
        }

        .welcome-content {
          position: relative;
          z-index: 1;
        }

        .welcome-title {
          font-size: 5rem;
          font-weight: 300;
          margin-bottom: 2rem;
          letter-spacing: -2px;
          text-shadow: 0 0 30px rgba(255, 255, 255, 0.5);
        }

        .welcome-subtitle {
          font-size: 1.2rem;
          line-height: 1.6;
          margin-bottom: 3rem;
          opacity: 0.9;
          font-weight: 300;
        }

        .get-started-btn {
          display: inline-block;
          background: linear-gradient(135deg, #3F51B5 0%, #9C27B0 100%);
          color: white;
          padding: 1rem 2.5rem;
          border-radius: 30px;
          font-weight: 600;
          font-size: 1.1rem;
          text-decoration: none;
          transition: all 0.3s ease;
          box-shadow: 0 8px 30px rgba(63, 81, 181, 0.4);
          border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .get-started-btn:hover {
          transform: translateY(-3px);
          box-shadow: 0 15px 40px rgba(63, 81, 181, 0.6);
          background: linear-gradient(135deg, #5C6BC0 0%, #BA68C8 100%);
        }

        /* Animations */
        @keyframes float {
          0%, 100% { 
            transform: translateY(0px) scale(1);
            opacity: 0.6;
          }
          50% { 
            transform: translateY(-20px) scale(1.1);
            opacity: 0.8;
          }
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

          .welcome-title {
            font-size: 3rem;
          }

          .welcome-subtitle {
            font-size: 1rem;
          }

          .glow-orb {
            filter: blur(60px);
          }

          .glow-1 {
            width: 200px;
            height: 200px;
          }

          .glow-2 {
            width: 250px;
            height: 250px;
          }

          .glow-3 {
            width: 180px;
            height: 180px;
          }
        }
      `}</style>
    </div>
  );
} 