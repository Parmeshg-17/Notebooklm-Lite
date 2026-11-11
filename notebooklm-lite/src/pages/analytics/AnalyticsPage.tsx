import { useState } from 'react';
import {
  ResponsiveContainer, LineChart, Line, AreaChart, Area,
  BarChart, Bar, PieChart, Pie, Cell, Tooltip,
  XAxis, YAxis, CartesianGrid, Legend
} from 'recharts';
import {
  Activity, CheckCircle2, AlertTriangle, Clock,
  DollarSign, Sparkles, BarChart2
} from 'lucide-react';
import MetricCard from '../../components/analytics/MetricCard';
import { MOCK_ANALYTICS } from '../../utils/mockData';

const PIE_DATA = [
  { name: 'Successful (Grounded)', value: 1384, color: '#006040' },
  { name: 'Failed / Unreachable', value: 45, color: '#ba1a1a' },
];

export default function AnalyticsPage() {
  const [timeRange, setTimeRange] = useState<'7D' | '30D' | '90D'>('7D');

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-300">
      {/* ── Page Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span
              className="text-label-sm font-semibold uppercase tracking-wider"
              style={{ color: 'var(--color-primary)' }}
            >
              Enterprise Telemetry & Observability
            </span>
            <span className="text-label-sm text-[--color-on-surface-variant]">·</span>
            <span className="text-label-sm text-[--color-on-surface-variant]">
              Production Cluster: us-east-4
            </span>
          </div>
          <h1 className="text-display-lg font-bold" style={{ color: 'var(--color-on-surface)' }}>
            AI Query Observability
          </h1>
          <p className="text-body-md mt-1" style={{ color: 'var(--color-on-surface-variant)' }}>
            Real-time inference metrics, token budgets, citation densities, and RAG error rates.
          </p>
        </div>

        {/* Date Range Selector */}
        <div
          className="flex items-center p-1 rounded-xl self-start sm:self-auto"
          style={{
            backgroundColor: 'var(--color-surface-container-low)',
            border: '1px solid var(--color-outline-variant)',
          }}
        >
          {(['7D', '30D', '90D'] as const).map((r) => (
            <button
              key={r}
              onClick={() => setTimeRange(r)}
              className={`px-3 py-1.5 rounded-lg text-label-md font-semibold transition-all ${
                timeRange === r
                  ? 'bg-[--color-surface-container-lowest] shadow-2xs text-[--color-primary]'
                  : 'text-[--color-on-surface-variant] hover:text-[--color-on-surface]'
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {/* ── Metric Cards Row 1: Query & Latency KPIs ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <MetricCard
          label="Total Queries"
          value={MOCK_ANALYTICS.totalQueries.toLocaleString()}
          change={12.4}
          changeLabel="vs last week"
          icon={Activity}
        />
        <MetricCard
          label="Success Rate"
          value="96.9%"
          change={1.2}
          trend="up"
          changeLabel="grounded"
          icon={CheckCircle2}
        />
        <MetricCard
          label="Failed Queries"
          value={MOCK_ANALYTICS.failedQueries}
          change={-18}
          trend="up"
          changeLabel="reduced"
          icon={AlertTriangle}
        />
        <MetricCard
          label="Avg Latency"
          value="1.24s"
          change={-5.8}
          trend="up"
          changeLabel="faster"
          icon={Clock}
        />
        <MetricCard
          label="P95 Latency"
          value="3.80s"
          subtitle="SLA threshold: 5.0s"
          icon={BarChart2}
        />
      </div>

      {/* ── Metric Cards Row 2: Token Economics & Satisfaction ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Input Tokens"
          value="2.84M"
          subtitle="Document context loaded"
          icon={Sparkles}
        />
        <MetricCard
          label="Output Tokens"
          value="1.12M"
          subtitle="Synthesized answers"
          icon={Sparkles}
        />
        <MetricCard
          label="Estimated Cost"
          value={`$${MOCK_ANALYTICS.estimatedCostUsd.toFixed(2)}`}
          change={4.2}
          changeLabel="within budget"
          icon={DollarSign}
        />
        <MetricCard
          label="User Satisfaction"
          value={`${MOCK_ANALYTICS.userSatisfactionScore} / 5.0`}
          subtitle="94% positive thumbs-up"
          icon={CheckCircle2}
        />
      </div>

      {/* ── Observability Charts ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart 1: Queries Over Time */}
        <div
          className="rounded-2xl p-6 shadow-xs space-y-4"
          style={{
            backgroundColor: 'var(--color-surface-container-lowest)',
            border: '1px solid color-mix(in srgb, var(--color-outline-variant) 40%, transparent)',
          }}
        >
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-headline-sm font-bold" style={{ color: 'var(--color-on-surface)' }}>
                Query Volume Trend
              </h3>
              <p className="text-body-sm" style={{ color: 'var(--color-on-surface-variant)' }}>
                Daily requests handled by the multi-corpus RAG pipeline
              </p>
            </div>
            <span
              className="text-code-sm px-2 py-0.5 rounded font-medium"
              style={{
                backgroundColor: 'var(--color-primary-fixed)',
                color: 'var(--color-on-primary-fixed-variant)',
              }}
            >
              Mean: 102 req/day
            </span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={MOCK_ANALYTICS.queriesOverTime}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--color-surface-container-high)" />
                <XAxis dataKey="date" stroke="var(--color-on-surface-variant)" fontSize={12} tickLine={false} />
                <YAxis stroke="var(--color-on-surface-variant)" fontSize={12} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--color-surface-container-lowest)',
                    borderColor: 'var(--color-outline-variant)',
                    borderRadius: '0.75rem',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  name="Queries"
                  stroke="#493ebf"
                  strokeWidth={2.5}
                  dot={{ r: 3, fill: '#493ebf' }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 2: Token Consumption Area Chart */}
        <div
          className="rounded-2xl p-6 shadow-xs space-y-4"
          style={{
            backgroundColor: 'var(--color-surface-container-lowest)',
            border: '1px solid color-mix(in srgb, var(--color-outline-variant) 40%, transparent)',
          }}
        >
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-headline-sm font-bold" style={{ color: 'var(--color-on-surface)' }}>
                Token Ingestion & Generation
              </h3>
              <p className="text-body-sm" style={{ color: 'var(--color-on-surface-variant)' }}>
                Daily token utilization across prompts and synthesis
              </p>
            </div>
            <span
              className="text-code-sm px-2 py-0.5 rounded font-medium"
              style={{
                backgroundColor: 'var(--color-tertiary-fixed)',
                color: 'var(--color-on-tertiary-fixed-variant)',
              }}
            >
              3.96M total
            </span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={MOCK_ANALYTICS.tokenUsageOverTime}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--color-surface-container-high)" />
                <XAxis dataKey="date" stroke="var(--color-on-surface-variant)" fontSize={12} tickLine={false} />
                <YAxis stroke="var(--color-on-surface-variant)" fontSize={12} tickLine={false} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--color-surface-container-lowest)',
                    borderColor: 'var(--color-outline-variant)',
                    borderRadius: '0.75rem',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                  }}
                  formatter={(val: unknown) => [`${val} tokens`, 'Usage']}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  name="Tokens"
                  stroke="#006040"
                  fill="#006040"
                  fillOpacity={0.2}
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 3: Response Latency Distribution */}
        <div
          className="rounded-2xl p-6 shadow-xs space-y-4"
          style={{
            backgroundColor: 'var(--color-surface-container-lowest)',
            border: '1px solid color-mix(in srgb, var(--color-outline-variant) 40%, transparent)',
          }}
        >
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-headline-sm font-bold" style={{ color: 'var(--color-on-surface)' }}>
                End-to-End Latency (ms)
              </h3>
              <p className="text-body-sm" style={{ color: 'var(--color-on-surface-variant)' }}>
                Average response time from query to first streamed citation
              </p>
            </div>
            <span
              className="text-code-sm px-2 py-0.5 rounded font-medium"
              style={{
                backgroundColor: 'var(--color-secondary-container)',
                color: 'var(--color-on-secondary-container)',
              }}
            >
              Target: &lt; 2000ms
            </span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={MOCK_ANALYTICS.latencyOverTime}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--color-surface-container-high)" />
                <XAxis dataKey="date" stroke="var(--color-on-surface-variant)" fontSize={12} tickLine={false} />
                <YAxis stroke="var(--color-on-surface-variant)" fontSize={12} tickLine={false} tickFormatter={(v) => `${v}ms`} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--color-surface-container-lowest)',
                    borderColor: 'var(--color-outline-variant)',
                    borderRadius: '0.75rem',
                  }}
                  formatter={(val: unknown) => [`${val} ms`, 'Latency']}
                />
                <Bar dataKey="value" name="Latency" fill="#6259d9" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 4: Grounding Success vs Error Breakdown */}
        <div
          className="rounded-2xl p-6 shadow-xs space-y-4"
          style={{
            backgroundColor: 'var(--color-surface-container-lowest)',
            border: '1px solid color-mix(in srgb, var(--color-outline-variant) 40%, transparent)',
          }}
        >
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-headline-sm font-bold" style={{ color: 'var(--color-on-surface)' }}>
                Grounding Precision Status
              </h3>
              <p className="text-body-sm" style={{ color: 'var(--color-on-surface-variant)' }}>
                Verification breakdown against indexed document chunks
              </p>
            </div>
          </div>

          <div className="h-64 w-full flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={PIE_DATA}
                  cx="50%"
                  cy="50%"
                  innerRadius={65}
                  outerRadius={95}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {PIE_DATA.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--color-surface-container-lowest)',
                    borderColor: 'var(--color-outline-variant)',
                    borderRadius: '0.75rem',
                  }}
                />
                <Legend verticalAlign="bottom" height={36} iconType="circle" />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
