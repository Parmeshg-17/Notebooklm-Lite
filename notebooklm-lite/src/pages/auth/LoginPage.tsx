import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { BookOpen, Sparkles, Shield, Cpu, ArrowRight } from 'lucide-react';
import { useAuthStore } from '../../store';
import Button from '../../components/common/Button';

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isAuthenticated } = useAuthStore();

  const from = (location.state as any)?.from?.pathname || '/dashboard';

  useEffect(() => {
    if (isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, from]);

  const [email, setEmail] = useState('elena.vance@blackmesa.gov');
  const [password, setPassword] = useState('Password123!');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!email || !password) {
      setError('Please fill in both email and password.');
      return;
    }

    try {
      setLoading(true);
      await login(email, password);
      navigate(from, { replace: true });
    } catch {
      setError('Invalid credentials. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex w-full" style={{ backgroundColor: 'var(--color-surface)' }}>
      {/* ── Left Feature Panel (Desktop) ── */}
      <div
        className="hidden lg:flex lg:w-1/2 flex-col justify-between p-12 xl:p-16 relative overflow-hidden flex-shrink-0"
        style={{
          backgroundColor: 'var(--color-primary-container)',
          color: 'var(--color-on-primary-container)',
        }}
      >
        {/* Ambient background glow */}
        <div
          className="absolute -right-24 -bottom-24 w-[32rem] h-[32rem] rounded-full blur-3xl opacity-30 pointer-events-none"
          style={{ backgroundColor: 'var(--color-primary-fixed)' }}
        />

        {/* Brand Header */}
        <div className="flex items-center gap-3 relative z-10">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center shadow-md flex-shrink-0"
            style={{ backgroundColor: 'var(--color-primary)', color: 'white' }}
          >
            <BookOpen size={22} />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-headline-md font-bold tracking-tight text-white">
              NotebookLM Lite
            </span>
            <span className="text-code-sm px-2 py-0.5 rounded-full bg-white/20 text-white font-medium">
              Enterprise v1.4
            </span>
          </div>
        </div>

        {/* Value Proposition Highlights */}
        <div className="max-w-lg my-auto py-10 space-y-6 relative z-10">
          <h1 className="text-display-lg font-bold text-white leading-tight">
            Your documents.<br />Your knowledge.<br />One intelligent workspace.
          </h1>
          <p className="text-body-lg text-white/85 leading-relaxed">
            Enterprise-grade RAG synthesis powered by deterministic document grounding, page-level citation tracking, and telemetry observability.
          </p>

          <div className="space-y-4 pt-4">
            <div className="flex items-start gap-3.5">
              <div className="p-2 rounded-lg bg-white/10 text-white mt-0.5 flex-shrink-0">
                <Sparkles size={18} />
              </div>
              <div>
                <h3 className="font-semibold text-white text-body-lg">Strict Grounding & Precision Citations</h3>
                <p className="text-body-sm text-white/75 mt-0.5">
                  Every AI response links directly to verified pages, paragraphs, and tables in your uploaded corpus.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3.5">
              <div className="p-2 rounded-lg bg-white/10 text-white mt-0.5 flex-shrink-0">
                <Cpu size={18} />
              </div>
              <div>
                <h3 className="font-semibold text-white text-body-lg">Hybrid RAG & Kernel Acceleration</h3>
                <p className="text-body-sm text-white/75 mt-0.5">
                  Dense 768d vector embeddings paired with ColBERT re-ranking for ultra-low latency inference.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3.5">
              <div className="p-2 rounded-lg bg-white/10 text-white mt-0.5 flex-shrink-0">
                <Shield size={18} />
              </div>
              <div>
                <h3 className="font-semibold text-white text-body-lg">Enterprise Observability & Security</h3>
                <p className="text-body-sm text-white/75 mt-0.5">
                  Full token accounting, P95 latency monitoring, audit trails, and strict organizational isolation.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer info */}
        <div className="text-code-sm text-white/60 relative z-10">
          Google Stitch UI Architecture · Enterprise Preview Edition
        </div>
      </div>

      {/* ── Right Form Panel ── */}
      <div className="flex-1 min-w-0 w-full flex flex-col justify-center items-center p-6 sm:p-12 lg:p-16 min-h-screen">
        <div className="w-full max-w-md space-y-7">
          {/* Mobile Header (< lg) */}
          <div className="flex lg:hidden items-center gap-2.5 mb-2">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center shadow-xs flex-shrink-0"
              style={{ backgroundColor: 'var(--color-primary)', color: 'white' }}
            >
              <BookOpen size={20} />
            </div>
            <div>
              <span className="text-headline-sm font-bold tracking-tight" style={{ color: 'var(--color-on-surface)' }}>
                NotebookLM Lite
              </span>
              <span className="ml-2 text-code-sm px-1.5 py-0.5 rounded-full bg-[--color-secondary-container] text-[--color-on-secondary-container] font-medium">
                v1.4 Ent
              </span>
            </div>
          </div>

          <div>
            <h2 className="text-display-lg font-bold tracking-tight" style={{ color: 'var(--color-on-surface)' }}>
              Welcome back
            </h2>
            <p className="text-body-md mt-1.5" style={{ color: 'var(--color-on-surface-variant)' }}>
              Sign in to your enterprise research workspace
            </p>
          </div>

          {error && (
            <div
              className="p-3.5 rounded-xl text-body-sm font-medium border"
              style={{
                backgroundColor: 'var(--color-error-container)',
                color: 'var(--color-on-error-container)',
                borderColor: 'var(--color-error)',
              }}
            >
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                className="block text-label-md font-semibold mb-1.5"
                style={{ color: 'var(--color-on-surface)' }}
              >
                Work Email
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@institution.org"
                className="w-full px-3.5 py-2.5 rounded-xl text-body-md outline-none transition-all"
                style={{
                  backgroundColor: 'var(--color-surface-container-low)',
                  border: '1px solid var(--color-outline-variant)',
                  color: 'var(--color-on-surface)',
                }}
                onFocus={(e) => {
                  e.currentTarget.style.borderColor = 'var(--color-primary)';
                  e.currentTarget.style.boxShadow = '0 0 0 3px color-mix(in srgb, var(--color-primary) 15%, transparent)';
                }}
                onBlur={(e) => {
                  e.currentTarget.style.borderColor = 'var(--color-outline-variant)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label
                  className="text-label-md font-semibold"
                  style={{ color: 'var(--color-on-surface)' }}
                >
                  Password
                </label>
                <a
                  href="#forgot"
                  onClick={(e) => {
                    e.preventDefault();
                    alert('Password reset instructions sent to your registered work email.');
                  }}
                  className="text-label-sm font-medium hover:underline"
                  style={{ color: 'var(--color-primary)' }}
                >
                  Forgot password?
                </a>
              </div>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full px-3.5 py-2.5 rounded-xl text-body-md outline-none transition-all"
                style={{
                  backgroundColor: 'var(--color-surface-container-low)',
                  border: '1px solid var(--color-outline-variant)',
                  color: 'var(--color-on-surface)',
                }}
                onFocus={(e) => {
                  e.currentTarget.style.borderColor = 'var(--color-primary)';
                  e.currentTarget.style.boxShadow = '0 0 0 3px color-mix(in srgb, var(--color-primary) 15%, transparent)';
                }}
                onBlur={(e) => {
                  e.currentTarget.style.borderColor = 'var(--color-outline-variant)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              />
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              loading={loading}
              className="w-full mt-3 py-2.5 shadow-sm"
              icon={ArrowRight}
              iconPosition="right"
            >
              Sign In to Workspace
            </Button>
          </form>

          {/* Demo account hint */}
          <div
            className="p-3.5 rounded-xl text-code-sm space-y-1"
            style={{
              backgroundColor: 'var(--color-surface-container-low)',
              border: '1px solid color-mix(in srgb, var(--color-outline-variant) 40%, transparent)',
              color: 'var(--color-on-surface-variant)',
            }}
          >
            <div className="flex items-center justify-between">
              <span className="font-semibold" style={{ color: 'var(--color-on-surface)' }}>
                Enterprise Demo Account
              </span>
              <span
                className="px-1.5 py-0.2 rounded text-[10px] font-semibold uppercase tracking-wider"
                style={{ backgroundColor: 'var(--color-tertiary-fixed)', color: 'var(--color-on-tertiary-fixed-variant)' }}
              >
                Preloaded
              </span>
            </div>
            <p className="text-body-sm font-medium" style={{ color: 'var(--color-on-surface)' }}>
              Dr. Elena Vance (Lead Research Scientist)
            </p>
            <p className="text-[11px] opacity-75">
              Click &ldquo;Sign In to Workspace&rdquo; to test with full enterprise permissions and mock data.
            </p>
          </div>

          <div className="text-center text-body-sm" style={{ color: 'var(--color-on-surface-variant)' }}>
            Need an enterprise license?{' '}
            <Link
              to="/auth/register"
              className="font-semibold hover:underline"
              style={{ color: 'var(--color-primary)' }}
            >
              Create an account
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
