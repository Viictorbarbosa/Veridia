-- ============================================================================
-- Veridia — MVP Delta Schema
-- ============================================================================
-- Implements the delta model described in docs/architecture.md §1–2.
-- Field names map to the JSON schema in the docs as follows:
--   timestamp        -> created_at   (avoids ambiguity with the `timestamp` type)
--   source_span       -> new: stores the grounding snippet (architecture.md §3.1)
--   metadata           -> new: open JSONB field for extensibility without migrations
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- for gen_random_uuid()

CREATE TABLE IF NOT EXISTS deltas (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    causal_key        TEXT NOT NULL,             -- stable identifier this delta describes
    content           TEXT NOT NULL,              -- the causal fact/event itself
    source_span       TEXT,                        -- exact source text used for grounding (nullable for non-extracted/manual deltas)

    cause             UUID REFERENCES deltas(id) ON DELETE SET NULL,
    effect            UUID[] NOT NULL DEFAULT '{}',  -- array of delta ids; no FK enforcement at MVP tier (see note below)

    previous_version  UUID REFERENCES deltas(id) ON DELETE SET NULL,
    active            BOOLEAN NOT NULL DEFAULT true,

    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata          JSONB NOT NULL DEFAULT '{}'::jsonb  -- open field for future tags/attributes
);

-- Note on `effect`: Postgres cannot enforce array-of-foreign-keys natively.
-- At MVP scale this is an acceptable trade-off for simplicity. If integrity
-- here becomes important, replace with a normalized `delta_effects(delta_id, effect_id)`
-- join table — planned for the scalable/ tier.

-- ============================================================================
-- Indexes
-- ============================================================================

-- Enforces "exactly one current truth per causal_key" at the database level.
-- This is what makes current-truth lookup a deterministic O(1)/O(log n) query
-- rather than something the application layer has to guarantee on its own.
CREATE UNIQUE INDEX IF NOT EXISTS idx_deltas_active_causal_key
    ON deltas (causal_key)
    WHERE active = true;

-- Supports history/audit queries and point-in-time reconstruction.
CREATE INDEX IF NOT EXISTS idx_deltas_causal_key_history
    ON deltas (causal_key, created_at DESC);

-- Supports walking causal chains (cause -> effect).
CREATE INDEX IF NOT EXISTS idx_deltas_cause
    ON deltas (cause);

-- ============================================================================
-- Versioning trigger
-- ============================================================================
-- When a new active delta is inserted for a causal_key that already has an
-- active delta, this automatically:
--   1. Deactivates the prior active delta (never deletes it)
--   2. Links the new delta's `previous_version` to it, if not already set
-- Runs BEFORE INSERT so the unique index above is never violated.

CREATE OR REPLACE FUNCTION supersede_previous_delta()
RETURNS TRIGGER AS $$
DECLARE
    prior_id UUID;
BEGIN
    IF NEW.active THEN
        SELECT id INTO prior_id
        FROM deltas
        WHERE causal_key = NEW.causal_key
          AND active = true
        LIMIT 1;

        IF prior_id IS NOT NULL THEN
            UPDATE deltas SET active = false WHERE id = prior_id;

            IF NEW.previous_version IS NULL THEN
                NEW.previous_version := prior_id;
            END IF;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_supersede_previous_delta ON deltas;

CREATE TRIGGER trg_supersede_previous_delta
    BEFORE INSERT ON deltas
    FOR EACH ROW
    EXECUTE FUNCTION supersede_previous_delta();

-- ============================================================================
-- Convenience view: current truth only
-- ============================================================================

CREATE OR REPLACE VIEW current_truth AS
SELECT * FROM deltas WHERE active = true;

-- ============================================================================
-- Bonus: point-in-time reconstruction
-- ============================================================================
-- Answers "what was true about X as of a given timestamp" — the audit-trail
-- capability described in docs/architecture.md §2. Not required to validate
-- the MVP, but demonstrates the core temporal-consistency claim directly.

CREATE OR REPLACE FUNCTION truth_as_of(target_causal_key TEXT, as_of TIMESTAMPTZ)
RETURNS SETOF deltas AS $$
    SELECT *
    FROM deltas
    WHERE causal_key = target_causal_key
      AND created_at <= as_of
    ORDER BY created_at DESC
    LIMIT 1;
$$ LANGUAGE sql STABLE;

-- ============================================================================
-- Example (commented out) — mirrors the causal chain + versioning example
-- used in docs/diagrams/veridia-flow.svg
-- ============================================================================

-- INSERT INTO deltas (causal_key, content, source_span, active) VALUES
--     ('auth.token_expiry', 'Session timeout triggers automatic logout',
--      'when the timeout expires, the user is logged out', true);
--
-- INSERT INTO deltas (causal_key, content, cause, active) VALUES
--     ('auth.session_state', 'Automatic logout results in session loss',
--      (SELECT id FROM deltas WHERE causal_key = 'auth.token_expiry' AND active = true),
--      true);
--
-- -- Later, the timeout policy changes — inserting this supersedes the v1 delta
-- -- above automatically via the trigger, no UPDATE statement needed:
-- INSERT INTO deltas (causal_key, content, source_span, active) VALUES
--     ('auth.token_expiry', 'Session timeout reduced to 15 minutes',
--      'timeout policy updated to 15 minutes effective March 2026', true);
--
-- SELECT * FROM current_truth WHERE causal_key = 'auth.token_expiry';
-- SELECT * FROM truth_as_of('auth.token_expiry', '2026-02-01');