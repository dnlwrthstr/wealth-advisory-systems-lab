DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'wealth_advisory'
    ) THEN
        CREATE ROLE wealth_advisory LOGIN PASSWORD 'wealth_advisory';
    END IF;
END
$$;

ALTER ROLE wealth_advisory SET search_path = custodian, advisory, admin, audit, public;

CREATE SCHEMA IF NOT EXISTS custodian;
CREATE SCHEMA IF NOT EXISTS advisory;
CREATE SCHEMA IF NOT EXISTS admin;
CREATE SCHEMA IF NOT EXISTS audit;

GRANT USAGE, CREATE ON SCHEMA custodian TO wealth_advisory;
GRANT USAGE, CREATE ON SCHEMA advisory TO wealth_advisory;
GRANT USAGE, CREATE ON SCHEMA admin TO wealth_advisory;
GRANT USAGE, CREATE ON SCHEMA audit TO wealth_advisory;

-- ------------------------------------------------------------
-- custodian schema  (custodian-api)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS custodian.custody_customer (
    customer_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    domicile CHAR(2) NOT NULL,
    segment TEXT NOT NULL,
    risk_profile TEXT NOT NULL,
    source_system TEXT NOT NULL DEFAULT 'openwealth_mock',
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS custodian.custody_portfolio (
    portfolio_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES custodian.custody_customer(customer_id),
    name TEXT NOT NULL,
    base_currency CHAR(3) NOT NULL,
    mandate_type TEXT NOT NULL,
    strategy TEXT NOT NULL,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS custodian.custody_account (
    account_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES custodian.custody_customer(customer_id),
    portfolio_id TEXT NOT NULL REFERENCES custodian.custody_portfolio(portfolio_id),
    account_number TEXT NOT NULL,
    account_type TEXT NOT NULL,
    currency CHAR(3) NOT NULL,
    iban TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS custodian.custody_position (
    position_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES custodian.custody_customer(customer_id),
    account_id TEXT NOT NULL REFERENCES custodian.custody_account(account_id),
    portfolio_id TEXT NOT NULL REFERENCES custodian.custody_portfolio(portfolio_id),
    position_type TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    isin TEXT,
    instrument_name TEXT NOT NULL,
    instrument_type TEXT NOT NULL,
    instrument_currency CHAR(3) NOT NULL,
    instrument_country CHAR(2),
    instrument_sector TEXT,
    quantity NUMERIC(24, 8) NOT NULL,
    price NUMERIC(24, 8) NOT NULL,
    market_value NUMERIC(18, 2) NOT NULL,
    accrued_interest NUMERIC(18, 2) NOT NULL DEFAULT 0,
    valuation_currency CHAR(3) NOT NULL,
    fx_rate_to_base NUMERIC(18, 8) NOT NULL DEFAULT 1,
    base_market_value NUMERIC(18, 2) NOT NULL,
    valuation_date DATE NOT NULL,
    weight NUMERIC(10, 6) NOT NULL,
    safekeeping_place TEXT,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS custodian.custody_transaction (
    transaction_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES custodian.custody_customer(customer_id),
    account_id TEXT NOT NULL REFERENCES custodian.custody_account(account_id),
    portfolio_id TEXT NOT NULL REFERENCES custodian.custody_portfolio(portfolio_id),
    position_id TEXT REFERENCES custodian.custody_position(position_id),
    transaction_type TEXT NOT NULL,
    booking_date DATE NOT NULL,
    value_date DATE NOT NULL,
    amount NUMERIC(18, 2) NOT NULL,
    currency CHAR(3) NOT NULL,
    quantity NUMERIC(24, 8),
    instrument_id TEXT,
    description TEXT NOT NULL,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- advisory schema  (profile-api)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS advisory.client_profile (
    client_id TEXT PRIMARY KEY,
    age INTEGER NOT NULL CHECK (age >= 0),
    annual_income NUMERIC(14, 2) NOT NULL CHECK (annual_income >= 0),
    liquid_net_worth NUMERIC(14, 2) NOT NULL CHECK (liquid_net_worth > 0),
    investment_horizon_years INTEGER NOT NULL CHECK (investment_horizon_years >= 0),
    liquidity_need_12m NUMERIC(14, 2) NOT NULL CHECK (liquidity_need_12m >= 0),
    risk_tolerance TEXT NOT NULL CHECK (risk_tolerance IN ('low', 'medium', 'high')),
    investment_knowledge TEXT NOT NULL CHECK (investment_knowledge IN ('basic', 'intermediate', 'advanced')),
    instrument_knowledge JSONB NOT NULL DEFAULT '{
        "equities": "none",
        "bonds": "none",
        "funds_etfs": "basic",
        "derivatives": "none",
        "structured_products": "none"
    }'::jsonb,
    has_dependents BOOLEAN NOT NULL DEFAULT FALSE,
    restrictions TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS advisory.product_profile (
    product_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    risk_level TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high')),
    required_knowledge TEXT NOT NULL CHECK (required_knowledge IN ('basic', 'intermediate', 'advanced')),
    instrument_type TEXT NOT NULL DEFAULT 'funds_etfs' CHECK (
        instrument_type IN ('equities', 'bonds', 'funds_etfs', 'derivatives', 'structured_products')
    ),
    minimum_instrument_experience TEXT NOT NULL DEFAULT 'basic' CHECK (
        minimum_instrument_experience IN ('none', 'basic', 'experienced', 'advanced')
    ),
    daily_liquidity BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS advisory.suitability_evaluation (
    evaluation_id BIGSERIAL PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES advisory.client_profile(client_id),
    product_id TEXT NOT NULL REFERENCES advisory.product_profile(product_id),
    liquidity_ratio NUMERIC(8, 4) NOT NULL,
    risk_capacity TEXT NOT NULL CHECK (risk_capacity IN ('low', 'medium', 'high')),
    combined_risk_profile TEXT NOT NULL CHECK (combined_risk_profile IN ('low', 'medium', 'high')),
    suitable BOOLEAN NOT NULL,
    flags TEXT[] NOT NULL DEFAULT '{}',
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- admin schema  (profile-api)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS admin.questionnaire_definition (
    questionnaire_id TEXT NOT NULL,
    version TEXT NOT NULL,
    definition JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'retired')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (questionnaire_id, version)
);

-- ------------------------------------------------------------
-- audit schema  (profile-api)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS audit.profile_processing_run (
    processing_run_id BIGSERIAL PRIMARY KEY,
    client_id TEXT NOT NULL,
    questionnaire_id TEXT NOT NULL,
    questionnaire_version TEXT NOT NULL,
    ontology_version TEXT NOT NULL,
    raw_answers JSONB NOT NULL,
    score_contributions JSONB NOT NULL,
    derived_profile JSONB,
    strategy_profile JSONB,
    gates JSONB NOT NULL DEFAULT '[]'::jsonb,
    warnings TEXT[] NOT NULL DEFAULT '{}',
    errors TEXT[] NOT NULL DEFAULT '{}',
    valid BOOLEAN NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (questionnaire_id, questionnaire_version)
        REFERENCES admin.questionnaire_definition(questionnaire_id, version)
);

-- ------------------------------------------------------------
-- Grants
-- ------------------------------------------------------------

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA custodian TO wealth_advisory;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA advisory TO wealth_advisory;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA admin TO wealth_advisory;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA audit TO wealth_advisory;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA custodian TO wealth_advisory;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA advisory TO wealth_advisory;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA admin TO wealth_advisory;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA audit TO wealth_advisory;

ALTER DEFAULT PRIVILEGES IN SCHEMA custodian
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO wealth_advisory;
ALTER DEFAULT PRIVILEGES IN SCHEMA advisory
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO wealth_advisory;
ALTER DEFAULT PRIVILEGES IN SCHEMA admin
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO wealth_advisory;
ALTER DEFAULT PRIVILEGES IN SCHEMA audit
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO wealth_advisory;
ALTER DEFAULT PRIVILEGES IN SCHEMA custodian
    GRANT USAGE, SELECT ON SEQUENCES TO wealth_advisory;
ALTER DEFAULT PRIVILEGES IN SCHEMA advisory
    GRANT USAGE, SELECT ON SEQUENCES TO wealth_advisory;
ALTER DEFAULT PRIVILEGES IN SCHEMA admin
    GRANT USAGE, SELECT ON SEQUENCES TO wealth_advisory;
ALTER DEFAULT PRIVILEGES IN SCHEMA audit
    GRANT USAGE, SELECT ON SEQUENCES TO wealth_advisory;

-- ------------------------------------------------------------
-- Seed data
-- ------------------------------------------------------------

INSERT INTO admin.questionnaire_definition (
    questionnaire_id,
    version,
    definition,
    status
) VALUES (
    'client_profile_v1',
    '1.0',
    '{
        "questionnaire_id": "client_profile_v1",
        "version": "1.0",
        "questions": [
            {
                "question_id": "loss_reaction",
                "prompt": "What would you most likely do if your portfolio fell by 15%?",
                "answer_type": "single_choice",
                "target_signal": "risk_willingness",
                "required": true,
                "ontology_path": "client_profile.risk_tolerance.questionnaire.loss_scenarios.loss_10_percent",
                "options": [
                    {"value": "sell", "label": "Sell to avoid further losses", "score": 0},
                    {"value": "hold", "label": "Hold the portfolio", "score": 1},
                    {"value": "buy_more", "label": "Invest more at lower prices", "score": 2}
                ]
            },
            {
                "question_id": "portfolio_decline_comfort",
                "prompt": "How comfortable are you with temporary portfolio declines?",
                "answer_type": "single_choice",
                "target_signal": "risk_willingness",
                "required": true,
                "ontology_path": "client_profile.risk_tolerance.questionnaire.loss_scenarios.loss_20_percent",
                "options": [
                    {"value": "very_uncomfortable", "label": "Very uncomfortable", "score": 0},
                    {"value": "somewhat_comfortable", "label": "Somewhat comfortable", "score": 1},
                    {"value": "comfortable", "label": "Comfortable", "score": 2}
                ]
            },
            {
                "question_id": "investment_experience",
                "prompt": "Which investments have you previously used?",
                "answer_type": "single_choice",
                "target_signal": "knowledge",
                "required": true,
                "ontology_path": "client_profile.knowledge_and_experience.instruments.funds_etfs",
                "options": [
                    {"value": "savings_only", "label": "Savings accounts only", "score": 0},
                    {"value": "funds_and_etfs", "label": "Funds or ETFs", "score": 1},
                    {"value": "complex_products", "label": "Complex products", "score": 2}
                ]
            },
            {
                "question_id": "product_knowledge",
                "prompt": "How would you describe your investment product knowledge?",
                "answer_type": "single_choice",
                "target_signal": "knowledge",
                "required": true,
                "ontology_path": "client_profile.knowledge_and_experience",
                "options": [
                    {"value": "limited", "label": "Limited", "score": 0},
                    {"value": "general", "label": "General", "score": 1},
                    {"value": "advanced", "label": "Advanced", "score": 2}
                ]
            },
            {
                "question_id": "horizon",
                "prompt": "When do you expect to need most of this invested capital?",
                "answer_type": "single_choice",
                "target_signal": "horizon",
                "required": true,
                "ontology_path": "client_profile.investment_objectives.investment_horizon",
                "options": [
                    {"value": "under_3_years", "label": "Under 3 years", "score": 2},
                    {"value": "3_to_7_years", "label": "3 to 7 years", "score": 6},
                    {"value": "7_to_15_years", "label": "7 to 15 years", "score": 12},
                    {"value": "over_15_years", "label": "Over 15 years", "score": 18}
                ]
            },
            {
                "question_id": "liquidity_need",
                "prompt": "How much liquidity do you expect to need over the next 12 months?",
                "answer_type": "single_choice",
                "target_signal": "liquidity_pressure",
                "required": true,
                "ontology_path": "client_profile.financial_situation.liquidity_needs",
                "options": [
                    {"value": "low", "label": "Low", "score": 25000},
                    {"value": "moderate", "label": "Moderate", "score": 60000},
                    {"value": "high", "label": "High", "score": 150000}
                ]
            },
            {
                "question_id": "has_dependents",
                "prompt": "Do you have dependents or similar financial obligations?",
                "answer_type": "boolean",
                "target_signal": "obligation",
                "required": true,
                "ontology_path": "client_profile.financial_situation",
                "options": [
                    {"value": false, "label": "No", "score": 0},
                    {"value": true, "label": "Yes", "score": 1}
                ]
            }
        ]
    }'::jsonb,
    'active'
) ON CONFLICT (questionnaire_id, version) DO NOTHING;

INSERT INTO advisory.client_profile (
    client_id, age, annual_income, liquid_net_worth,
    investment_horizon_years, liquidity_need_12m,
    risk_tolerance, investment_knowledge, instrument_knowledge,
    has_dependents, restrictions
) VALUES (
    'C-1001', 42, 180000, 750000, 12, 60000,
    'medium', 'intermediate',
    '{"equities":"basic","bonds":"basic","funds_etfs":"experienced","derivatives":"none","structured_products":"none"}'::jsonb,
    TRUE, ARRAY['no single-stock positions above 10%']
) ON CONFLICT (client_id) DO NOTHING;

INSERT INTO advisory.product_profile (
    product_id, name, risk_level, required_knowledge,
    instrument_type, minimum_instrument_experience, daily_liquidity
) VALUES (
    'P-204', 'Global Multi-Asset Fund', 'medium', 'basic',
    'funds_etfs', 'basic', TRUE
) ON CONFLICT (product_id) DO NOTHING;

INSERT INTO custodian.custody_customer (
    customer_id, display_name, domicile, segment, risk_profile, raw_payload
) VALUES
    ('C-1001', 'Anna Keller',        'CH', 'private_client', 'balanced', '{"source":"openwealth_mock"}'::jsonb),
    ('C-2002', 'Meyer Family Office', 'CH', 'family_office',  'growth',   '{"source":"openwealth_mock"}'::jsonb)
ON CONFLICT (customer_id) DO NOTHING;

INSERT INTO custodian.custody_portfolio (
    portfolio_id, customer_id, name, base_currency, mandate_type, strategy
) VALUES
    ('PF-1001-CORE',   'C-1001', 'Core discretionary mandate', 'CHF', 'discretionary', 'balanced'),
    ('PF-1001-LIQ',    'C-1001', 'Liquidity reserve',          'CHF', 'advisory',       'capital_preservation'),
    ('PF-2002-GROWTH', 'C-2002', 'Global growth portfolio',    'CHF', 'advisory',       'growth')
ON CONFLICT (portfolio_id) DO NOTHING;

INSERT INTO custodian.custody_account (
    account_id, customer_id, portfolio_id, account_number, account_type, currency, iban
) VALUES
    ('A-1001-CHF',  'C-1001', 'PF-1001-CORE',   '700001.01', 'custody_account', 'CHF', 'CH9300762011623852957'),
    ('A-1001-EUR',  'C-1001', 'PF-1001-CORE',   '700001.02', 'current_account', 'EUR', NULL),
    ('A-1001-CASH', 'C-1001', 'PF-1001-LIQ',    '700001.03', 'current_account', 'CHF', NULL),
    ('A-2002-CHF',  'C-2002', 'PF-2002-GROWTH', '800002.01', 'custody_account', 'CHF', NULL)
ON CONFLICT (account_id) DO NOTHING;

INSERT INTO custodian.custody_position (
    position_id, customer_id, account_id, portfolio_id,
    position_type, instrument_id, isin, instrument_name, instrument_type,
    instrument_currency, instrument_country, instrument_sector,
    quantity, price, market_value, accrued_interest,
    valuation_currency, fx_rate_to_base, base_market_value, valuation_date, weight,
    safekeeping_place
) VALUES
    ('POS-1001-CASH-CHF', 'C-1001', 'A-1001-CASH', 'PF-1001-LIQ',
     'cash', 'CASH-CHF', NULL, 'Swiss franc cash', 'cash',
     'CHF', 'CH', NULL,
     85000, 1, 85000, 0,
     'CHF', 1, 85000, '2026-05-14', 0.106, NULL),
    ('POS-1001-CHSPI', 'C-1001', 'A-1001-CHF', 'PF-1001-CORE',
     'security', 'CHSPI', 'CH0237935652', 'iShares Core SPI ETF', 'funds_etfs',
     'CHF', 'CH', 'broad_market',
     940, 152.4, 143256, 0,
     'CHF', 1, 143256, '2026-05-14', 0.179, 'SIX SIS'),
    ('POS-1001-WRLD', 'C-1001', 'A-1001-CHF', 'PF-1001-CORE',
     'security', 'WRLD', 'IE00B4L5Y983', 'iShares Core MSCI World UCITS ETF', 'funds_etfs',
     'USD', 'IE', 'global_equity',
     2350, 117.85, 276947.5, 0,
     'USD', 0.91, 252022.23, '2026-05-14', 0.315, 'Clearstream'),
    ('POS-1001-BOND', 'C-1001', 'A-1001-CHF', 'PF-1001-CORE',
     'security', 'CHGOV-2034', 'CH0557778319', 'Swiss Confederation Bond 0.5% 2034', 'bonds',
     'CHF', 'CH', 'government',
     220000, 96.2, 211640, 612,
     'CHF', 1, 212252, '2026-05-14', 0.265, 'SIX SIS'),
    ('POS-1001-ALT', 'C-1001', 'A-1001-CHF', 'PF-1001-CORE',
     'security', 'ALT-REAL', 'CH0031069328', 'Swiss Prime Site AG', 'equities',
     'CHF', 'CH', 'real_estate',
     1080, 99.8, 107784, 0,
     'CHF', 1, 107784, '2026-05-14', 0.135, 'SIX SIS'),
    ('POS-2002-WRLD', 'C-2002', 'A-2002-CHF', 'PF-2002-GROWTH',
     'security', 'WRLD', 'IE00B4L5Y983', 'iShares Core MSCI World UCITS ETF', 'funds_etfs',
     'USD', 'IE', 'global_equity',
     7200, 117.85, 848520, 0,
     'USD', 0.91, 772153.2, '2026-05-14', 0.68, 'Clearstream')
ON CONFLICT (position_id) DO NOTHING;

INSERT INTO custodian.custody_transaction (
    transaction_id, customer_id, account_id, portfolio_id, position_id,
    transaction_type, booking_date, value_date, amount, currency,
    quantity, instrument_id, description
) VALUES
    ('TX-1001-001', 'C-1001', 'A-1001-CHF', 'PF-1001-CORE', 'POS-1001-WRLD',
     'buy', '2026-05-10', '2026-05-12', -54418.00, 'CHF',
     500, 'WRLD', 'Purchase MSCI World ETF'),
    ('TX-1001-002', 'C-1001', 'A-1001-CHF', 'PF-1001-CORE', 'POS-1001-BOND',
     'coupon', '2026-05-12', '2026-05-14', 550.00, 'CHF',
     NULL, 'CHGOV-2034', 'Bond coupon payment'),
    ('TX-1001-003', 'C-1001', 'A-1001-CASH', 'PF-1001-LIQ', NULL,
     'deposit', '2026-05-13', '2026-05-13', 25000, 'CHF',
     NULL, NULL, 'Client cash deposit')
ON CONFLICT (transaction_id) DO NOTHING;
