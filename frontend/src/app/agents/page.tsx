'use client';

import { useEffect, useState } from 'react';
import { agentAPI } from '@/lib/api';

type AgentStatus = {
  ollama_available: boolean;
  selected_model: string | null;
  installed_models: string[];
  mode: string;
  langchain_available?: boolean;
  langgraph_available?: boolean;
  email_configured?: boolean;
};

export default function AgentsPage() {
  const [status, setStatus] = useState<AgentStatus | null>(null);
  const [question, setQuestion] = useState('What is the sprint status?');
  const [prompt, setPrompt] = useState(
    'Create project called Customer Support Portal with key CSP, create a scrum board, create a high priority story for implementing secure login, assign it to rupam, and send the issue mail notification.'
  );
  const [repositoryUrl, setRepositoryUrl] = useState('https://github.com/example/repository');
  const [repositoryBranch, setRepositoryBranch] = useState('');
  const [repositoryToken, setRepositoryToken] = useState('');
  const [maxFiles, setMaxFiles] = useState('120');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    void loadStatus();
  }, []);

  async function loadStatus() {
    const response = await agentAPI.getStatus();
    setStatus(response.data);
  }

  async function runAutomation() {
    setLoading(true);
    try {
      const response = await agentAPI.runAutomation({ intent: 'full_scan' });
      setResult(response.data);
    } finally {
      setLoading(false);
    }
  }

  async function askAgent() {
    setLoading(true);
    try {
      const response = await agentAPI.ask(question);
      setResult(response.data);
    } finally {
      setLoading(false);
    }
  }

  async function executePrompt() {
    setLoading(true);
    try {
      const response = await agentAPI.executePrompt(prompt);
      setResult(response.data);
      await loadStatus();
    } finally {
      setLoading(false);
    }
  }

  async function reviewRepository() {
    setLoading(true);
    try {
      const response = await agentAPI.reviewRepository({
        repository_url: repositoryUrl,
        branch: repositoryBranch.trim() || undefined,
        github_token: repositoryToken.trim() || undefined,
        max_files: maxFiles ? Number(maxFiles) : undefined,
      });
      setResult(response.data);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] border border-slate-200 bg-white/85 p-6 shadow-[0_22px_55px_rgba(15,23,42,0.08)] backdrop-blur">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-sky-600">Agentic AI</p>
        <h2 className="mt-2 text-2xl font-semibold text-slate-950">Automation command center</h2>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          Run the full backend workflow, inspect pending actions, or ask focused operational questions.
        </p>

        <div className="mt-5 flex flex-wrap gap-3 text-sm">
          <div className="rounded-2xl bg-slate-100 px-4 py-2 text-slate-700">
            Mode: <span className="font-semibold">{status?.mode || 'Loading...'}</span>
          </div>
          <div className="rounded-2xl bg-slate-100 px-4 py-2 text-slate-700">
            Model: <span className="font-semibold">{status?.selected_model || 'Fallback only'}</span>
          </div>
          <div className="rounded-2xl bg-slate-100 px-4 py-2 text-slate-700">
            LangChain: <span className="font-semibold">{status?.langchain_available ? 'Ready' : 'Not installed'}</span>
          </div>
          <div className="rounded-2xl bg-slate-100 px-4 py-2 text-slate-700">
            LangGraph: <span className="font-semibold">{status?.langgraph_available ? 'Ready' : 'Fallback graph'}</span>
          </div>
          <div className="rounded-2xl bg-slate-100 px-4 py-2 text-slate-700">
            Email: <span className="font-semibold">{status?.email_configured ? 'Configured' : 'Needs SMTP env'}</span>
          </div>
        </div>

        <div className="mt-6 flex flex-wrap gap-3">
          <button
            onClick={runAutomation}
            disabled={loading}
            className="rounded-2xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-60"
          >
            Run full automation
          </button>
          <button
            onClick={() => setResult(null)}
            className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            Clear output
          </button>
        </div>
      </section>

      <section className="rounded-[2rem] border border-slate-200 bg-white/85 p-6 shadow-[0_22px_55px_rgba(15,23,42,0.08)] backdrop-blur">
        <h3 className="text-lg font-semibold text-slate-950">Execute full prompt automation</h3>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          This path can create a project, create a board, create an issue, assign it to a named teammate or auto assign it, and attempt assignment email delivery.
        </p>
        <textarea
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          className="mt-4 min-h-[150px] w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-sky-400"
          placeholder="Describe the full workflow you want ZYRAA to automate..."
        />
        <div className="mt-4 flex flex-wrap gap-3">
          <button
            onClick={executePrompt}
            disabled={loading}
            className="rounded-2xl bg-emerald-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:opacity-60"
          >
            Run prompt automation
          </button>
        </div>
      </section>

      <section className="rounded-[2rem] border border-slate-200 bg-white/85 p-6 shadow-[0_22px_55px_rgba(15,23,42,0.08)] backdrop-blur">
        <h3 className="text-lg font-semibold text-slate-950">Ask an agent</h3>
        <div className="mt-4 flex flex-col gap-3 sm:flex-row">
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            className="flex-1 rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-sky-400"
            placeholder="Ask about sprint health, assignments, or PR review status..."
          />
          <button
            onClick={askAgent}
            disabled={loading}
            className="rounded-2xl bg-sky-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-sky-500 disabled:opacity-60"
          >
            Ask
          </button>
        </div>
      </section>

      <section className="rounded-[2rem] border border-slate-200 bg-white/85 p-6 shadow-[0_22px_55px_rgba(15,23,42,0.08)] backdrop-blur">
        <h3 className="text-lg font-semibold text-slate-950">Review a GitHub repository</h3>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Paste a GitHub repository link and the agent will scan accessible source files for vulnerabilities, implementation risks, and heuristic syntax quality across mixed-language stacks.
        </p>

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <input
            value={repositoryUrl}
            onChange={(event) => setRepositoryUrl(event.target.value)}
            className="md:col-span-2 rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-sky-400"
            placeholder="https://github.com/owner/repository"
          />
          <input
            value={repositoryBranch}
            onChange={(event) => setRepositoryBranch(event.target.value)}
            className="rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-sky-400"
            placeholder="Branch (optional)"
          />
          <input
            value={maxFiles}
            onChange={(event) => setMaxFiles(event.target.value)}
            className="rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-sky-400"
            placeholder="Max files"
          />
          <input
            value={repositoryToken}
            onChange={(event) => setRepositoryToken(event.target.value)}
            className="md:col-span-2 rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-sky-400"
            placeholder="GitHub token for private repos (optional)"
          />
        </div>

        <div className="mt-4 flex flex-wrap gap-3">
          <button
            onClick={reviewRepository}
            disabled={loading || !repositoryUrl.trim()}
            className="rounded-2xl bg-violet-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:opacity-60"
          >
            Review repository
          </button>
        </div>
      </section>

      {result && (
        <section className="rounded-[2rem] border border-slate-200 bg-slate-950 p-6 text-slate-100 shadow-[0_22px_55px_rgba(15,23,42,0.18)]">
          <h3 className="text-lg font-semibold">Agent output</h3>
          <pre className="mt-4 overflow-auto rounded-2xl bg-black/20 p-4 text-xs leading-6">
            {JSON.stringify(result, null, 2)}
          </pre>
        </section>
      )}
    </div>
  );
}
