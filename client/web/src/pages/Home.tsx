import { useNavigate } from 'react-router-dom';

export function Home() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-white flex items-center justify-center px-6">
      <div className="max-w-4xl w-full text-center">
        <h1 className="text-6xl font-bold text-gray-900 mb-6 tracking-tight">
          x402 Payment Demo
        </h1>
        <p className="text-xl text-gray-500 mb-12 max-w-2xl mx-auto">
          Experience decentralized pay-per-request on TRON
        </p>
        
        <button
          onClick={() => navigate('/protected')}
          className="btn-primary text-lg inline-flex items-center gap-3"
        >
          Try it
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
          </svg>
        </button>
      </div>
    </div>
  );
}
