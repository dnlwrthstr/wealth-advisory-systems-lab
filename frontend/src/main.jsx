import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import CustodianApp from "./custodian";
import {
  fetchQuestionnaire,
  listClientSegments,
  listCustodyCustomers,
  listQuestionnaires,
  processAnswers,
  saveClientSegment,
  saveQuestionnaire,
} from "./services/api";
import "./styles.css";

const DEFAULT_ANSWERS = {
  loss_reaction: "hold",
  portfolio_decline_comfort: "somewhat_comfortable",
  investment_experience: "funds_and_etfs",
  product_knowledge: "general",
  horizon: "7_to_15_years",
  liquidity_need: "moderate",
  has_dependents: true,
};

const DEFAULT_PRODUCT = {
  product_id: "P-204",
  name: "Global Multi-Asset Fund",
  risk_level: "medium",
  required_knowledge: "basic",
  instrument_type: "funds_etfs",
  minimum_instrument_experience: "basic",
  daily_liquidity: true,
};

// ─── Top-level shell ────────────────────────────────────────────────────────

function App() {
  const [status, setStatus] = useState("Loading");
  const [message, setMessage] = useState("");
  const [activeSection, setActiveSection] = useState("custodian");

  // Questionnaire admin state
  const [questionnaires, setQuestionnaires] = useState([]);
  const [selectedId, setSelectedId] = useState("client_profile_v1");
  const [questionnaire, setQuestionnaire] = useState(null);
  const [editorText, setEditorText] = useState("");
  const [clientSegments, setClientSegments] = useState([]);

  // Profiling state
  const [customers, setCustomers] = useState([]);
  const [answers, setAnswers] = useState(DEFAULT_ANSWERS);
  const [product, setProduct] = useState(DEFAULT_PRODUCT);
  const [result, setResult] = useState(null);

  useEffect(() => {
    async function load() {
      const errors = [];
      try {
        const items = await listQuestionnaires();
        setQuestionnaires(items);
        const firstId = items[0]?.questionnaire_id ?? "client_profile_v1";
        setSelectedId(firstId);
        const detail = await fetchQuestionnaire(firstId);
        setQuestionnaire(detail);
        setEditorText(JSON.stringify(detail, null, 2));
      } catch (error) {
        errors.push(`Questionnaires: ${error.message}`);
      }
      try {
        setClientSegments(await listClientSegments());
      } catch (error) {
        errors.push(`Client segments: ${error.message}`);
      }
      try {
        setCustomers(await listCustodyCustomers());
      } catch (error) {
        errors.push(`Customers: ${error.message}`);
      }
      setStatus(errors.length ? "API partial" : "API online");
      setMessage(errors.join(" | "));
    }
    load();
  }, []);

  useEffect(() => {
    async function loadSelected() {
      if (!selectedId) return;
      try {
        const detail = await fetchQuestionnaire(selectedId);
        setQuestionnaire(detail);
        setEditorText(JSON.stringify(detail, null, 2));
      } catch (error) {
        setMessage(error.message);
      }
    }
    loadSelected();
  }, [selectedId]);

  const orderedQuestions = useMemo(() => questionnaire?.questions ?? [], [questionnaire]);

  async function handleSaveQuestionnaire(event) {
    event.preventDefault();
    setMessage("");
    try {
      const payload = JSON.parse(editorText);
      const saved = await saveQuestionnaire(payload);
      setQuestionnaire(saved);
      setSelectedId(saved.questionnaire_id);
      setEditorText(JSON.stringify(saved, null, 2));
      setQuestionnaires(await listQuestionnaires());
      setMessage("Questionnaire saved");
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function handleProcess(clientId, financialContext) {
    setMessage("");
    try {
      const payload = {
        answer_set: { client_id: clientId, answers },
        financial_context: financialContext,
        product,
      };
      setResult(await processAnswers(selectedId, payload));
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function handleSaveSegment(segment) {
    setMessage("");
    try {
      const saved = await saveClientSegment(segment);
      setClientSegments((current) => {
        const exists = current.some((item) => item.segment_id === saved.segment_id);
        return exists
          ? current.map((item) => (item.segment_id === saved.segment_id ? saved : item))
          : [...current, saved];
      });
      setMessage("Client segment saved");
    } catch (error) {
      setMessage(error.message);
    }
  }

  return (
    <main className="app-layout">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">Wealth Advisory</p>
          <h1>Systems Lab</h1>
        </div>
        <nav className="side-menu" aria-label="Main menu">
          {[
            ["custodian", "Custodian"],
            ["questionnaires", "Questionnaires"],
            ["profile", "Profile"],
          ].map(([key, label]) => (
            <button
              key={key}
              className={activeSection === key ? "active" : ""}
              type="button"
              onClick={() => setActiveSection(key)}
            >
              {label}
            </button>
          ))}
        </nav>
        <div className={`status ${status === "API online" ? "ok" : status === "API partial" ? "api-partial" : "error"}`}>
          {status}
        </div>
      </aside>

      <section className="content-shell">
        {message ? <p className="message">{message}</p> : null}
        {activeSection === "custodian" && <CustodianApp />}
        {activeSection === "questionnaires" && (
          <QuestionnairesView
            questionnaires={questionnaires}
            selectedId={selectedId}
            setSelectedId={setSelectedId}
            questionnaire={questionnaire}
            editorText={editorText}
            setEditorText={setEditorText}
            onSave={handleSaveQuestionnaire}
            clientSegments={clientSegments}
            onSaveSegment={handleSaveSegment}
          />
        )}
        {activeSection === "profile" && (
          <ProfileView
            customers={customers}
            questionnaires={questionnaires}
            selectedQuestionnaireId={selectedId}
            onSelectQuestionnaire={setSelectedId}
            questionnaire={questionnaire}
            questions={orderedQuestions}
            answers={answers}
            setAnswers={setAnswers}
            product={product}
            setProduct={setProduct}
            result={result}
            onProcess={handleProcess}
          />
        )}
      </section>
    </main>
  );
}

// ─── Questionnaires view ─────────────────────────────────────────────────────
// Purpose: admin configuration — design questionnaire DAGs, manage client segments.

function QuestionnairesView({
  questionnaires,
  selectedId,
  setSelectedId,
  questionnaire,
  editorText,
  setEditorText,
  onSave,
  clientSegments,
  onSaveSegment,
}) {
  return (
    <section className="admin-layout">
      <SegmentAdmin segments={clientSegments} onSaveSegment={onSaveSegment} />

      <section className="admin-section">
        <div className="section-header">
          <h2>Questionnaire Definition</h2>
          <label className="inline-select">
            Active
            <select value={selectedId} onChange={(event) => setSelectedId(event.target.value)}>
              {questionnaires.map((item) => (
                <option key={item.questionnaire_id} value={item.questionnaire_id}>
                  {item.questionnaire_id} v{item.version}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="work-grid">
          <section className="panel">
            <h3>Flow</h3>
            <QuestionnaireTree questionnaire={questionnaire} />
          </section>

          <form className="panel admin-panel" onSubmit={onSave}>
            <div className="section-header">
              <h3>JSON Editor</h3>
              <button type="submit">Save</button>
            </div>
            <textarea
              spellCheck="false"
              value={editorText}
              onChange={(event) => setEditorText(event.target.value)}
            />
          </form>
        </div>
      </section>
    </section>
  );
}

// ─── Profile view ────────────────────────────────────────────────────────────
// Purpose: advisor workflow — run profiling for existing or new clients.

function ProfileView({
  customers,
  questionnaires,
  selectedQuestionnaireId,
  onSelectQuestionnaire,
  questionnaire,
  questions,
  answers,
  setAnswers,
  product,
  setProduct,
  result,
  onProcess,
}) {
  const [mode, setMode] = useState("existing"); // "existing" | "new"

  return (
    <section className="admin-layout">
      <div className="section-header" style={{ padding: "0 0 1rem" }}>
        <h2>Client Profiling</h2>
        <div className="tab-bar">
          <button
            type="button"
            className={mode === "existing" ? "active" : ""}
            onClick={() => setMode("existing")}
          >
            Existing Client
          </button>
          <button
            type="button"
            className={mode === "new" ? "active" : ""}
            onClick={() => setMode("new")}
          >
            New Client
          </button>
        </div>
      </div>

      {mode === "existing" ? (
        <ReprofilingView
          customers={customers}
          questionnaires={questionnaires}
          selectedQuestionnaireId={selectedQuestionnaireId}
          onSelectQuestionnaire={onSelectQuestionnaire}
          questionnaire={questionnaire}
          questions={questions}
          answers={answers}
          setAnswers={setAnswers}
          product={product}
          setProduct={setProduct}
          result={result}
          onProcess={onProcess}
        />
      ) : (
        <OnboardingView customers={customers} />
      )}
    </section>
  );
}

// ─── Existing client: reprofiling / periodic review ──────────────────────────

function ReprofilingView({
  customers,
  questionnaires,
  selectedQuestionnaireId,
  onSelectQuestionnaire,
  questionnaire,
  questions,
  answers,
  setAnswers,
  product,
  setProduct,
  result,
  onProcess,
}) {
  const [selectedCustomerId, setSelectedCustomerId] = useState(customers[0]?.id ?? "");
  const [financialContext, setFinancialContext] = useState({
    age: 42,
    annual_income: 180000,
    liquid_net_worth: 750000,
    restrictions: [],
  });

  // Keep default selection in sync once customers load
  useEffect(() => {
    if (!selectedCustomerId && customers.length) {
      setSelectedCustomerId(customers[0].id);
    }
  }, [customers]);

  function updateContext(field, value) {
    setFinancialContext((ctx) => ({ ...ctx, [field]: value }));
  }

  function handleSubmit(event) {
    event.preventDefault();
    onProcess(selectedCustomerId, financialContext);
  }

  return (
    <section className="admin-section">
      <div className="section-header">
        <p className="muted">Reprofiling or periodic review for an existing client.</p>
        <label className="inline-select">
          Questionnaire
          <select
            value={selectedQuestionnaireId}
            onChange={(event) => onSelectQuestionnaire(event.target.value)}
          >
            {questionnaires.map((item) => (
              <option key={item.questionnaire_id} value={item.questionnaire_id}>
                {item.questionnaire_id} v{item.version}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="work-grid">
        <form className="panel" onSubmit={handleSubmit}>
          <div className="section-header">
            <h3>Client &amp; Context</h3>
          </div>

          <label>
            Client
            <select
              value={selectedCustomerId}
              onChange={(event) => setSelectedCustomerId(event.target.value)}
            >
              {customers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.id})
                </option>
              ))}
            </select>
          </label>

          <div className="three-col" style={{ marginTop: "1rem" }}>
            <label>
              Age
              <input
                type="number"
                min="18"
                max="100"
                value={financialContext.age}
                onChange={(e) => updateContext("age", Number(e.target.value))}
              />
            </label>
            <label>
              Annual income (CHF)
              <input
                type="number"
                min="0"
                step="10000"
                value={financialContext.annual_income}
                onChange={(e) => updateContext("annual_income", Number(e.target.value))}
              />
            </label>
            <label>
              Liquid net worth (CHF)
              <input
                type="number"
                min="0"
                step="50000"
                value={financialContext.liquid_net_worth}
                onChange={(e) => updateContext("liquid_net_worth", Number(e.target.value))}
              />
            </label>
          </div>

          <div className="section-header" style={{ marginTop: "1.5rem" }}>
            <h3>Questionnaire Answers</h3>
          </div>
          <div className="question-list">
            {questions.map((question) => (
              <QuestionField
                key={question.question_id}
                question={question}
                value={answers[question.question_id]}
                onChange={(value) =>
                  setAnswers((current) => ({ ...current, [question.question_id]: value }))
                }
              />
            ))}
          </div>

          <ProductPanel product={product} setProduct={setProduct} />

          <div style={{ marginTop: "1.5rem" }}>
            <button type="submit">Run Profile</button>
          </div>
        </form>

        <ResultPanel result={result} />
      </div>
    </section>
  );
}

// ─── New client: KYC + segmentation + profiling ───────────────────────────────

function OnboardingView() {
  return (
    <section className="admin-section">
      <div className="panel empty-state">
        <h3>New Client Onboarding</h3>
        <p>
          The onboarding workflow covers KYC data capture, client segmentation, and initial
          profiling. This will be built in the next iteration.
        </p>
        <ol className="plain-list onboarding-steps">
          <li>KYC — identity, legal entity, tax residency</li>
          <li>Segmentation — assign client segment based on AuM and mandate type</li>
          <li>Profiling — run the segment's assigned questionnaire and derive strategy</li>
        </ol>
      </div>
    </section>
  );
}

// ─── Shared components ────────────────────────────────────────────────────────

function QuestionField({ question, value, onChange }) {
  if (question.answer_type === "multiple_choice") {
    const selectedValues = Array.isArray(value) ? value : [];
    return (
      <fieldset className="question choice-group">
        <legend>
          {question.prompt}
          <small>{question.ontology_path}</small>
        </legend>
        {question.options.map((option) => (
          <label key={String(option.value)} className="checkbox-row">
            <input
              type="checkbox"
              checked={selectedValues.includes(option.value)}
              onChange={(event) => {
                const next = event.target.checked
                  ? [...selectedValues, option.value]
                  : selectedValues.filter((item) => item !== option.value);
                onChange(next);
              }}
            />
            {option.label}
          </label>
        ))}
      </fieldset>
    );
  }

  if (question.answer_type === "slider") {
    const scale = question.scale ?? { min: 1, max: 5, step: 1 };
    return (
      <label className="question">
        <span>
          {question.prompt}
          <small>{question.ontology_path}</small>
        </span>
        <div className="slider-row">
          <span>{scale.min_label ?? scale.min}</span>
          <input
            type="range"
            min={scale.min}
            max={scale.max}
            step={scale.step}
            value={value ?? scale.min}
            onChange={(event) => onChange(Number(event.target.value))}
          />
          <strong>{value ?? scale.min}</strong>
          <span>{scale.max_label ?? scale.max}</span>
        </div>
      </label>
    );
  }

  if (question.answer_type === "text") {
    return (
      <label className="question">
        <span>
          {question.prompt}
          <small>{question.ontology_path}</small>
        </span>
        <textarea
          className="short-textarea"
          maxLength={question.max_length ?? undefined}
          value={value ?? ""}
          onChange={(event) => onChange(event.target.value)}
        />
      </label>
    );
  }

  if (question.answer_type === "image_choice" || question.answer_type === "image_upload") {
    return (
      <div className="question deferred-question">
        <span>
          {question.prompt}
          <small>{question.ontology_path}</small>
        </span>
        <p>Image questions are defined in the model but deferred from the first implementation.</p>
      </div>
    );
  }

  return (
    <label className="question">
      <span>
        {question.prompt}
        <small>{question.ontology_path}</small>
      </span>
      {question.answer_type === "boolean" ? (
        <select value={String(value ?? false)} onChange={(event) => onChange(event.target.value === "true")}>
          {question.options.map((option) => (
            <option key={String(option.value)} value={String(option.value)}>
              {option.label}
            </option>
          ))}
        </select>
      ) : (
        <select value={value ?? ""} onChange={(event) => onChange(event.target.value)}>
          {question.options.map((option) => (
            <option key={String(option.value)} value={String(option.value)}>
              {option.label} · {option.score}
            </option>
          ))}
        </select>
      )}
    </label>
  );
}

function QuestionnaireTree({ questionnaire }) {
  const nodes = questionnaire?.nodes ?? [];
  const edges = questionnaire?.edges ?? [];
  const questions = questionnaire?.questions ?? [];

  if (!nodes.length && !questions.length) return null;

  const treeNodes = nodes.length
    ? nodes
    : questions.map((question, index) => ({
        node_id: question.question_id,
        kind: "question",
        question,
        navigation: { display_order: (index + 1) * 10 },
      }));

  const childrenByNode = edges.reduce((groups, edge) => {
    groups[edge.from_node_id] = [...(groups[edge.from_node_id] ?? []), edge];
    return groups;
  }, {});
  const nodeById = Object.fromEntries(treeNodes.map((node) => [node.node_id, node]));
  const entryNodeId = questionnaire?.entry_node_id ?? treeNodes[0]?.node_id;

  function renderNode(nodeId, depth = 0, visited = new Set()) {
    const node = nodeById[nodeId];
    if (!node || visited.has(nodeId)) return null;
    const nextVisited = new Set(visited);
    nextVisited.add(nodeId);
    const childEdges = childrenByNode[nodeId] ?? [];
    return (
      <li key={`${nodeId}-${depth}`} style={{ "--depth": depth }}>
        <div>
          <strong>{node.question?.question_id ?? node.label ?? node.node_id}</strong>
          <span>{node.kind}</span>
        </div>
        {childEdges.length ? (
          <ul>
            {childEdges.map((edge) => (
              <React.Fragment key={`${edge.from_node_id}-${edge.to_node_id}`}>
                <li className="edge-label" style={{ "--depth": depth + 1 }}>
                  {edge.condition
                    ? `${edge.condition.question_id} ${edge.condition.operator} ${String(edge.condition.value)}`
                    : "next"}
                </li>
                {renderNode(edge.to_node_id, depth + 1, nextVisited)}
              </React.Fragment>
            ))}
          </ul>
        ) : null}
      </li>
    );
  }

  return (
    <section className="tree-panel">
      <ul>{entryNodeId ? renderNode(entryNodeId) : null}</ul>
    </section>
  );
}

function ProductPanel({ product, setProduct }) {
  function update(field, value) {
    setProduct((current) => ({ ...current, [field]: value }));
  }
  return (
    <section className="subpanel" style={{ marginTop: "1.5rem" }}>
      <h3>Product Gate Input</h3>
      <div className="three-col">
        <label>
          Instrument
          <select value={product.instrument_type} onChange={(e) => update("instrument_type", e.target.value)}>
            <option value="equities">Equities</option>
            <option value="bonds">Bonds</option>
            <option value="funds_etfs">Funds / ETFs</option>
            <option value="derivatives">Derivatives</option>
            <option value="structured_products">Structured products</option>
          </select>
        </label>
        <label>
          Min experience
          <select value={product.minimum_instrument_experience} onChange={(e) => update("minimum_instrument_experience", e.target.value)}>
            <option value="none">None</option>
            <option value="basic">Basic</option>
            <option value="experienced">Experienced</option>
            <option value="advanced">Advanced</option>
          </select>
        </label>
        <label>
          Risk
          <select value={product.risk_level} onChange={(e) => update("risk_level", e.target.value)}>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </label>
        <label>
          Knowledge
          <select value={product.required_knowledge} onChange={(e) => update("required_knowledge", e.target.value)}>
            <option value="basic">Basic</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </select>
        </label>
        <label>
          Liquidity
          <select value={String(product.daily_liquidity)} onChange={(e) => update("daily_liquidity", e.target.value === "true")}>
            <option value="true">Daily</option>
            <option value="false">Not daily</option>
          </select>
        </label>
      </div>
    </section>
  );
}

function ResultPanel({ result }) {
  if (!result) {
    return (
      <section className="panel empty-state">
        <h2>Profile Output</h2>
        <p>Run the questionnaire to derive profile, strategy, gates, and audit evidence.</p>
      </section>
    );
  }
  return (
    <section className="panel result-panel">
      <div className="section-header">
        <h2>Profile Output</h2>
        <span className={result.valid ? "badge ok" : "badge error"}>
          {result.valid ? "Valid" : "Invalid"}
        </span>
      </div>
      <MetricGrid
        metrics={[
          ["Processing run", result.processing_run_id ?? "Not stored"],
          ["Strategy", result.strategy_profile?.strategy ?? "-"],
          ["Risk profile", result.strategy_profile?.risk_profile_category ?? "-"],
          ["Combined risk", result.strategy_profile?.combined_risk_profile ?? "-"],
          ["Review", result.requires_review ? "Required" : "No"],
          ["Passed", result.passed === false ? "No" : "Yes"],
        ]}
      />
      <h3>Gates</h3>
      <div className="gate-list">
        {result.gates.map((gate) => (
          <article key={gate.gate_id} className={`gate ${gate.passed ? "passed" : "failed"}`}>
            <strong>{gate.gate_id}</strong>
            <span>{gate.gate_type}</span>
            <p>{gate.message}</p>
            <small>{gate.ontology_path}</small>
          </article>
        ))}
      </div>
      <h3>Suitability Envelope</h3>
      <pre>{JSON.stringify(result.strategy_profile?.suitability_envelope ?? {}, null, 2)}</pre>
      <h3>Warnings and Errors</h3>
      <ul className="plain-list">
        {[...result.warnings, ...result.errors].length ? (
          [...result.warnings, ...result.errors].map((item) => <li key={item}>{item}</li>)
        ) : (
          <li>No warnings or errors</li>
        )}
      </ul>
    </section>
  );
}

function MetricGrid({ metrics }) {
  return (
    <dl className="metrics">
      {metrics.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function SegmentAdmin({ segments, onSaveSegment }) {
  const [draft, setDraft] = useState({
    segment_id: "",
    label: "",
    description: "",
    minimum_liquid_net_worth: 0,
    default_questionnaire_id: "client_profile_v1",
    review_policy: "standard",
    enabled: true,
  });

  function edit(field, value) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  function handleSubmit(event) {
    event.preventDefault();
    onSaveSegment({
      ...draft,
      segment_id: draft.segment_id.trim(),
      label: draft.label.trim(),
      description: draft.description.trim(),
      minimum_liquid_net_worth: Number(draft.minimum_liquid_net_worth),
    });
  }

  return (
    <section className="panel">
      <div className="section-header">
        <h2>Client Segments</h2>
        <span className="badge">Admin config</span>
      </div>
      <div className="segment-grid">
        <div className="segment-list">
          {segments.map((segment) => (
            <button
              key={segment.segment_id}
              className="segment-row"
              type="button"
              onClick={() => setDraft(segment)}
            >
              <strong>{segment.label}</strong>
              <span>{segment.segment_id}</span>
              <small>
                {formatMoney(segment.minimum_liquid_net_worth, "CHF")} · {segment.review_policy}
              </small>
            </button>
          ))}
        </div>
        <form className="segment-form" onSubmit={handleSubmit}>
          <div className="two-col">
            <label>
              Segment ID
              <input type="text" value={draft.segment_id} onChange={(e) => edit("segment_id", e.target.value)} required />
            </label>
            <label>
              Label
              <input type="text" value={draft.label} onChange={(e) => edit("label", e.target.value)} required />
            </label>
            <label>
              Minimum liquid net worth
              <input type="number" min="0" step="50000" value={draft.minimum_liquid_net_worth} onChange={(e) => edit("minimum_liquid_net_worth", e.target.value)} />
            </label>
            <label>
              Review policy
              <select value={draft.review_policy} onChange={(e) => edit("review_policy", e.target.value)}>
                <option value="standard">Standard</option>
                <option value="enhanced">Enhanced</option>
                <option value="specialist">Specialist</option>
              </select>
            </label>
          </div>
          <label>
            Description
            <textarea className="short-textarea" value={draft.description} onChange={(e) => edit("description", e.target.value)} />
          </label>
          <label className="checkbox-row">
            <input type="checkbox" checked={draft.enabled} onChange={(e) => edit("enabled", e.target.checked)} />
            Enabled for onboarding and questionnaire assignment
          </label>
          <button type="submit">Save Segment</button>
        </form>
      </div>
    </section>
  );
}

function formatMoney(value, currency) {
  return new Intl.NumberFormat("en-CH", { style: "currency", currency, maximumFractionDigits: 0 }).format(value);
}

createRoot(document.getElementById("root")).render(<App />);
