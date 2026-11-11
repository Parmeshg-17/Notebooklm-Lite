import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { BookOpen, Sparkles, Shield, Cpu, ArrowRight } from 'lucide-react';
import { useAuthStore } from '../../store';
import Button from '../../components/common/Button';

export default function RegisterPage() {
  const navigate = useNavigate();
  const { login } = useAuthStore();

  const [name, setName] = useState('Dr. Elena Vance');
  const [email, setEmail] = useState('e.vance@research.ai');
  const [password, setPassword] = useState('password123');
  const [confirmPassword, setConfirmPassword] = useState('password123');
  const [agreeTerms, setAgreeTerms] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!name || !email || !password || !confirmPassword) {
      setError('Please fill in all fields.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    if (!agreeTerms) {
      setError('You must accept the terms of service.');
      return;
    }

    try {
      setLoading(true);
      await login(email, password);
      navigate('/dashboard');
    } catch {
      setError('Registration failed. Please try again.');
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
        <div
          className="absolute -right-24 -bottom-24 w-[32rem] h-[32rem] rounded-full blur-3xl opacity-30 pointer-events-none"
          style={{ backgroundColor: 'var(--color-primary-fixed)' }}
        />

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

        <div className="max-w-lg my-auto py-10 space-y-6 relative z-10">
          <h1 className="text-display-lg font-bold text-white leading-tight">
            Deploy intelligence across your entire enterprise literature.
          </h1>
          <p className="text-body-lg text-white/85 leading-relaxed">
            Create research workspaces, ground responses in mission-critical papers, and cross-reference citations effortlessly.
          </p>

          <div className="space-y-4 pt-4">
            <div className="flex items-start gap-3.5">
              <div className="p-2 rounded-lg bg-white/10 text-white mt-0.5 flex-shrink-0">
                <Sparkles size={18} />
              </div>
              <div>
                <h3 className="font-semibold text-white text-body-lg">Instant Multi-Document Synthesis</h3>
                <p className="text-body-sm text-white/75 mt-0.5">
                  Index hundreds of PDF, DOCX, and TXT sources per workspace with automatic vector embeddings.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3.5">
              <div className="p-2 rounded-lg bg-white/10 text-white mt-0.5 flex-shrink-0">
                <Cpu size={18} />
              </div>
              <div>
                <h3 className="font-semibold text-white text-body-lg">Zero Hallucination Grounding</h3>
                <p className="text-body-sm text-white/75 mt-0.5">
                  Restricted context windows ensure answers are generated strictly from cited document passages.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3.5">
              <div className="p-2 rounded-lg bg-white/10 text-white mt-0.5 flex-shrink-0">
                <Shield size={18} />
              </div>
              <div>
                <h3 className="font-semibold text-white text-body-lg">SOC2 Type II Compliant</h3>
                <p className="text-body-sm text-white/75 mt-0.5">
                  Isolated workspaces with end-to-end encryption, verifiable citations, and full audit logging.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="text-code-sm text-white/60 relative z-10">
          Google Stitch UI Architecture · Enterprise Tier
        </div>
      </div>

      {/* ── Right Form Panel ── */}
      <div className="flex-1 min-w-0 w-full flex flex-col justify-center items-center p-6 sm:p-12 lg:p-16 min-h-screen">
        <div className="w-full max-w-md space-y-6">
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
              Create an account
            </h2>
            <p className="text-body-md mt-1.5" style={{ color: 'var(--color-on-surface-variant)' }}>
              Join your organization&apos;s intelligent knowledge workspace
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

          <form onSubmit={handleSubmit} className="space-y-3.5">
            <div>
              <label
                className="block text-label-md font-semibold mb-1"
                style={{ color: 'var(--color-on-surface)' }}
              >
                Full Name
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Dr. Elena Vance"
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
              <label
                className="block text-label-md font-semibold mb-1"
                style={{ color: 'var(--color-on-surface)' }}
              >
                Institutional Email
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="e.vance@research.ai"
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
              <label
                className="block text-label-md font-semibold mb-1"
                style={{ color: 'var(--color-on-surface)' }}
              >
                Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Minimum 8 characters"
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
              <label
                className="block text-label-md font-semibold mb-1"
                style={{ color: 'var(--color-on-surface)' }}
              >
                Confirm Password
              </label>
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter password"
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

            <div className="flex items-start gap-2 pt-1">
              <input
                type="checkbox"
                id="terms"
                checked={agreeTerms}
                onChange={(e) => setAgreeTerms(e.target.checked)}
                className="mt-1 w-4 h-4 rounded accent-[--color-primary] cursor-pointer"
              />
              <label htmlFor="terms" className="text-body-sm cursor-pointer select-none" style={{ color: 'var(--color-on-surface-variant)' }}>
                I agree to the Enterprise Master Services Agreement and Privacy Policy.
              </label>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              loading={loading}
              className="w-full mt-2 py-2.5 shadow-sm"
              icon={ArrowRight}
              iconPosition="right"
            >
              Create Enterprise Account
            </Button>
          </form>

          <div className="text-center text-body-sm" style={{ color: 'var(--color-on-surface-variant)' }}>
            Already have an account?{' '}
            <Link
              to="/auth/login"
              className="font-semibold hover:underline"
              style={{ color: 'var(--color-primary)' }}
            >
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
