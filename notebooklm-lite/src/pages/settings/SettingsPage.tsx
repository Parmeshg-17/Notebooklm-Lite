import { useState } from 'react';
import {
  User, Sparkles, Shield, Key,
  CreditCard, Check, Copy, AlertTriangle,
  Save, Eye, EyeOff
} from 'lucide-react';
import { useAuthStore } from '../../store';
import Button from '../../components/common/Button';

type Tab = 'profile' | 'ai' | 'data' | 'api' | 'account';

export default function SettingsPage() {
  const { user } = useAuthStore();

  const [activeTab, setActiveTab] = useState<Tab>('profile');
  const [savedSuccess, setSavedSuccess] = useState(false);

  // Profile form state
  const [name, setName] = useState(user?.name ?? 'Dr. Elena Vance');
  const [email, setEmail] = useState(user?.email ?? 'e.vance@research.ai');
  const [institution, setInstitution] = useState('DeepMind Advanced Research Institute');

  // AI preferences state
  const [model, setModel] = useState('text-embedding-3-large');
  const [responseStyle, setResponseStyle] = useState<'concise' | 'balanced' | 'detailed'>('balanced');
  const [citationDensity, setCitationDensity] = useState<'minimal' | 'standard' | 'verbose'>('standard');

  // API state
  const [showApiKey, setShowApiKey] = useState(false);
  const [copiedKey, setCopiedKey] = useState(false);
  const apiKey = 'nb_live_948f72a1e8c459d201bfa82937e01';

  // Data retention
  const [retentionDays, setRetentionDays] = useState('90');
  const [hybridSearch, setHybridSearch] = useState(true);

  const handleSave = () => {
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2500);
  };

  const copyKey = () => {
    navigator.clipboard.writeText(apiKey);
    setCopiedKey(true);
    setTimeout(() => setCopiedKey(false), 2000);
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-300">
      {/* ── Page Header ── */}
      <div>
        <h1 className="text-display-lg font-bold" style={{ color: 'var(--color-on-surface)' }}>
          System Settings
        </h1>
        <p className="text-body-md mt-1" style={{ color: 'var(--color-on-surface-variant)' }}>
          Manage your enterprise profile, AI grounding preferences, API access, and security policies.
        </p>
      </div>

      {/* ── Settings Split View ── */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-start">
        {/* Left Nav Tabs (col-span-3) */}
        <div
          className="md:col-span-3 rounded-2xl p-2 shadow-xs space-y-1"
          style={{
            backgroundColor: 'var(--color-surface-container-lowest)',
            border: '1px solid color-mix(in srgb, var(--color-outline-variant) 40%, transparent)',
          }}
        >
          {[
            { id: 'profile', label: 'User Profile', icon: User },
            { id: 'ai', label: 'AI & Grounding', icon: Sparkles },
            { id: 'data', label: 'Data & Privacy', icon: Shield },
            { id: 'api', label: 'API Configuration', icon: Key },
            { id: 'account', label: 'Enterprise Plan', icon: CreditCard },
          ].map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id as Tab)}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-label-md font-medium text-left transition-colors cursor-pointer ${
                  isActive
                    ? 'shadow-2xs'
                    : 'text-[--color-on-surface-variant] hover:bg-[--color-surface-container-low]'
                }`}
                style={{
                  backgroundColor: isActive ? 'var(--color-primary-container)' : 'transparent',
                  color: isActive ? 'var(--color-on-primary-container)' : 'inherit',
                }}
              >
                <Icon size={16} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>

        {/* Right Content Panel (col-span-9) */}
        <div
          className="md:col-span-9 rounded-2xl p-6 shadow-xs space-y-6"
          style={{
            backgroundColor: 'var(--color-surface-container-lowest)',
            border: '1px solid color-mix(in srgb, var(--color-outline-variant) 40%, transparent)',
          }}
        >
          {savedSuccess && (
            <div
              className="p-3.5 rounded-xl flex items-center gap-2 text-label-md font-semibold text-[--color-tertiary] animate-in fade-in"
              style={{ backgroundColor: 'var(--color-tertiary-fixed)' }}
            >
              <Check size={16} />
              <span>Settings saved successfully.</span>
            </div>
          )}

          {/* TAB 1: PROFILE */}
          {activeTab === 'profile' && (
            <div className="space-y-6">
              <div className="border-b pb-4" style={{ borderColor: 'var(--color-surface-container)' }}>
                <h3 className="text-headline-sm font-bold text-[--color-on-surface]">
                  Personal Profile
                </h3>
                <p className="text-body-sm text-[--color-on-surface-variant]">
                  Your enterprise identity and attribution on shared notebooks
                </p>
              </div>

              {/* Avatar row */}
              <div className="flex items-center gap-4">
                <div
                  className="w-16 h-16 rounded-full flex items-center justify-center text-headline-md font-bold text-white shadow-sm"
                  style={{ backgroundColor: 'var(--color-primary)' }}
                >
                  EV
                </div>
                <div>
                  <h4 className="text-body-md font-semibold text-[--color-on-surface]">{name}</h4>
                  <p className="text-body-sm text-[--color-on-surface-variant]">Lead Research Scientist</p>
                  <button
                    onClick={() => alert('Avatar upload modal')}
                    className="text-label-sm font-semibold hover:underline mt-1"
                    style={{ color: 'var(--color-primary)' }}
                  >
                    Change avatar
                  </button>
                </div>
              </div>

              <div className="space-y-4 max-w-lg">
                <div>
                  <label className="block text-label-md font-semibold mb-1 text-[--color-on-surface]">
                    Full Name
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-xl text-body-md outline-none border focus:border-[--color-primary]"
                    style={{
                      backgroundColor: 'var(--color-surface-container-low)',
                      borderColor: 'var(--color-outline-variant)',
                    }}
                  />
                </div>

                <div>
                  <label className="block text-label-md font-semibold mb-1 text-[--color-on-surface]">
                    Work Email
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-xl text-body-md outline-none border focus:border-[--color-primary]"
                    style={{
                      backgroundColor: 'var(--color-surface-container-low)',
                      borderColor: 'var(--color-outline-variant)',
                    }}
                  />
                </div>

                <div>
                  <label className="block text-label-md font-semibold mb-1 text-[--color-on-surface]">
                    Organization / Lab
                  </label>
                  <input
                    type="text"
                    value={institution}
                    onChange={(e) => setInstitution(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-xl text-body-md outline-none border focus:border-[--color-primary]"
                    style={{
                      backgroundColor: 'var(--color-surface-container-low)',
                      borderColor: 'var(--color-outline-variant)',
                    }}
                  />
                </div>

                <Button variant="primary" icon={Save} onClick={handleSave}>
                  Save Changes
                </Button>
              </div>
            </div>
          )}

          {/* TAB 2: AI & GROUNDING */}
          {activeTab === 'ai' && (
            <div className="space-y-6">
              <div className="border-b pb-4" style={{ borderColor: 'var(--color-surface-container)' }}>
                <h3 className="text-headline-sm font-bold text-[--color-on-surface]">
                  AI & Grounding Parameters
                </h3>
                <p className="text-body-sm text-[--color-on-surface-variant]">
                  Configure embedding models, synthesis temperature, and citation verification depth
                </p>
              </div>

              <div className="space-y-5 max-w-xl">
                <div>
                  <label className="block text-label-md font-semibold mb-2 text-[--color-on-surface]">
                    Primary Vector Embedding Model
                  </label>
                  <div className="space-y-2">
                    {[
                      {
                        id: 'text-embedding-3-large',
                        title: 'text-embedding-3-large (Recommended)',
                        desc: '3072 dimensions · High semantic accuracy for scientific & legal corpus',
                      },
                      {
                        id: 'text-embedding-3-small',
                        title: 'text-embedding-3-small',
                        desc: '1536 dimensions · Ultra-low latency retrieval',
                      },
                      {
                        id: 'colbert-v2',
                        title: 'ColBERT-v2 Late Interaction',
                        desc: 'Token-level multivector representation for exact citation matching',
                      },
                    ].map((opt) => (
                      <label
                        key={opt.id}
                        onClick={() => setModel(opt.id)}
                        className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-all ${
                          model === opt.id
                            ? 'border-[--color-primary] bg-[--color-surface-container-low]'
                            : 'border-[--color-outline-variant]'
                        }`}
                      >
                        <input
                          type="radio"
                          name="model"
                          checked={model === opt.id}
                          onChange={() => setModel(opt.id)}
                          className="mt-1 accent-[--color-primary]"
                        />
                        <div>
                          <div className="font-semibold text-body-md text-[--color-on-surface]">
                            {opt.title}
                          </div>
                          <div className="text-body-sm text-[--color-on-surface-variant]">
                            {opt.desc}
                          </div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-label-md font-semibold mb-2 text-[--color-on-surface]">
                    Response Synthesis Style
                  </label>
                  <div className="grid grid-cols-3 gap-3">
                    {(['concise', 'balanced', 'detailed'] as const).map((style) => (
                      <button
                        key={style}
                        type="button"
                        onClick={() => setResponseStyle(style)}
                        className={`p-2.5 rounded-xl border text-label-md font-semibold capitalize transition-all cursor-pointer ${
                          responseStyle === style
                            ? 'border-[--color-primary] bg-[--color-primary-fixed] text-[--color-on-primary-fixed-variant]'
                            : 'border-[--color-outline-variant] text-[--color-on-surface-variant]'
                        }`}
                      >
                        {style}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-label-md font-semibold mb-2 text-[--color-on-surface]">
                    Citation Density
                  </label>
                  <div className="grid grid-cols-3 gap-3">
                    {(['minimal', 'standard', 'verbose'] as const).map((density) => (
                      <button
                        key={density}
                        type="button"
                        onClick={() => setCitationDensity(density)}
                        className={`p-2.5 rounded-xl border text-label-md font-semibold capitalize transition-all cursor-pointer ${
                          citationDensity === density
                            ? 'border-[--color-primary] bg-[--color-primary-fixed] text-[--color-on-primary-fixed-variant]'
                            : 'border-[--color-outline-variant] text-[--color-on-surface-variant]'
                        }`}
                      >
                        {density}
                      </button>
                    ))}
                  </div>
                </div>

                <Button variant="primary" icon={Save} onClick={handleSave}>
                  Save AI Preferences
                </Button>
              </div>
            </div>
          )}

          {/* TAB 3: DATA & PRIVACY */}
          {activeTab === 'data' && (
            <div className="space-y-6">
              <div className="border-b pb-4" style={{ borderColor: 'var(--color-surface-container)' }}>
                <h3 className="text-headline-sm font-bold text-[--color-on-surface]">
                  Data Retention & Governance
                </h3>
                <p className="text-body-sm text-[--color-on-surface-variant]">
                  Compliance rules and indexing policies
                </p>
              </div>

              <div className="space-y-5 max-w-xl">
                <div className="flex items-center justify-between p-3.5 rounded-xl border" style={{ borderColor: 'var(--color-outline-variant)' }}>
                  <div>
                    <div className="font-semibold text-body-md text-[--color-on-surface]">
                      Hybrid BM25 + Dense Search
                    </div>
                    <div className="text-body-sm text-[--color-on-surface-variant]">
                      Combine lexical matching with semantic vectors
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={hybridSearch}
                    onChange={(e) => setHybridSearch(e.target.checked)}
                    className="accent-[--color-primary] w-4 h-4 cursor-pointer"
                  />
                </div>

                <div>
                  <label className="block text-label-md font-semibold mb-1 text-[--color-on-surface]">
                    Audit Log Retention Window
                  </label>
                  <select
                    value={retentionDays}
                    onChange={(e) => setRetentionDays(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-xl text-body-md outline-none border"
                    style={{
                      backgroundColor: 'var(--color-surface-container-low)',
                      borderColor: 'var(--color-outline-variant)',
                    }}
                  >
                    <option value="30">30 days (Ephemeral compliance)</option>
                    <option value="90">90 days (Recommended)</option>
                    <option value="365">365 days (Full annual audit)</option>
                  </select>
                </div>

                <div className="pt-4 border-t" style={{ borderColor: 'var(--color-surface-container)' }}>
                  <Button
                    variant="outline"
                    onClick={() => alert('Exporting all workspace citations and documents to encrypted archive...')}
                  >
                    Export All Workspace Data (ZIP)
                  </Button>
                </div>

                {/* Danger zone */}
                <div
                  className="p-4 rounded-xl border border-red-200 mt-6 space-y-2"
                  style={{ backgroundColor: 'var(--color-error-container)' }}
                >
                  <div className="flex items-center gap-2 text-label-md font-bold" style={{ color: 'var(--color-on-error-container)' }}>
                    <AlertTriangle size={16} />
                    <span>Danger Zone</span>
                  </div>
                  <p className="text-body-sm" style={{ color: 'var(--color-on-error-container)' }}>
                    Deleting your workspace will immediately purge all indexed embeddings and citation links.
                  </p>
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => confirm('Are you sure you want to purge all workspace data?')}
                  >
                    Purge All Embeddings
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: API CONFIGURATION */}
          {activeTab === 'api' && (
            <div className="space-y-6">
              <div className="border-b pb-4" style={{ borderColor: 'var(--color-surface-container)' }}>
                <h3 className="text-headline-sm font-bold text-[--color-on-surface]">
                  API Keys & FastAPIBase URL
                </h3>
                <p className="text-body-sm text-[--color-on-surface-variant]">
                  Integrate your custom scripts, Zotero bridges, or CI/CD pipelines
                </p>
              </div>

              <div className="space-y-4 max-w-xl">
                <div>
                  <label className="block text-label-md font-semibold mb-1 text-[--color-on-surface]">
                    Enterprise Secret API Key
                  </label>
                  <div className="flex items-center gap-2">
                    <div
                      className="flex-1 flex items-center justify-between px-3.5 py-2 rounded-xl border font-mono text-code-sm"
                      style={{
                        backgroundColor: 'var(--color-surface-container-low)',
                        borderColor: 'var(--color-outline-variant)',
                        color: 'var(--color-on-surface)',
                      }}
                    >
                      <span>{showApiKey ? apiKey : '••••••••••••••••••••••••••••••••••••'}</span>
                      <button
                        onClick={() => setShowApiKey(!showApiKey)}
                        className="text-[--color-on-surface-variant] hover:text-[--color-on-surface]"
                      >
                        {showApiKey ? <EyeOff size={15} /> : <Eye size={15} />}
                      </button>
                    </div>
                    <Button variant="secondary" icon={Copy} onClick={copyKey}>
                      {copiedKey ? 'Copied' : 'Copy'}
                    </Button>
                  </div>
                </div>

                <div className="p-3.5 rounded-xl border text-body-sm" style={{ borderColor: 'var(--color-outline-variant)' }}>
                  <div className="font-semibold text-[--color-on-surface] mb-1">
                    Monthly API Quota
                  </div>
                  <div className="flex justify-between text-code-sm text-[--color-on-surface-variant] mb-1">
                    <span>1,429 / 100,000 queries used</span>
                    <span>1.4%</span>
                  </div>
                  <div className="w-full h-1.5 rounded-full overflow-hidden bg-[--color-surface-container]">
                    <div className="h-full bg-[--color-primary] w-[1.4%]" />
                  </div>
                </div>

                <Button
                  variant="outline"
                  onClick={() => alert('New API key generated and old key revoked.')}
                >
                  Regenerate API Key
                </Button>
              </div>
            </div>
          )}

          {/* TAB 5: ENTERPRISE PLAN */}
          {activeTab === 'account' && (
            <div className="space-y-6">
              <div className="border-b pb-4" style={{ borderColor: 'var(--color-surface-container)' }}>
                <h3 className="text-headline-sm font-bold text-[--color-on-surface]">
                  Enterprise Plan & Licensing
                </h3>
                <p className="text-body-sm text-[--color-on-surface-variant]">
                  Account tier: Enterprise Dedicated Cluster
                </p>
              </div>

              <div className="space-y-4 max-w-xl">
                <div
                  className="p-5 rounded-2xl border"
                  style={{
                    backgroundColor: 'var(--color-surface-container-low)',
                    borderColor: 'var(--color-primary)',
                  }}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-headline-md font-bold text-[--color-primary]">
                      Enterprise Pro
                    </span>
                    <span
                      className="px-2 py-0.5 rounded-full text-code-sm font-semibold"
                      style={{
                        backgroundColor: 'var(--color-tertiary-fixed)',
                        color: 'var(--color-on-tertiary-fixed-variant)',
                      }}
                    >
                      Active · v1.4 Ent
                    </span>
                  </div>
                  <p className="text-body-sm text-[--color-on-surface-variant]">
                    Dedicated vector instance, unlimited workspaces, ColBERT re-ranking, and priority DeepMind support.
                  </p>
                </div>

                <div className="flex gap-2">
                  <Button variant="primary" onClick={() => alert('Opening enterprise billing portal...')}>
                    Manage Subscription
                  </Button>
                  <Button variant="secondary" onClick={() => alert('Opening team seats manager...')}>
                    Invite Collaborators
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
