import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import CustodianApp from "./custodian";
import {
  fetchQuestionnaire,
  listClientSegments,
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

function App() {
  const [status, setStatus] = useState("Loading");
  const [questionnaires, setQuestionnaires] = useState([]);
  const [selectedId, setSelectedId] = useState("client_profile_v1");
  const [questionnaire, setQuestionnaire] = useState(null);
  const [editorText, setEditorText] = useState("");
  const [answers, setAnswers] = useState(DEFAULT_ANSWERS);
  const [product, setProduct] = useState(DEFAULT_PRODUCT);
  const [result, setResult] = useState(null);
  const [clientSegments, setClientSegments] = useState([]);
  const [activeSection, setActiveSection] = useState("custodian");
  const [message, setMessage] = useState("");

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

  async function handleProcess(event) {
    event.preventDefault();
    setMessage("");
    try {
      const payload = {
        answer_set: {
          client_id: "C-1001",
          answers,
        },
        financial_context: {
          age: 42,
          annual_income: 180000,
          liquid_net_worth: 750000,
          restrictions: ["no single-stock positions above 10%"],
        },
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
        if (exists) {
          return current.map((item) => (item.segment_id === saved.segment_id ? saved : item));
        }
        return [...current, saved];
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
          <button
            className={activeSection === "custodian" ? "active" : ""}
            type="button"
            onClick={() => setActiveSection("custodian")}
          >
            Custodian
          </button>
          <button
            className={activeSection === "admin" ? "active" : ""}
            type="button"
            onClick={() => setActiveSection("admin")}
          >
            Admin
          </button>
        </nav>
        <div className={`status ${status === "API online" ? "ok" : status === "API partial" ? "api-partial" : "error"}`}>
          {status}
        </div>
      </aside>

      <section className="content-shell">
        {message ? <p className="message">{message}</p> : null}

        {activeSection === "custodian" ? (
          <CustodianApp />
        ) : (
          <AdminView
            questionnaires={questionnaires}
            selectedId={selectedId}
            setSelectedId={setSelectedId}
            clientSegments={clientSegments}
            onSaveSegment={handleSaveSegment}
            editorText={editorText}
            setEditorText={setEditorText}
            onSubmit={handleSaveQuestionnaire}
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

function ProcessView({ questionnaire, questions, answers, setAnswers, product, setProduct, result, onSubmit }) {
  return (
    <section className="work-grid">
      <form className="panel" onSubmit={onSubmit}>
        <div className="section-header">
          <h2>Answers</h2>
          <button type="submit">Run Profile</button>
        </div>

        <QuestionnaireTree questionnaire={questionnaire} />

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
      </form>

      <ResultPanel result={result} />
    </section>
  );
}

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

  if (!nodes.length && !questions.length) {
    return null;
  }

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
                  {edge.condition ? `${edge.condition.question_id} ${edge.condition.operator} ${String(edge.condition.value)}` : "next"}
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
      <h3>Questionnaire Tree</h3>
      <ul>{entryNodeId ? renderNode(entryNodeId) : null}</ul>
    </section>
  );
}

function ProductPanel({ product, setProduct }) {
  function update(field, value) {
    setProduct((current) => ({ ...current, [field]: value }));
  }

  return (
    <section className="subpanel">
      <h3>Product Gate Input</h3>
      <div className="three-col">
        <label>
          Instrument
          <select
            value={product.instrument_type}
            onChange={(event) => update("instrument_type", event.target.value)}
          >
            <option value="equities">Equities</option>
            <option value="bonds">Bonds</option>
            <option value="funds_etfs">Funds / ETFs</option>
            <option value="derivatives">Derivatives</option>
            <option value="structured_products">Structured products</option>
          </select>
        </label>
        <label>
          Min experience
          <select
            value={product.minimum_instrument_experience}
            onChange={(event) => update("minimum_instrument_experience", event.target.value)}
          >
            <option value="none">None</option>
            <option value="basic">Basic</option>
            <option value="experienced">Experienced</option>
            <option value="advanced">Advanced</option>
          </select>
        </label>
        <label>
          Risk
          <select value={product.risk_level} onChange={(event) => update("risk_level", event.target.value)}>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </label>
        <label>
          Knowledge
          <select
            value={product.required_knowledge}
            onChange={(event) => update("required_knowledge", event.target.value)}
          >
            <option value="basic">Basic</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </select>
        </label>
        <label>
          Liquidity
          <select
            value={String(product.daily_liquidity)}
            onChange={(event) => update("daily_liquidity", event.target.value === "true")}
          >
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

function formatMoney(value, currency) {
  return new Intl.NumberFormat("en-CH", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(value);
}

function formatNumber(value) {
  return new Intl.NumberFormat("en-CH", {
    maximumFractionDigits: 2,
  }).format(value);
}

function AdminView({
  questionnaires,
  selectedId,
  setSelectedId,
  clientSegments,
  onSaveSegment,
  editorText,
  setEditorText,
  onSubmit,
  questionnaire,
  questions,
  answers,
  setAnswers,
  product,
  setProduct,
  result,
  onProcess,
}) {
  return (
    <section className="admin-layout">
      <SegmentAdmin segments={clientSegments} onSaveSegment={onSaveSegment} />

      <section className="admin-section">
        <div className="section-header">
          <h2>Questionnaire And Profiling</h2>
          <label className="inline-select">
            Questionnaire
            <select value={selectedId} onChange={(event) => setSelectedId(event.target.value)}>
              {questionnaires.map((item) => (
                <option key={item.questionnaire_id} value={item.questionnaire_id}>
                  {item.questionnaire_id} v{item.version}
                </option>
              ))}
            </select>
          </label>
        </div>

        <ProcessView
          questionnaire={questionnaire}
          questions={questions}
          answers={answers}
          setAnswers={setAnswers}
          product={product}
          setProduct={setProduct}
          result={result}
          onSubmit={onProcess}
        />
      </section>

      <form className="panel admin-panel" onSubmit={onSubmit}>
        <div className="section-header">
          <h2>Questionnaire Definition</h2>
          <button type="submit">Save Definition</button>
        </div>
        <textarea
          spellCheck="false"
          value={editorText}
          onChange={(event) => setEditorText(event.target.value)}
        />
      </form>
    </section>
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

  function loadSegment(segment) {
    setDraft(segment);
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
              onClick={() => loadSegment(segment)}
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
              <input
                type="text"
                value={draft.segment_id}
                onChange={(event) => edit("segment_id", event.target.value)}
                required
              />
            </label>
            <label>
              Label
              <input
                type="text"
                value={draft.label}
                onChange={(event) => edit("label", event.target.value)}
                required
              />
            </label>
            <label>
              Minimum liquid net worth
              <input
                type="number"
                min="0"
                step="50000"
                value={draft.minimum_liquid_net_worth}
                onChange={(event) => edit("minimum_liquid_net_worth", event.target.value)}
              />
            </label>
            <label>
              Review policy
              <select
                value={draft.review_policy}
                onChange={(event) => edit("review_policy", event.target.value)}
              >
                <option value="standard">Standard</option>
                <option value="enhanced">Enhanced</option>
                <option value="specialist">Specialist</option>
              </select>
            </label>
          </div>
          <label>
            Description
            <textarea
              className="short-textarea"
              value={draft.description}
              onChange={(event) => edit("description", event.target.value)}
            />
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={draft.enabled}
              onChange={(event) => edit("enabled", event.target.checked)}
            />
            Enabled for onboarding and questionnaire assignment
          </label>
          <button type="submit">Save Segment</button>
        </form>
      </div>
    </section>
  );
}

createRoot(document.getElementById("root")).render(<App />);
